from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.master_data.models import (
    Department,
    InspectionTool,
    MachinePMLog,
    ShiftType,
    ToolStatus,
    ToolType,
    Workstation,
    WorkstationStatus,
)


class MasterDataAndCalibrationLocksTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = timezone.now().date()

        self.supervisor = User.objects.create_user(
            username='sup_user',
            employee_id='EMP-SUP-01',
            role=UserRole.SHIFT_SUPERVISOR,
            password='password123'
        )
        self.engineer = User.objects.create_user(
            username='qe_user',
            employee_id='EMP-QE-01',
            role=UserRole.QUALITY_ENGINEER,
            password='password123'
        )
        self.inspector = User.objects.create_user(
            username='insp_user',
            employee_id='EMP-INSP-01',
            role=UserRole.QA_FLOOR_INSPECTOR,
            password='password123'
        )

        self.dept = Department.objects.create(
            code='MACH',
            name='Machining Bay'
        )

        self.workstation = Workstation.objects.create(
            machine_code='CNC-04',
            name='CNC Lathe #04',
            department=self.dept,
            qr_code_identifier='WS-CNC-04-QR',
            status=WorkstationStatus.IDLE
        )

        self.valid_tool = InspectionTool.objects.create(
            tool_id='VC-104',
            name='Digital Caliper',
            tool_type=ToolType.CALIPER,
            serial_number='SN-VC-104',
            calibration_date=self.today - timedelta(days=30),
            calibration_expiry_date=self.today + timedelta(days=60),
            status=ToolStatus.CALIBRATED
        )

        self.expired_tool = InspectionTool.objects.create(
            tool_id='MIC-02',
            name='Outside Micrometer',
            tool_type=ToolType.MICROMETER,
            serial_number='SN-MIC-02',
            calibration_date=self.today - timedelta(days=380),
            calibration_expiry_date=self.today - timedelta(days=10),
            status=ToolStatus.EXPIRED
        )

    def test_workstation_pm_lockout_when_pm_overdue(self):
        """
        BRD Section 2.2:
        Before an operator can select a job on tablet, system checks whether machine's daily
        PM checklist is complete. If PM is overdue, job selection MUST be disabled.
        """
        can_start, reason = self.workstation.can_start_job(date=self.today)
        self.assertFalse(can_start)
        self.assertIn("Machine PM Lockout", reason)
        self.assertIn("overdue", reason)

    def test_workstation_cleared_when_pm_passed(self):
        """
        When daily PM checklist is completed with all safety checks passed,
        the machine is unlocked for job selection.
        """
        pm = MachinePMLog.objects.create(
            workstation=self.workstation,
            log_date=self.today,
            shift=ShiftType.MORNING,
            completed_by=self.supervisor,
            zero_point_verified=True,
            lubrication_level_ok=True,
            safety_interlocks_ok=True,
            spindle_runout_ok=True,
            pneumatic_pressure_ok=True,
            emergency_stop_tested=True,
            remarks="All morning checks normal."
        )
        self.assertTrue(pm.is_passed)
        self.assertTrue(self.workstation.is_daily_pm_completed(date=self.today))

        can_start, reason = self.workstation.can_start_job(date=self.today)
        self.assertTrue(can_start)
        self.assertIn("cleared for production", reason)

    def test_workstation_maintenance_locked_overrides_pm(self):
        """
        Even if daily PM is passed, if the machine is under MAINTENANCE_LOCKED status,
        job selection must remain strictly blocked.
        """
        MachinePMLog.objects.create(
            workstation=self.workstation,
            log_date=self.today,
            shift=ShiftType.MORNING,
            completed_by=self.supervisor,
            zero_point_verified=True,
            lubrication_level_ok=True,
            safety_interlocks_ok=True,
            spindle_runout_ok=True,
            pneumatic_pressure_ok=True,
            emergency_stop_tested=True
        )
        self.workstation.status = WorkstationStatus.MAINTENANCE_LOCKED
        self.workstation.save()

        can_start, reason = self.workstation.can_start_job(date=self.today)
        self.assertFalse(can_start)
        self.assertIn("MAINTENANCE LOCKOUT", reason)

    def test_workstation_pm_fails_if_any_check_missing(self):
        """
        Server-side validation: if any safety check is unchecked, PM is marked as FAILED.
        """
        pm = MachinePMLog(
            workstation=self.workstation,
            log_date=self.today,
            shift=ShiftType.MORNING,
            completed_by=self.supervisor,
            zero_point_verified=True,
            lubrication_level_ok=False,  # Fails!
            safety_interlocks_ok=True,
            spindle_runout_ok=True,
            pneumatic_pressure_ok=True,
            emergency_stop_tested=True
        )
        pm.save()
        self.assertFalse(pm.is_passed)
        can_start, _ = self.workstation.can_start_job(date=self.today)
        self.assertFalse(can_start)

    def test_tool_calibration_lockout_enforcement(self):
        """
        BRD Section 2.3:
        If gauge calibration interval has expired, tablet blocks measurement entry,
        displays 'Expired Tool Calibration' error, and instructs worker to obtain a calibrated tool.
        """
        # Valid tool should validate without error
        self.assertTrue(self.valid_tool.is_calibration_valid)
        try:
            self.valid_tool.validate_for_measurement()
        except ValidationError:
            self.fail("Valid tool raised ValidationError unexpectedly.")

        # Expired tool must raise ValidationError with exact required phrasing
        self.assertFalse(self.expired_tool.is_calibration_valid)
        with self.assertRaises(ValidationError) as ctx:
            self.expired_tool.validate_for_measurement()
        self.assertIn("Expired Tool Calibration", str(ctx.exception))
        self.assertIn("MIC-02", str(ctx.exception))

    def test_tool_verify_api_endpoint(self):
        """Verify API response for gauge validation endpoint."""
        self.client.force_login(self.supervisor)

        # 1. Valid tool returns 200 with success: True
        resp_valid = self.client.get(reverse('master_data:tool_verify_api'), {'tool_id': 'VC-104'})
        self.assertEqual(resp_valid.status_code, 200)
        data_valid = resp_valid.json()
        self.assertTrue(data_valid['success'])
        self.assertTrue(data_valid['is_valid'])

        # 2. Expired tool returns 422 with success: False and lockout error message
        resp_expired = self.client.get(reverse('master_data:tool_verify_api'), {'tool_id': 'MIC-02'})
        self.assertEqual(resp_expired.status_code, 422)
        data_expired = resp_expired.json()
        self.assertFalse(data_expired['success'])
        self.assertIn("Expired Tool Calibration", data_expired['error'])

    def test_pm_checklist_rbac_access(self):
        """
        Verify that authorized roles (Supervisor) can submit PM,
        while unauthorized roles (Quality Engineer) are prevented.
        """
        # Engineer attempt
        self.client.force_login(self.engineer)
        resp_qe = self.client.get(reverse('master_data:workstation_pm_create', args=[self.workstation.pk]))
        self.assertRedirects(resp_qe, reverse('dashboard:index'))

        # Supervisor attempt
        self.client.force_login(self.supervisor)
        resp_sup = self.client.get(reverse('master_data:workstation_pm_create', args=[self.workstation.pk]))
        self.assertEqual(resp_sup.status_code, 200)

        # Supervisor post PM form
        post_resp = self.client.post(reverse('master_data:workstation_pm_create', args=[self.workstation.pk]), {
            'shift': ShiftType.MORNING,
            'zero_point_verified': 'on',
            'lubrication_level_ok': 'on',
            'safety_interlocks_ok': 'on',
            'spindle_runout_ok': 'on',
            'pneumatic_pressure_ok': 'on',
            'emergency_stop_tested': 'on',
            'remarks': 'Supervisor verification complete'
        })
        self.assertRedirects(post_resp, reverse('master_data:workstation_detail', args=[self.workstation.pk]))
        self.assertTrue(self.workstation.is_daily_pm_completed(date=self.today))

    def test_tool_create_rbac_and_validation(self):
        """
        Verify tool creation is permitted for Quality Engineer,
        blocked for Floor Inspector, and validates that expiry is after calibration date.
        """
        # Floor Inspector attempt should be blocked
        self.client.force_login(self.inspector)
        resp_insp = self.client.get(reverse('master_data:tool_create'))
        self.assertRedirects(resp_insp, reverse('dashboard:index'))

        # Quality Engineer attempt should be permitted
        self.client.force_login(self.engineer)
        resp_qe = self.client.get(reverse('master_data:tool_create'))
        self.assertEqual(resp_qe.status_code, 200)

        # Invalid dates: expiry before calibration date
        resp_invalid_date = self.client.post(reverse('master_data:tool_create'), {
            'tool_id': 'TEST-01',
            'name': 'Test Gauge',
            'tool_type': ToolType.CALIPER,
            'serial_number': 'SN-TEST-01',
            'calibration_date': '2026-10-10',
            'calibration_expiry_date': '2026-09-01',  # Earlier than calibration date!
        })
        self.assertEqual(resp_invalid_date.status_code, 200)
        self.assertFalse(InspectionTool.objects.filter(tool_id='TEST-01').exists())

        # Valid dates
        resp_valid_date = self.client.post(reverse('master_data:tool_create'), {
            'tool_id': 'TEST-01',
            'name': 'Test Gauge',
            'tool_type': ToolType.CALIPER,
            'serial_number': 'SN-TEST-01',
            'calibration_date': '2026-10-10',
            'calibration_expiry_date': '2027-10-10',
            'storage_location': 'Crib 1'
        })
        self.assertRedirects(resp_valid_date, reverse('master_data:tool_list'))
        self.assertTrue(InspectionTool.objects.filter(tool_id='TEST-01').exists())
