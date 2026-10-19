from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.audit_trail.models import AuditLog
from apps.inventory.models import (
    IntakeStatus,
    LabStatus,
    MaterialGrade,
    QuantityUnit,
    RawMaterialIntake,
)
from apps.master_data.models import (
    Department,
    InspectionTool,
    MachinePMLog,
    ToolStatus,
    ToolType,
    Workstation,
)
from apps.production.models import (
    JobTraveler,
    JobTravelerStatus,
    OperationStatus,
    TravelerOperation,
    WorkOrder,
    WorkOrderStatus,
)
from apps.quality.models import (
    Blueprint,
    BlueprintPin,
    CertificateOfConformance,
    CertificateStatus,
    ConcessionReason,
    ConcessionRecord,
    FloorInspection,
    FloorInspectionStatus,
    InspectionDefectPhoto,
    InspectionMeasurement,
    InspectionParameter,
    InspectionTemplate,
    InspectionTemplateRevision,
    MRBDisposition,
    MRBDispositionType,
    ParameterType,
    Part,
    RevisionStatus,
    TemplateType,
    ThresholdType,
    validate_defect_photo_file,
)


class QualityModelAndLogicTests(TestCase):
    def setUp(self):
        # Create users
        self.plant_mgr = User.objects.create_user(
            username='plant_mgr', employee_id='EMP-101', role=UserRole.PLANT_MANAGER
        )
        self.quality_mgr = User.objects.create_user(
            username='quality_mgr', employee_id='EMP-102', role=UserRole.QUALITY_MANAGER
        )
        self.quality_eng = User.objects.create_user(
            username='quality_eng', employee_id='EMP-103', role=UserRole.QUALITY_ENGINEER
        )
        self.inspector = User.objects.create_user(
            username='inspector', employee_id='EMP-105', role=UserRole.QA_FLOOR_INSPECTOR
        )

        self.grade = MaterialGrade.objects.create(
            code='AISI-4140',
            name='Chromoly Alloy Steel',
            description='ASTM A29 alloy steel standard',
        )

        self.part = Part.objects.create(
            part_number='PART-SH-401',
            part_name='Drive Shaft',
            material_grade=self.grade,
            drawing_number='DWG-SH401',
            revision_level='Rev A',
        )

        self.template = InspectionTemplate.objects.create(
            part=self.part,
            template_code='TPL-SH401-PDI',
            title='Drive Shaft Final PDI',
            template_type=TemplateType.FINAL_PDI,
        )

        self.revision = InspectionTemplateRevision.objects.create(
            template=self.template,
            revision_label='Rev A',
            status=RevisionStatus.DRAFT,
            created_by=self.quality_eng,
        )

    def test_quality_engineer_can_draft_template(self):
        """Quality engineers can draft templates in DRAFT status."""
        self.assertEqual(self.revision.status, RevisionStatus.DRAFT)
        self.assertFalse(self.revision.is_locked)

    def test_non_quality_manager_cannot_approve_template(self):
        """Only Quality Managers can formally approve template revisions."""
        # Quality engineer attempts approval
        with self.assertRaises(ValidationError):
            self.revision.approve(self.quality_eng)

        # Inspector attempts approval
        with self.assertRaises(ValidationError):
            self.revision.approve(self.inspector)

        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, RevisionStatus.DRAFT)

    def test_quality_manager_approval_locks_revision_and_supersedes_prior(self):
        """Approval locks revision and supersedes older approved revisions."""
        # QM approves Rev A
        self.revision.approve(self.quality_mgr, notes="Approved for production")
        self.revision.refresh_from_db()

        self.assertEqual(self.revision.status, RevisionStatus.APPROVED)
        self.assertEqual(self.revision.approved_by, self.quality_mgr)
        self.assertTrue(self.revision.is_locked)

        # Create Rev B and approve it
        rev_b = InspectionTemplateRevision.objects.create(
            template=self.template,
            revision_label='Rev B',
            status=RevisionStatus.DRAFT,
            created_by=self.quality_eng,
        )
        rev_b.approve(self.quality_mgr, notes="Rev B approved")

        self.revision.refresh_from_db()
        rev_b.refresh_from_db()

        # Prior revision is now superseded
        self.assertEqual(self.revision.status, RevisionStatus.SUPERSEDED)
        self.assertEqual(rev_b.status, RevisionStatus.APPROVED)
        self.assertEqual(self.template.get_approved_revision(), rev_b)

    def test_inspection_parameter_dimension_tolerance_evaluation(self):
        """Test server-side numerical tolerance validation (nominal +/- upper/lower)."""
        param = InspectionParameter.objects.create(
            template_revision=self.revision,
            sequence_order=1,
            parameter_name='Shaft Diameter Ø25.000',
            parameter_type=ParameterType.DIMENSION,
            nominal_value=Decimal('25.000'),
            upper_tolerance=Decimal('0.050'),  # Max 25.050
            lower_tolerance=Decimal('-0.020'), # Min 24.980
            unit='mm',
            is_ctq=True,
            required_tool_type=ToolType.MICROMETER,
        )

        self.assertEqual(param.upper_limit, Decimal('25.050'))
        self.assertEqual(param.lower_limit, Decimal('24.980'))

        # In tolerance
        passed, msg = param.evaluate_reading(Decimal('25.020'))
        self.assertTrue(passed)
        self.assertIn('within', msg)

        # At lower bound
        passed, msg = param.evaluate_reading(Decimal('24.980'))
        self.assertTrue(passed)

        # Below lower bound (FAIL)
        passed, msg = param.evaluate_reading(Decimal('24.975'))
        self.assertFalse(passed)
        self.assertIn('below lower limit', msg)

        # Above upper bound (FAIL)
        passed, msg = param.evaluate_reading(Decimal('25.055'))
        self.assertFalse(passed)
        self.assertIn('exceeds upper limit', msg)

    def test_inspection_parameter_threshold_evaluation(self):
        """Test MAX and MIN threshold parameter evaluations."""
        param_max = InspectionParameter.objects.create(
            template_revision=self.revision,
            sequence_order=2,
            parameter_name='Surface Roughness Ra 0.8 MAX',
            parameter_type=ParameterType.THRESHOLD,
            threshold_type=ThresholdType.MAX,
            threshold_limit=Decimal('0.800'),
            unit='Ra',
        )

        # Meets MAX
        passed, _ = param_max.evaluate_reading(Decimal('0.650'))
        self.assertTrue(passed)
        passed, _ = param_max.evaluate_reading(Decimal('0.800'))
        self.assertTrue(passed)

        # Exceeds MAX
        passed, msg = param_max.evaluate_reading(Decimal('0.920'))
        self.assertFalse(passed)
        self.assertIn('Exceeds Maximum', msg)

        param_min = InspectionParameter.objects.create(
            template_revision=self.revision,
            sequence_order=3,
            parameter_name='Hardness 45 HRC MIN',
            parameter_type=ParameterType.THRESHOLD,
            threshold_type=ThresholdType.MIN,
            threshold_limit=Decimal('45.000'),
            unit='HRC',
        )

        passed, _ = param_min.evaluate_reading(Decimal('48.000'))
        self.assertTrue(passed)
        passed, msg = param_min.evaluate_reading(Decimal('42.000'))
        self.assertFalse(passed)
        self.assertIn('Below Minimum', msg)

    def test_blueprint_pin_normalized_coordinates(self):
        """Test blueprint pin coordinate normalization and percentage calculations."""
        bp = Blueprint.objects.create(
            template_revision=self.revision,
            title='Shaft Blueprint',
            drawing_file='blueprints/sample.png'
        )

        param = InspectionParameter.objects.create(
            template_revision=self.revision,
            sequence_order=1,
            parameter_name='Pin Location Check',
            parameter_type=ParameterType.DIMENSION,
            nominal_value=Decimal('10.000'),
            is_ctq=True,
        )

        pin = BlueprintPin.objects.create(
            blueprint=bp,
            parameter=param,
            pin_number=1,
            label='Pin 1: Journal',
            coordinate_x=Decimal('0.3540'),
            coordinate_y=Decimal('0.7250'),
        )

        self.assertAlmostEqual(pin.percentage_x, 35.40, places=2)
        self.assertAlmostEqual(pin.percentage_y, 72.50, places=2)
        self.assertTrue(pin.parameter.is_ctq)


class QualityRBACViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.quality_mgr = User.objects.create_user(
            username='qm', password='password123', employee_id='EMP-QM', role=UserRole.QUALITY_MANAGER
        )
        self.quality_eng = User.objects.create_user(
            username='qe', password='password123', employee_id='EMP-QE', role=UserRole.QUALITY_ENGINEER
        )
        self.inspector = User.objects.create_user(
            username='inspector', password='password123', employee_id='EMP-INSP', role=UserRole.QA_FLOOR_INSPECTOR
        )

        self.grade = MaterialGrade.objects.create(
            code='EN-8D', name='Medium Carbon Steel', description='IS 5517 standard'
        )
        self.part = Part.objects.create(
            part_number='PART-GEAR-101', part_name='Pinion Gear', material_grade=self.grade, drawing_number='DWG-101'
        )
        self.template = InspectionTemplate.objects.create(
            part=self.part, template_code='TPL-GEAR-101', title='Gear PDI Plan'
        )
        self.revision = InspectionTemplateRevision.objects.create(
            template=self.template, revision_label='Rev A', created_by=self.quality_eng
        )

    def test_inspector_cannot_access_template_create_view(self):
        """QA Floor Inspector is redirected to dashboard when attempting to create template."""
        self.client.login(username='inspector', password='password123')
        response = self.client.get(reverse('quality:template_create'))
        self.assertRedirects(response, reverse('dashboard:index'))

    def test_quality_engineer_can_access_template_create_view(self):
        """Quality Engineer has permission to create templates."""
        self.client.login(username='qe', password='password123')
        response = self.client.get(reverse('quality:template_create'))
        self.assertEqual(response.status_code, 200)

    def test_quality_engineer_cannot_approve_revision_view(self):
        """Quality Engineer is redirected to dashboard when attempting to approve revision."""
        self.client.login(username='qe', password='password123')
        response = self.client.post(reverse('quality:template_revision_approve', kwargs={'revision_id': self.revision.id}))
        self.assertRedirects(response, reverse('dashboard:index'))

    def test_quality_manager_can_approve_revision_view(self):
        """Quality Manager can approve template revision."""
        self.client.login(username='qm', password='password123')
        response = self.client.post(
            reverse('quality:template_revision_approve', kwargs={'revision_id': self.revision.id}),
            {'approval_notes': 'All checks confirmed'}
        )
        self.assertEqual(response.status_code, 302)  # Redirects to template detail
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, RevisionStatus.APPROVED)


class FloorInspectionAndConcessionTests(TestCase):
    """
    Automated test suite for Phase 4:
    - Dual QR/Barcode Scanning & Workstation/Traveler validation
    - Floor Inspector Tablet workflow & tolerance evaluation
    - Measuring Tool calibration lockout
    - Mandatory Defect Photo enforcement
    - Supervisor Review, Zero-Concession CTQ rule, & Concession approval
    - Inspection Rejection & Lot Quarantine isolation
    - Duplicate inspection prevention and RBAC
    """
    def setUp(self):
        self.client = Client()

        # 1. Users
        self.plant_mgr = User.objects.create_user(
            username='pm_f4', password='password123', employee_id='EMP-PM-F4', role=UserRole.PLANT_MANAGER
        )
        self.quality_mgr = User.objects.create_user(
            username='qm_f4', password='password123', employee_id='EMP-QM-F4', role=UserRole.QUALITY_MANAGER
        )
        self.supervisor = User.objects.create_user(
            username='sup_f4', password='password123', employee_id='EMP-SUP-F4', role=UserRole.SHIFT_SUPERVISOR
        )
        self.quality_eng = User.objects.create_user(
            username='qe_f4', password='password123', employee_id='EMP-QE-F4', role=UserRole.QUALITY_ENGINEER
        )
        self.inspector = User.objects.create_user(
            username='insp_f4', password='password123', employee_id='EMP-INSP-F4', role=UserRole.QA_FLOOR_INSPECTOR
        )

        # 2. Department & Workstations
        self.dept = Department.objects.create(name='Precision Machining Cell', code='PMC-F4')
        self.ws_cnc = Workstation.objects.create(
            department=self.dept,
            name='CNC Turning Lathe 01',
            machine_code='CNC-F4-01',
            qr_code_identifier='QR-CNC-F4-01',
            is_active=True
        )
        self.ws_grind = Workstation.objects.create(
            department=self.dept,
            name='Cylindrical Grinder 01',
            machine_code='GRD-F4-01',
            qr_code_identifier='QR-GRD-F4-01',
            is_active=True
        )

        # 3. Machine PM Logs (Satisfy PM requirements so machines are unlocked by default)
        self.pm_cnc = MachinePMLog.objects.create(
            workstation=self.ws_cnc,
            log_date=timezone.now().date(),
            completed_by=self.supervisor,
            zero_point_verified=True,
            lubrication_level_ok=True,
            safety_interlocks_ok=True,
            spindle_runout_ok=True,
            pneumatic_pressure_ok=True,
            emergency_stop_tested=True,
        )
        self.pm_grind = MachinePMLog.objects.create(
            workstation=self.ws_grind,
            log_date=timezone.now().date(),
            completed_by=self.supervisor,
            zero_point_verified=True,
            lubrication_level_ok=True,
            safety_interlocks_ok=True,
            spindle_runout_ok=True,
            pneumatic_pressure_ok=True,
            emergency_stop_tested=True,
        )

        # 4. Measuring Tools (Calibrated vs Expired)
        self.calibrated_micrometer = InspectionTool.objects.create(
            tool_id='MIC-F4-001',
            name='Digital Outside Micrometer 0-25mm',
            tool_type=ToolType.MICROMETER,
            serial_number='SN-MIC-F4-001',
            status=ToolStatus.CALIBRATED,
            calibration_date=timezone.now().date() - timedelta(days=20),
            calibration_expiry_date=timezone.now().date() + timedelta(days=345),
        )
        self.calibrated_caliper = InspectionTool.objects.create(
            tool_id='CAL-F4-001',
            name='Digital Vernier Caliper 0-150mm',
            tool_type=ToolType.CALIPER,
            serial_number='SN-CAL-F4-001',
            status=ToolStatus.CALIBRATED,
            calibration_date=timezone.now().date() - timedelta(days=20),
            calibration_expiry_date=timezone.now().date() + timedelta(days=345),
        )
        self.expired_micrometer = InspectionTool.objects.create(
            tool_id='MIC-F4-EXP',
            name='Expired Micrometer 25-50mm',
            tool_type=ToolType.MICROMETER,
            serial_number='SN-MIC-EXP-999',
            status=ToolStatus.CALIBRATED,
            calibration_date=timezone.now().date() - timedelta(days=400),
            calibration_expiry_date=timezone.now().date() - timedelta(days=35),
        )
        self.expired_tool = self.expired_micrometer

        # 5. Material, Part, Work Order & Traveler
        self.grade = MaterialGrade.objects.create(
            code='AISI-4140-F4', name='Chromoly Steel F4', description='High Tensile Steel'
        )
        self.part = Part.objects.create(
            part_number='PART-F4-SHAFT',
            part_name='Precision Turbine Shaft',
            material_grade=self.grade,
            drawing_number='DWG-F4-77',
        )
        self.raw_lot = RawMaterialIntake.objects.create(
            lot_number='LOT-F4-001',
            heat_number='HEAT-F4-88',
            supplier_name='ArcelorMittal',
            purchase_order_no='PO-F4-500',
            material_grade=self.grade,
            quantity_received=Decimal('1000.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.IN_STORE,
            received_by=self.supervisor,
            mtc_verified=True,
            mtc_verified_by=self.quality_mgr,
            mtc_verified_at=timezone.now(),
            lab_status=LabStatus.PASSED,
            barcode_identifier='RAW-LOT-F4-001',
        )
        self.work_order = WorkOrder.objects.create(
            work_order_number='WO-F4-101',
            part=self.part,
            raw_material_lot=self.raw_lot,
            target_quantity=50,
            status=WorkOrderStatus.RELEASED,
            released_by=self.supervisor,
            released_at=timezone.now(),
        )
        self.traveler = JobTraveler.objects.create(
            work_order=self.work_order,
            traveler_barcode='TRV-F4-101-01',
            status=JobTravelerStatus.ACTIVE,
        )

        # 6. Inspection Template, Revision, & Parameters
        self.template = InspectionTemplate.objects.create(
            part=self.part,
            template_code='TPL-F4-101',
            title='Turbine Shaft In-Process Checklist',
            template_type=TemplateType.IN_PROCESS,
        )
        self.revision = InspectionTemplateRevision.objects.create(
            template=self.template,
            revision_label='Rev 1',
            status=RevisionStatus.APPROVED,
            created_by=self.quality_eng,
            approved_by=self.quality_mgr,
            approved_at=timezone.now(),
        )
        self.param_ctq = InspectionParameter.objects.create(
            template_revision=self.revision,
            sequence_order=1,
            parameter_name='Bearing Journal Ø25.000 (CTQ)',
            parameter_type=ParameterType.DIMENSION,
            nominal_value=Decimal('25.000'),
            upper_tolerance=Decimal('0.050'),   # Max: 25.050
            lower_tolerance=Decimal('-0.020'),  # Min: 24.980
            unit='mm',
            is_ctq=True,
            required_tool_type=ToolType.MICROMETER,
        )
        self.param_non_ctq = InspectionParameter.objects.create(
            template_revision=self.revision,
            sequence_order=2,
            parameter_name='Overall Length 150.000',
            parameter_type=ParameterType.DIMENSION,
            nominal_value=Decimal('150.000'),
            upper_tolerance=Decimal('0.100'),   # Max: 150.100
            lower_tolerance=Decimal('-0.100'),  # Min: 149.900
            unit='mm',
            is_ctq=False,
            required_tool_type=ToolType.CALIPER,
        )

        # 7. Traveler Operations
        self.op10 = TravelerOperation.objects.create(
            traveler=self.traveler,
            operation_sequence=10,
            operation_name='CNC Turning & Profiling',
            workstation=self.ws_cnc,
            inspection_template_revision=self.revision,
            status=OperationStatus.PENDING,
        )
        self.op20 = TravelerOperation.objects.create(
            traveler=self.traveler,
            operation_sequence=20,
            operation_name='Finish Cylindrical Grinding',
            workstation=self.ws_grind,
            status=OperationStatus.PENDING,
        )

    def test_dual_scan_workstation_mismatch_blocked(self):
        """Scanning a workstation that doesn't match the traveler active operation is blocked and logged."""
        self.client.login(username='insp_f4', password='password123')
        # op10 is on ws_cnc (QR-CNC-F4-01), but inspector scans ws_grind (QR-GRD-F4-01)
        response = self.client.post(reverse('quality:floor_scan_validate'), {
            'station_code': self.ws_grind.qr_code_identifier,
            'traveler_code': self.traveler.traveler_barcode,
        }, follow=True)

        self.assertRedirects(response, reverse('quality:floor_scan'))
        messages = list(response.context['messages'])
        self.assertTrue(any('Workstation Mismatch' in m.message for m in messages))

        # Check Audit Log security alert recorded
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.SECURITY_ALERT,
                model_name='TravelerOperation',
                details__contains='Workstation Mismatch'
            ).exists()
        )

    def test_dual_scan_workstation_pm_overdue_blocked(self):
        """Scanning a workstation with overdue daily PM is blocked by server-side interlock."""
        # Invalidate PM on ws_cnc
        self.pm_cnc.delete()
        self.ws_cnc.refresh_from_db()
        self.assertFalse(self.ws_cnc.can_start_job()[0])

        self.client.login(username='insp_f4', password='password123')
        response = self.client.post(reverse('quality:floor_scan_validate'), {
            'station_code': self.ws_cnc.qr_code_identifier,
            'traveler_code': self.traveler.traveler_barcode,
        }, follow=True)

        self.assertRedirects(response, reverse('quality:floor_scan'))
        messages = list(response.context['messages'])
        self.assertTrue(any('Workstation Lockout' in m.message for m in messages))

        # Verify PM lockout logged in audit trail
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.PM_LOCKOUT,
                model_name='Workstation'
            ).exists()
        )

    def test_expired_measuring_tool_rejected_on_server(self):
        """Using an expired gauge raises ValidationError and blocks measurement submission."""
        self.assertFalse(self.expired_tool.is_calibration_valid)
        with self.assertRaises(ValidationError) as ctx:
            self.expired_tool.validate_for_measurement()
        self.assertIn("Expired Tool Calibration", str(ctx.exception))

        # Test model-level measurement clean() enforcement
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-TEST-EXP-01',
            traveler_operation=self.op10,
            template_revision=self.revision,
            workstation=self.ws_cnc,
            inspector=self.inspector,
            station_qr_scanned=self.ws_cnc.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
        )
        meas = InspectionMeasurement(
            inspection=inspection,
            parameter=self.param_ctq,
            measuring_tool=self.expired_tool,
            measured_value=Decimal('25.010'),
        )
        with self.assertRaises(ValidationError) as ctx:
            meas.clean()
        self.assertIn("Expired Tool Calibration", str(ctx.exception))
        inspection.delete()

        # Test view-level enforcement on tablet submission
        self.client.login(username='insp_f4', password='password123')
        post_data = {
            f"param_{self.param_ctq.id}": "25.010",
            f"tool_{self.param_ctq.id}": str(self.expired_tool.id),
            f"param_{self.param_non_ctq.id}": "150.000",
            f"tool_{self.param_non_ctq.id}": str(self.calibrated_caliper.id),
        }
        response = self.client.post(
            reverse('quality:floor_inspect', kwargs={'op_id': self.op10.id}),
            post_data,
            follow=True
        )
        messages = list(response.context['messages'])
        self.assertTrue(any("Expired Tool Calibration" in m.message for m in messages))
        # Ensure no new inspection was saved
        self.assertEqual(FloorInspection.objects.filter(traveler_operation=self.op10).count(), 0)

    def test_defect_photo_validation(self):
        """validate_defect_photo_file validates allowed extensions and file size limits."""
        # Valid PNG file passes
        valid_file = SimpleUploadedFile("part_defect.png", b"test content", content_type="image/png")
        validate_defect_photo_file(valid_file)

        # Invalid extension raises ValidationError
        invalid_ext = SimpleUploadedFile("macro.exe", b"binary content", content_type="application/octet-stream")
        with self.assertRaises(ValidationError) as ctx:
            validate_defect_photo_file(invalid_ext)
        self.assertIn("Invalid file format", str(ctx.exception))

        # Oversized file (> 5MB) raises ValidationError
        oversized = SimpleUploadedFile("huge_photo.jpg", b"0" * (6 * 1024 * 1024), content_type="image/jpeg")
        with self.assertRaises(ValidationError) as ctx:
            validate_defect_photo_file(oversized)
        self.assertIn("exceeds 5MB limit", str(ctx.exception))

    def test_mandatory_defect_photo_enforcement(self):
        """Out-of-tolerance inspection requires at least one defect photo under BRD Section 5.4."""
        self.client.login(username='insp_f4', password='password123')

        # 1. Submit out-of-tolerance reading without defect photo -> Must be rejected
        post_data_no_photo = {
            f"param_{self.param_ctq.id}": "25.010",  # in tolerance
            f"tool_{self.param_ctq.id}": str(self.calibrated_micrometer.id),
            f"param_{self.param_non_ctq.id}": "150.350",  # OUT OF TOLERANCE (Max 150.100)
            f"tool_{self.param_non_ctq.id}": str(self.calibrated_caliper.id),
            'inspector_notes': 'Length exceeds upper limit by 0.25mm',
        }
        response = self.client.post(
            reverse('quality:floor_inspect', kwargs={'op_id': self.op10.id}),
            post_data_no_photo,
            follow=True
        )
        messages = list(response.context['messages'])
        self.assertTrue(any("Mandatory Defect Photo" in m.message for m in messages))
        self.assertEqual(FloorInspection.objects.filter(traveler_operation=self.op10).count(), 0)

        # 2. Submit same out-of-tolerance reading WITH a defect photo -> Must succeed
        test_photo = SimpleUploadedFile("length_gauge_reading.jpg", b"fake image bytes", content_type="image/jpeg")
        post_data_with_photo = {
            f"param_{self.param_ctq.id}": "25.010",
            f"tool_{self.param_ctq.id}": str(self.calibrated_micrometer.id),
            f"param_{self.param_non_ctq.id}": "150.350",
            f"tool_{self.param_non_ctq.id}": str(self.calibrated_caliper.id),
            'defect_photos': test_photo,
            'photo_caption': 'Digital caliper reading 150.350mm on shaft shoulder',
        }
        response = self.client.post(
            reverse('quality:floor_inspect', kwargs={'op_id': self.op10.id}),
            post_data_with_photo,
            follow=True
        )
        self.assertRedirects(response, reverse('quality:floor_scan'))
        inspection = FloorInspection.objects.filter(traveler_operation=self.op10).first()
        self.assertIsNotNone(inspection)
        self.assertEqual(inspection.status, FloorInspectionStatus.PENDING_REVIEW)
        self.assertFalse(inspection.overall_in_tolerance)
        self.assertFalse(inspection.has_ctq_defect)  # non-CTQ failed, CTQ passed
        self.assertEqual(inspection.defect_photos.count(), 1)

    def test_valid_inspection_submission_routes_to_supervisor_queue(self):
        """Within-tolerance inspection is logged and routes to supervisor queue for sign-off."""
        self.client.login(username='insp_f4', password='password123')
        post_data = {
            f"param_{self.param_ctq.id}": "25.015",  # in tolerance (24.980 - 25.050)
            f"tool_{self.param_ctq.id}": str(self.calibrated_micrometer.id),
            f"param_{self.param_non_ctq.id}": "150.020",  # in tolerance (149.900 - 150.100)
            f"tool_{self.param_non_ctq.id}": str(self.calibrated_caliper.id),
            'inspector_notes': 'All dimensions verified and clean',
        }
        response = self.client.post(
            reverse('quality:floor_inspect', kwargs={'op_id': self.op10.id}),
            post_data,
            follow=True
        )
        self.assertRedirects(response, reverse('quality:floor_scan'))

        inspection = FloorInspection.objects.filter(traveler_operation=self.op10).first()
        self.assertIsNotNone(inspection)
        self.assertEqual(inspection.status, FloorInspectionStatus.PENDING_REVIEW)
        self.assertTrue(inspection.overall_in_tolerance)
        self.assertFalse(inspection.has_ctq_defect)
        self.assertEqual(inspection.measurements.count(), 2)

        # Verify audit trail
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.INSPECTION_ENTRY,
                model_name='FloorInspection',
                object_id=str(inspection.id)
            ).exists()
        )

    def test_ctq_zero_concession_enforcement(self):
        """
        BRD Section 4.3 & 6.1: Zero concessions are permitted on Critical-to-Quality (CTQ) parameters.
        Server recalculates CTQ failure directly from database measurements and rejects concession.
        """
        # Create an inspection where CTQ parameter failed (OD = 25.100 exceeds upper limit 25.050)
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-CTQ-FAIL-01',
            traveler_operation=self.op10,
            template_revision=self.revision,
            workstation=self.ws_cnc,
            inspector=self.inspector,
            station_qr_scanned=self.ws_cnc.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.PENDING_REVIEW,
        )
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param_ctq,
            measuring_tool=self.calibrated_micrometer,
            measured_value=Decimal('25.100'),  # OUT OF TOLERANCE
        )
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param_non_ctq,
            measuring_tool=self.calibrated_caliper,
            measured_value=Decimal('150.000'),  # In tolerance
        )
        inspection.recalculate_tolerance_and_ctq()
        self.assertFalse(inspection.overall_in_tolerance)
        self.assertTrue(inspection.has_ctq_defect)

        # Client / malicious tampering simulation: reset flag on model
        inspection.has_ctq_defect = False
        inspection.save(update_fields=['has_ctq_defect'])

        # Server recalculation must catch the CTQ failure and raise ValidationError
        with self.assertRaises(ValidationError) as ctx:
            inspection.grant_concession(
                user=self.quality_mgr,
                reason_code=ConcessionReason.ENGINEERING_DEVIATION,
                justification='Requesting variance for customer urgent order'
            )
        self.assertIn("Zero-Concession Violation", str(ctx.exception))
        self.assertIn("Critical-to-Quality", str(ctx.exception))

        # Status must remain PENDING_REVIEW and no ConcessionRecord created
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, FloorInspectionStatus.PENDING_REVIEW)
        self.assertFalse(hasattr(inspection, 'concession_record'))

        # Also test via Supervisor Review View POST
        self.client.login(username='qm_f4', password='password123')
        response = self.client.post(
            reverse('quality:supervisor_review', kwargs={'inspection_id': inspection.id}),
            {
                'action': 'concession',
                'reason_code': ConcessionReason.ENGINEERING_DEVIATION,
                'engineering_justification': 'Customer agreed to accept oversize shaft',
            },
            follow=True
        )
        messages = list(response.context['messages'])
        self.assertTrue(any("Zero-Concession Violation" in m.message for m in messages))
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, FloorInspectionStatus.PENDING_REVIEW)

    def test_non_ctq_deviation_concession_workflow(self):
        """Concession for non-CTQ parameters is permitted with Quality Manager approval."""
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-NON-CTQ-01',
            traveler_operation=self.op10,
            template_revision=self.revision,
            workstation=self.ws_cnc,
            inspector=self.inspector,
            station_qr_scanned=self.ws_cnc.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.PENDING_REVIEW,
        )
        # CTQ passes, Non-CTQ fails
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param_ctq,
            measuring_tool=self.calibrated_micrometer,
            measured_value=Decimal('25.010'),  # In tolerance
        )
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param_non_ctq,
            measuring_tool=self.calibrated_caliper,
            measured_value=Decimal('150.250'),  # OUT OF TOLERANCE (Max 150.100)
        )
        inspection.recalculate_tolerance_and_ctq()
        self.assertFalse(inspection.overall_in_tolerance)
        self.assertFalse(inspection.has_ctq_defect)

        # Quality Manager grants concession
        self.client.login(username='qm_f4', password='password123')
        response = self.client.post(
            reverse('quality:supervisor_review', kwargs={'inspection_id': inspection.id}),
            {
                'action': 'concession',
                'reason_code': ConcessionReason.ENGINEERING_DEVIATION,
                'engineering_justification': 'Overall length +0.15mm is within non-functional clearance allowance.',
            },
            follow=True
        )
        self.assertRedirects(response, reverse('quality:supervisor_queue'))

        inspection.refresh_from_db()
        self.assertEqual(inspection.status, FloorInspectionStatus.CONCESSION_APPROVED)
        self.assertEqual(inspection.reviewed_by, self.quality_mgr)

        # Verify concession record created
        concession = inspection.concession_record
        self.assertIsNotNone(concession)
        self.assertTrue(concession.concession_number.startswith('CONC-'))
        self.assertEqual(concession.reason_code, ConcessionReason.ENGINEERING_DEVIATION)

        # Verify operation signed off
        self.op10.refresh_from_db()
        self.assertEqual(self.op10.status, OperationStatus.COMPLETED)

        # Verify Audit Log
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.CONCESSION_ISSUED,
                model_name='FloorInspection',
                object_id=str(inspection.id)
            ).exists()
        )

    def test_supervisor_approve_workflow(self):
        """Shift Supervisor can formally approve a conforming inspection and clear the operation."""
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-APP-01',
            traveler_operation=self.op10,
            template_revision=self.revision,
            workstation=self.ws_cnc,
            inspector=self.inspector,
            station_qr_scanned=self.ws_cnc.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.PENDING_REVIEW,
        )
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param_ctq,
            measuring_tool=self.calibrated_micrometer,
            measured_value=Decimal('25.010'),
        )
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param_non_ctq,
            measuring_tool=self.calibrated_caliper,
            measured_value=Decimal('150.000'),
        )
        inspection.recalculate_tolerance_and_ctq()
        self.assertTrue(inspection.overall_in_tolerance)

        self.client.login(username='sup_f4', password='password123')
        response = self.client.post(
            reverse('quality:supervisor_review', kwargs={'inspection_id': inspection.id}),
            {
                'action': 'approve',
                'notes': 'All dimensions conform to drawing specifications.',
            },
            follow=True
        )
        self.assertRedirects(response, reverse('quality:supervisor_queue'))

        inspection.refresh_from_db()
        self.assertEqual(inspection.status, FloorInspectionStatus.APPROVED)
        self.assertEqual(inspection.reviewed_by, self.supervisor)

        self.op10.refresh_from_db()
        self.assertEqual(self.op10.status, OperationStatus.COMPLETED)

        # Op 20 is now unlocked and can start
        can_op20_start, _ = self.op20.can_start()
        self.assertTrue(can_op20_start)

        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.INSPECTION_APPROVED,
                model_name='FloorInspection',
                object_id=str(inspection.id)
            ).exists()
        )

    def test_inspection_rejection_quarantines_job_traveler_only(self):
        """
        Inspection rejection quarantines the affected Job Traveler and blocks downstream steps,
        without quarantining unrelated raw material inventory.
        """
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-REJ-01',
            traveler_operation=self.op10,
            template_revision=self.revision,
            workstation=self.ws_cnc,
            inspector=self.inspector,
            station_qr_scanned=self.ws_cnc.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.PENDING_REVIEW,
        )
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param_ctq,
            measuring_tool=self.calibrated_micrometer,
            measured_value=Decimal('25.120'),  # Severe oversize
        )

        self.client.login(username='sup_f4', password='password123')
        response = self.client.post(
            reverse('quality:supervisor_review', kwargs={'inspection_id': inspection.id}),
            {
                'action': 'reject',
                'rejection_reason': 'Severe oversize on journal diameter. Cannot be salvaged.',
            },
            follow=True
        )
        self.assertRedirects(response, reverse('quality:supervisor_queue'))

        inspection.refresh_from_db()
        self.assertEqual(inspection.status, FloorInspectionStatus.REJECTED_QUARANTINED)

        # 1. Affected Job Traveler is quarantined
        self.traveler.refresh_from_db()
        self.assertEqual(self.traveler.status, JobTravelerStatus.QUARANTINED)

        # 2. Raw Material Lot in store is NOT modified (isolated quarantine scope)
        self.raw_lot.refresh_from_db()
        self.assertEqual(self.raw_lot.status, IntakeStatus.IN_STORE)

        # 3. Downstream operations are blocked
        can_op20_start, op20_reason = self.op20.can_start()
        self.assertFalse(can_op20_start)

        # 4. Audit Log records rejection and quarantine moves
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.INSPECTION_REJECTED,
                model_name='FloorInspection'
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.QUARANTINE_MOVED,
                model_name='JobTraveler',
                object_id=str(self.traveler.id)
            ).exists()
        )

    def test_duplicate_inspection_prevention_and_double_decision(self):
        """Prevent submitting multiple active inspections and double supervisor decisions."""
        # Create an inspection in PENDING_REVIEW
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-DUP-01',
            traveler_operation=self.op10,
            template_revision=self.revision,
            workstation=self.ws_cnc,
            inspector=self.inspector,
            station_qr_scanned=self.ws_cnc.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.PENDING_REVIEW,
        )

        # Inspector attempts to submit a second inspection for op10
        self.client.login(username='insp_f4', password='password123')
        response = self.client.post(
            reverse('quality:floor_inspect', kwargs={'op_id': self.op10.id}),
            {
                f"param_{self.param_ctq.id}": "25.010",
                f"tool_{self.param_ctq.id}": str(self.calibrated_micrometer.id),
            },
            follow=True
        )
        self.assertRedirects(response, reverse('quality:floor_scan'))
        messages = list(response.context['messages'])
        self.assertTrue(any("already has an active inspection" in m.message for m in messages))

        # Supervisor formally approves
        inspection.approve(self.supervisor, notes="Approved")
        self.assertEqual(inspection.status, FloorInspectionStatus.APPROVED)

        # Attempting another decision on finalized inspection raises ValidationError
        with self.assertRaises(ValidationError) as ctx:
            inspection.approve(self.supervisor)
        self.assertIn("already finalized", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            inspection.reject_and_quarantine(self.supervisor, reason="Duplicate reject")
        self.assertIn("already finalized", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            inspection.grant_concession(self.quality_mgr, ConcessionReason.ENGINEERING_DEVIATION, "Justification")
        self.assertIn("already finalized", str(ctx.exception))

    def test_floor_inspection_and_review_rbac_security(self):
        """Role-Based Access Control: Floor inspector cannot access supervisor review queue/actions."""
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-RBAC-01',
            traveler_operation=self.op10,
            template_revision=self.revision,
            workstation=self.ws_cnc,
            inspector=self.inspector,
            station_qr_scanned=self.ws_cnc.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.PENDING_REVIEW,
        )

        # Inspector attempts to access supervisor review queue -> Redirected to dashboard
        self.client.login(username='insp_f4', password='password123')
        response = self.client.get(reverse('quality:supervisor_queue'))
        self.assertRedirects(response, reverse('dashboard:index'))

        # Inspector attempts to access supervisor review detail view -> Redirected to dashboard
        response = self.client.get(reverse('quality:supervisor_review', kwargs={'inspection_id': inspection.id}))
        self.assertRedirects(response, reverse('dashboard:index'))

        # Supervisor CAN access queue and review
        self.client.login(username='sup_f4', password='password123')
        response = self.client.get(reverse('quality:supervisor_queue'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('quality:supervisor_review', kwargs={'inspection_id': inspection.id}))
        self.assertEqual(response.status_code, 200)


class FinalPDITests(TestCase):
    """
    Automated test suite for Phase 5A: Final Pre-Dispatch Inspection (PDI).
    - Server-side verification that every preceding operation is completed
    - Server-side check that all process hold timers have elapsed
    - Protection against executing PDI on quarantined travelers
    - Measurement capture and routing to supervisor review
    - Quality approval marking traveler as COMPLETED
    - Role-based access control and audit trail logging
    """
    def setUp(self):
        self.client = Client()

        # Users
        self.plant_mgr = User.objects.create_user(
            username='pm_pdi', password='password123', employee_id='EMP-PM-PDI', role=UserRole.PLANT_MANAGER
        )
        self.quality_mgr = User.objects.create_user(
            username='qm_pdi', password='password123', employee_id='EMP-QM-PDI', role=UserRole.QUALITY_MANAGER
        )
        self.supervisor = User.objects.create_user(
            username='sup_pdi', password='password123', employee_id='EMP-SUP-PDI', role=UserRole.SHIFT_SUPERVISOR
        )
        self.quality_eng = User.objects.create_user(
            username='qe_pdi', password='password123', employee_id='EMP-QE-PDI', role=UserRole.QUALITY_ENGINEER
        )
        self.inspector = User.objects.create_user(
            username='insp_pdi', password='password123', employee_id='EMP-INSP-PDI', role=UserRole.QA_FLOOR_INSPECTOR
        )

        # Department & Workstations
        self.dept = Department.objects.create(name='Assembly & Quality Bay', code='ASSY-PDI')
        self.ws_turning = Workstation.objects.create(
            department=self.dept, name='CNC Lathe', machine_code='CNC-PDI-01',
            qr_code_identifier='QR-CNC-PDI-01', is_active=True
        )
        self.ws_heat = Workstation.objects.create(
            department=self.dept, name='Heat Oven', machine_code='OVEN-PDI-01',
            qr_code_identifier='QR-OVEN-PDI-01', is_active=True
        )
        self.ws_pdi = Workstation.objects.create(
            department=self.dept, name='PDI Inspection Station', machine_code='PDI-BAY-01',
            qr_code_identifier='QR-PDI-BAY-01', is_active=True
        )

        # Daily PM logs to keep machines unlocked
        for ws in [self.ws_turning, self.ws_heat, self.ws_pdi]:
            MachinePMLog.objects.create(
                workstation=ws,
                log_date=timezone.now().date(),
                completed_by=self.supervisor,
                zero_point_verified=True, lubrication_level_ok=True, safety_interlocks_ok=True,
                spindle_runout_ok=True, pneumatic_pressure_ok=True, emergency_stop_tested=True,
            )

        # Calibrated Tool
        self.tool = InspectionTool.objects.create(
            tool_id='MIC-PDI-01', name='Precision Micrometer', tool_type=ToolType.MICROMETER,
            serial_number='SN-PDI-01', status=ToolStatus.CALIBRATED,
            calibration_date=timezone.now().date() - timedelta(days=10),
            calibration_expiry_date=timezone.now().date() + timedelta(days=350),
        )

        # Material & Part
        self.grade = MaterialGrade.objects.create(code='EN-24-PDI', name='Alloy Steel PDI', description='Standard')
        self.part = Part.objects.create(
            part_number='PART-PDI-99', part_name='Transmission Gear PDI', material_grade=self.grade,
            drawing_number='DWG-PDI-99'
        )
        self.raw_lot = RawMaterialIntake.objects.create(
            lot_number='LOT-PDI-99', heat_number='HEAT-PDI-99', supplier_name='Tata Steel',
            purchase_order_no='PO-PDI-99', material_grade=self.grade, quantity_received=Decimal('200.00'),
            unit=QuantityUnit.KG, status=IntakeStatus.IN_STORE, received_by=self.supervisor,
            mtc_verified=True, mtc_verified_by=self.quality_mgr, mtc_verified_at=timezone.now(),
            lab_status=LabStatus.PASSED, barcode_identifier='RAW-LOT-PDI-99',
        )
        self.work_order = WorkOrder.objects.create(
            work_order_number='WO-PDI-99', part=self.part, raw_material_lot=self.raw_lot,
            target_quantity=10, status=WorkOrderStatus.RELEASED, released_by=self.supervisor,
            released_at=timezone.now(),
        )
        self.traveler = JobTraveler.objects.create(
            work_order=self.work_order, traveler_barcode='TRV-PDI-99', status=JobTravelerStatus.ACTIVE
        )

        # Inspection Template (FINAL_PDI)
        self.template = InspectionTemplate.objects.create(
            part=self.part, template_code='TPL-PDI-99', title='Transmission Gear PDI Plan',
            template_type=TemplateType.FINAL_PDI
        )
        self.revision = InspectionTemplateRevision.objects.create(
            template=self.template, revision_label='Rev 1', status=RevisionStatus.APPROVED,
            created_by=self.quality_eng, approved_by=self.quality_mgr, approved_at=timezone.now()
        )
        self.param = InspectionParameter.objects.create(
            template_revision=self.revision, sequence_order=1, parameter_name='Pitch Diameter Ø50.000 (CTQ)',
            parameter_type=ParameterType.DIMENSION, nominal_value=Decimal('50.000'),
            upper_tolerance=Decimal('0.030'), lower_tolerance=Decimal('-0.030'), unit='mm',
            is_ctq=True, required_tool_type=ToolType.MICROMETER
        )

        # Traveler Operations: Op 10, Op 20 (Heat Treat with hold), Op 50 (PDI)
        self.op10 = TravelerOperation.objects.create(
            traveler=self.traveler, operation_sequence=10, operation_name='CNC Rough Machining',
            workstation=self.ws_turning, status=OperationStatus.COMPLETED,
            completed_by=self.supervisor, completed_at=timezone.now()
        )
        self.op20 = TravelerOperation.objects.create(
            traveler=self.traveler, operation_sequence=20, operation_name='Induction Heat Treatment',
            workstation=self.ws_heat, requires_hold_time=True, hold_duration_minutes=120,
            status=OperationStatus.COMPLETED, completed_by=self.supervisor, completed_at=timezone.now(),
            hold_start_time=timezone.now() - timedelta(minutes=130),
            hold_release_time=timezone.now() - timedelta(minutes=10),  # expired hold
        )
        self.op50 = TravelerOperation.objects.create(
            traveler=self.traveler, operation_sequence=50, operation_name='Final Pre-Dispatch Inspection (PDI) & Wash',
            workstation=self.ws_pdi, inspection_template_revision=self.revision, status=OperationStatus.READY
        )

    def test_pdi_operation_lookup(self):
        """JobTraveler.get_pdi_operation correctly finds the operation with FINAL_PDI template."""
        pdi_op = self.traveler.get_pdi_operation()
        self.assertIsNotNone(pdi_op)
        self.assertEqual(pdi_op.operation_sequence, 50)
        self.assertEqual(pdi_op.inspection_template_revision.template.template_type, TemplateType.FINAL_PDI)

    def test_pdi_blocked_when_upstream_operations_incomplete(self):
        """Server-side interlock blocks PDI if any preceding operation is not completed."""
        # Reset Op 10 to PENDING
        self.op10.status = OperationStatus.PENDING
        self.op10.save(update_fields=['status'])

        is_ready, reason = self.traveler.is_ready_for_pdi()
        self.assertFalse(is_ready)
        self.assertIn("Sequential Routing Lockout", reason)
        self.assertIn("Op 10", reason)

        # Attempt to execute via view -> blocked and logged
        self.client.login(username='insp_pdi', password='password123')
        response = self.client.get(
            reverse('quality:pdi_execute', kwargs={'traveler_id': self.traveler.id}),
            follow=True
        )
        self.assertRedirects(response, reverse('quality:pdi_queue'))
        messages = list(response.context['messages'])
        self.assertTrue(any("Sequential Routing Lockout" in m.message for m in messages))

        # Check Audit Log lockout
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ActionType.ROUTING_LOCKOUT,
                model_name='JobTraveler',
                object_id=str(self.traveler.id)
            ).exists()
        )

    def test_pdi_blocked_when_hold_timer_active(self):
        """Server-side interlock blocks PDI if preceding operation has an active hold timer."""
        # Set Op 20 hold to unexpired (60 minutes remaining)
        self.op20.hold_start_time = timezone.now()
        self.op20.hold_release_time = timezone.now() + timedelta(minutes=60)
        self.op20.save(update_fields=['hold_start_time', 'hold_release_time'])

        is_ready, reason = self.traveler.is_ready_for_pdi()
        self.assertFalse(is_ready)
        self.assertIn("Process Hold Active", reason)

        self.client.login(username='insp_pdi', password='password123')
        response = self.client.get(
            reverse('quality:pdi_execute', kwargs={'traveler_id': self.traveler.id}),
            follow=True
        )
        self.assertRedirects(response, reverse('quality:pdi_queue'))
        messages = list(response.context['messages'])
        self.assertTrue(any("Process Hold Active" in m.message for m in messages))

    def test_pdi_blocked_when_traveler_is_quarantined(self):
        """PDI is strictly blocked if traveler is quarantined."""
        self.traveler.status = JobTravelerStatus.QUARANTINED
        self.traveler.save(update_fields=['status'])

        is_ready, reason = self.traveler.is_ready_for_pdi()
        self.assertFalse(is_ready)
        self.assertIn("QUALITY QUARANTINE", reason)

        self.client.login(username='insp_pdi', password='password123')
        response = self.client.get(
            reverse('quality:pdi_execute', kwargs={'traveler_id': self.traveler.id}),
            follow=True
        )
        self.assertRedirects(response, reverse('quality:pdi_queue'))
        messages = list(response.context['messages'])
        self.assertTrue(any("QUALITY QUARANTINE" in m.message for m in messages))

    def test_pdi_execution_records_measurements_and_routes_to_review(self):
        """Ready traveler launches PDI inspection tablet, records readings, and routes to review queue."""
        is_ready, _ = self.traveler.is_ready_for_pdi()
        self.assertTrue(is_ready)

        self.client.login(username='insp_pdi', password='password123')
        # Execute link prepares verified session and routes to floor inspect
        response = self.client.get(reverse('quality:pdi_execute', kwargs={'traveler_id': self.traveler.id}))
        self.assertRedirects(response, reverse('quality:floor_inspect', kwargs={'op_id': self.op50.id}))

        # Submit valid PDI measurement reading
        post_data = {
            f"param_{self.param.id}": "50.010",
            f"tool_{self.param.id}": str(self.tool.id),
            'inspector_notes': 'Final PDI clean, zero defects detected',
        }
        submit_response = self.client.post(
            reverse('quality:floor_inspect', kwargs={'op_id': self.op50.id}),
            post_data,
            follow=True
        )
        self.assertRedirects(submit_response, reverse('quality:floor_scan'))

        # Verify inspection record created in PENDING_REVIEW
        pdi_insp = self.traveler.get_pdi_inspection()
        self.assertIsNotNone(pdi_insp)
        self.assertEqual(pdi_insp.status, FloorInspectionStatus.PENDING_REVIEW)
        self.assertTrue(pdi_insp.overall_in_tolerance)
        self.assertFalse(pdi_insp.has_ctq_defect)
        self.assertFalse(self.traveler.is_pdi_approved())

    def test_pdi_quality_approval_clears_traveler_to_completed(self):
        """Quality Manager approval of Final PDI marks operation and entire traveler as COMPLETED."""
        # Create PDI inspection in PENDING_REVIEW
        inspection = FloorInspection.objects.create(
            inspection_number='INSP-PDI-PASS-01',
            traveler_operation=self.op50,
            template_revision=self.revision,
            workstation=self.ws_pdi,
            inspector=self.inspector,
            station_qr_scanned=self.ws_pdi.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.PENDING_REVIEW,
        )
        InspectionMeasurement.objects.create(
            inspection=inspection,
            parameter=self.param,
            measuring_tool=self.tool,
            measured_value=Decimal('50.005'),
        )
        inspection.recalculate_tolerance_and_ctq()

        # Quality Manager approves Final PDI
        self.client.login(username='qm_pdi', password='password123')
        response = self.client.post(
            reverse('quality:supervisor_review', kwargs={'inspection_id': inspection.id}),
            {'action': 'approve', 'notes': 'PDI sign-off granted. Released for packaging.'},
            follow=True
        )
        self.assertRedirects(response, reverse('quality:supervisor_queue'))

        inspection.refresh_from_db()
        self.assertEqual(inspection.status, FloorInspectionStatus.APPROVED)
        self.assertEqual(inspection.reviewed_by, self.quality_mgr)

        # Traveler is now PDI-approved and completed
        self.assertTrue(self.traveler.is_pdi_approved())
        self.op50.refresh_from_db()
        self.assertEqual(self.op50.status, OperationStatus.COMPLETED)
        self.traveler.refresh_from_db()
        self.assertEqual(self.traveler.status, JobTravelerStatus.COMPLETED)

    def test_pdi_queue_view_rbac_and_filtering(self):
        """PDI queue is accessible to authorized shopfloor roles with status filtering."""
        # Unauthenticated user redirected to login
        response = self.client.get(reverse('quality:pdi_queue'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('quality:pdi_queue')}")

        # QA Floor Inspector can access queue
        self.client.login(username='insp_pdi', password='password123')
        response = self.client.get(reverse('quality:pdi_queue'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.traveler.traveler_barcode)

        # Filter by stage=ready
        response = self.client.get(reverse('quality:pdi_queue') + '?stage=ready')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ready for Final PDI')


class CertificateOfConformanceTests(TestCase):
    """
    Automated test suite for Phase 5B: Certificate of Conformance (CoC).
    Conforms to BRD Section 11 (CoC Generation, Verification, & Shipping Interlocks).
    """
    def setUp(self):
        # 1. Factory Users
        self.qm = User.objects.create_user(
            username='qm_coc', employee_id='EMP-QM01', role=UserRole.QUALITY_MANAGER
        )
        self.qm.set_password('password123')
        self.qm.save()

        self.qe = User.objects.create_user(
            username='qe_coc', employee_id='EMP-QE01', role=UserRole.QUALITY_ENGINEER
        )
        self.qe.set_password('password123')
        self.qe.save()

        self.plant_mgr = User.objects.create_user(
            username='pm_coc', employee_id='EMP-PM01', role=UserRole.PLANT_MANAGER
        )
        self.plant_mgr.set_password('password123')
        self.plant_mgr.save()

        self.insp = User.objects.create_user(
            username='insp_coc', employee_id='EMP-IN01', role=UserRole.QA_FLOOR_INSPECTOR
        )
        self.insp.set_password('password123')
        self.insp.save()

        self.sup = User.objects.create_user(
            username='sup_coc', employee_id='EMP-SP01', role=UserRole.SHIFT_SUPERVISOR
        )
        self.sup.set_password('password123')
        self.sup.save()

        # 2. Material Grade & Intake Lot with Verified MTC & Heat Number
        self.grade = MaterialGrade.objects.create(
            code='AISI-4140-HT',
            name='High-Tensile Alloy 4140'
        )
        self.lot = RawMaterialIntake.objects.create(
            lot_number='LOT-2026-COC',
            heat_number='HEAT-9942',
            supplier_name='Tata Special Steels Ltd',
            purchase_order_no='PO-IND-2026-44',
            material_grade=self.grade,
            quantity_received=Decimal('500.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.IN_STORE,
            lab_status=LabStatus.PASSED,
            mtc_file=SimpleUploadedFile(' टाटा_MTC.pdf', b'%PDF-1.4 dummy mtc', content_type='application/pdf'),
            mtc_verified=True,
            mtc_verified_by=self.qm,
            mtc_verified_at=timezone.now(),
            received_by=self.qm,
        )

        # 3. Manufactured Part & Work Order
        self.part = Part.objects.create(
            part_number='PART-AXLE-800',
            part_name='Precision High-Speed Drive Axle',
            material_grade=self.grade,
            drawing_number='DWG-AXLE-800',
            revision_level='Rev C',
        )
        self.work_order = WorkOrder.objects.create(
            work_order_number='WO-2026-800',
            part=self.part,
            raw_material_lot=self.lot,
            target_quantity=50,
            completed_quantity=50,
            status=WorkOrderStatus.COMPLETED,
            released_by=self.sup,
            released_at=timezone.now() - timedelta(days=2),
        )
        self.traveler = JobTraveler.objects.create(
            work_order=self.work_order,
            traveler_barcode='TRV-WO-2026-800',
            current_operation_sequence=20,
            status=JobTravelerStatus.COMPLETED,
        )

        # 4. Department & Workstations
        self.dept = Department.objects.create(code='PROD', name='Production Machining')
        self.ws_machining = Workstation.objects.create(
            department=self.dept, machine_code='CNC-08', name='CNC Turning Center 08',
            qr_code_identifier='WS-QR-CNC-08', is_active=True
        )
        self.ws_pdi = Workstation.objects.create(
            department=self.dept, machine_code='PDI-GATE', name='Final Pre-Dispatch Gateway',
            qr_code_identifier='WS-QR-PDI-GATE', is_active=True
        )

        for ws in [self.ws_machining, self.ws_pdi]:
            MachinePMLog.objects.create(
                workstation=ws,
                log_date=timezone.now().date(),
                completed_by=self.sup,
                zero_point_verified=True, lubrication_level_ok=True, safety_interlocks_ok=True,
                spindle_runout_ok=True, pneumatic_pressure_ok=True, emergency_stop_tested=True,
            )

        # 5. Inspection Tool
        self.tool = InspectionTool.objects.create(
            tool_id='MIC-001',
            name='Digital Outside Micrometer',
            tool_type=ToolType.MICROMETER,
            serial_number='SN-MIC-2026-01',
            status=ToolStatus.CALIBRATED,
            calibration_date=timezone.now().date() - timedelta(days=30),
            calibration_expiry_date=timezone.now().date() + timedelta(days=335),
        )

        # 6. Inspection Template & Revision
        self.template = InspectionTemplate.objects.create(
            part=self.part,
            template_type=TemplateType.FINAL_PDI,
            title='Final PDI Inspection Plan for Axle',
            template_code='TPL-AXLE-PDI',
        )
        self.revision = InspectionTemplateRevision.objects.create(
            template=self.template,
            revision_label='Rev 1',
            status=RevisionStatus.APPROVED,
            created_by=self.qe,
            approved_by=self.qm,
            approved_at=timezone.now() - timedelta(days=1),
        )

        # 7. CTQ Inspection Parameter
        self.param_ctq = InspectionParameter.objects.create(
            template_revision=self.revision,
            parameter_name='Journal Diameter Ø35.000',
            parameter_type=ParameterType.DIMENSION,
            nominal_value=Decimal('35.000'),
            upper_tolerance=Decimal('0.020'),
            lower_tolerance=Decimal('-0.020'),
            unit='mm',
            is_ctq=True,
            required_tool_type=ToolType.MICROMETER,
            sequence_order=10,
        )

        # 8. Operations on Traveler
        self.op10 = TravelerOperation.objects.create(
            traveler=self.traveler,
            operation_sequence=10,
            operation_name='Op 10: CNC Finish Turning',
            workstation=self.ws_machining,
            status=OperationStatus.COMPLETED,
            completed_by=self.sup,
            completed_at=timezone.now() - timedelta(days=1),
        )
        self.op20 = TravelerOperation.objects.create(
            traveler=self.traveler,
            operation_sequence=20,
            operation_name='Op 20: Pre-Dispatch Final Inspection (PDI)',
            workstation=self.ws_pdi,
            inspection_template_revision=self.revision,
            status=OperationStatus.COMPLETED,
            completed_by=self.qm,
            completed_at=timezone.now(),
        )

        # 9. Final PDI Inspection & In-Tolerance CTQ Measurement
        self.pdi_inspection = FloorInspection.objects.create(
            inspection_number='INSP-PDI-800-01',
            traveler_operation=self.op20,
            template_revision=self.revision,
            workstation=self.ws_pdi,
            inspector=self.insp,
            station_qr_scanned=self.ws_pdi.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.APPROVED,
            reviewed_by=self.qm,
            reviewed_at=timezone.now(),
            supervisor_notes='PDI 100% verified and approved for shipping release.',
        )
        self.measurement = InspectionMeasurement.objects.create(
            inspection=self.pdi_inspection,
            parameter=self.param_ctq,
            measuring_tool=self.tool,
            measured_value=Decimal('35.005'),  # Inside 34.980 - 35.020
        )
        self.pdi_inspection.recalculate_tolerance_and_ctq()

    def test_coc_blocked_if_pdi_not_approved(self):
        """CoC generation is blocked if PDI has not been approved."""
        self.pdi_inspection.status = FloorInspectionStatus.PENDING_REVIEW
        self.pdi_inspection.save()

        is_eligible, reasons = CertificateOfConformance.validate_eligibility(self.traveler)
        self.assertFalse(is_eligible)
        self.assertTrue(any("PDI Pending Review" in r for r in reasons))

        # Direct HTTP POST attempt is blocked
        self.client.login(username='qm_coc', password='password123')
        url = reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id})
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse('quality:pdi_queue'))
        self.assertEqual(CertificateOfConformance.objects.count(), 0)

    def test_coc_blocked_if_operations_incomplete(self):
        """CoC generation is blocked if any operation is pending or running."""
        self.op10.status = OperationStatus.RUNNING
        self.op10.save()

        is_eligible, reasons = CertificateOfConformance.validate_eligibility(self.traveler)
        self.assertFalse(is_eligible)
        self.assertTrue(any("Incomplete Operations" in r for r in reasons))

    def test_coc_blocked_if_traveler_quarantined(self):
        """CoC generation is strictly blocked if traveler is quarantined."""
        self.traveler.status = JobTravelerStatus.QUARANTINED
        self.traveler.save()

        is_eligible, reasons = CertificateOfConformance.validate_eligibility(self.traveler)
        self.assertFalse(is_eligible)
        self.assertTrue(any("Quarantine Hold" in r for r in reasons))

    def test_coc_blocked_if_mtc_unverified_or_missing_heat(self):
        """CoC generation is blocked if MTC is unverified or heat number is missing."""
        # Unverified MTC
        self.lot.mtc_verified = False
        self.lot.save()
        is_eligible, reasons = CertificateOfConformance.validate_eligibility(self.traveler)
        self.assertFalse(is_eligible)
        self.assertTrue(any("Unverified MTC" in r for r in reasons))

        # Missing Heat Number
        self.lot.mtc_verified = True
        self.lot.heat_number = ''
        self.lot.save()
        is_eligible, reasons = CertificateOfConformance.validate_eligibility(self.traveler)
        self.assertFalse(is_eligible)
        self.assertTrue(any("Missing Heat Number" in r for r in reasons))

    def test_coc_blocked_if_ctq_parameter_failed(self):
        """CoC generation is blocked if a CTQ parameter failed tolerance (zero concession rule)."""
        # Set CTQ measurement out of spec
        self.measurement.measured_value = Decimal('35.080')
        self.measurement.save()

        is_eligible, reasons = CertificateOfConformance.validate_eligibility(self.traveler)
        self.assertFalse(is_eligible)
        self.assertTrue(any("CTQ Failure" in r for r in reasons))

    def test_coc_rbac_unauthorized_user_cannot_generate(self):
        """QA Floor Inspector or unauthorized roles cannot generate a CoC."""
        self.client.login(username='insp_coc', password='password123')
        url = reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id})
        response = self.client.post(url, follow=True)

        self.assertRedirects(response, reverse('quality:pdi_queue'))
        self.assertEqual(CertificateOfConformance.objects.count(), 0)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ActionType.SECURITY_ALERT).exists())

    def test_coc_successful_generation_and_pdf_creation(self):
        """Authorized Quality Manager successfully generates CoC with binary PDF and SHA256 hash."""
        self.client.login(username='qm_coc', password='password123')
        url = reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id})
        response = self.client.post(url, {'notes': 'Certified for release.'}, follow=True)

        self.assertEqual(CertificateOfConformance.objects.count(), 1)
        coc = CertificateOfConformance.objects.first()
        self.assertRedirects(response, reverse('quality:coc_detail', kwargs={'coc_id': coc.id}))
        self.assertEqual(coc.status, CertificateStatus.ACTIVE)
        self.assertEqual(coc.version, 1)
        self.assertEqual(coc.issued_by, self.qm)
        self.assertTrue(bool(coc.pdf_sha256_hash))
        self.assertTrue(bool(coc.pdf_file))

        # Check Audit Log
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.ActionType.COC_GENERATED,
            object_id=str(coc.id)
        ).exists())

    def test_coc_pdf_content_and_sha256_hash_integrity(self):
        """Generated PDF is valid binary PDF starting with %PDF and SHA-256 matches exact bytes."""
        self.client.login(username='qm_coc', password='password123')
        self.client.post(reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id}))

        coc = CertificateOfConformance.objects.first()
        pdf_bytes = coc.pdf_file.read()
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 500)

        import hashlib
        calculated_hash = hashlib.sha256(pdf_bytes).hexdigest()
        self.assertEqual(coc.pdf_sha256_hash, calculated_hash)

    def test_coc_prevent_duplicate_active_without_reissue(self):
        """Cannot generate a duplicate active CoC without the reissue parameter."""
        self.client.login(username='qm_coc', password='password123')
        url = reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id})

        # Initial generation
        self.client.post(url)
        self.assertEqual(CertificateOfConformance.objects.count(), 1)
        coc1 = CertificateOfConformance.objects.first()

        # Second attempt without reissue
        response = self.client.post(url, follow=True)
        self.assertEqual(CertificateOfConformance.objects.count(), 1)
        self.assertRedirects(response, reverse('quality:coc_detail', kwargs={'coc_id': coc1.id}))

    def test_coc_reissue_supersedes_previous_version(self):
        """Reissuing CoC creates version 2, supersedes version 1, and logs audit record."""
        self.client.login(username='qm_coc', password='password123')
        url = reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id})

        # 1. Initial generation (v1)
        self.client.post(url)
        coc_v1 = CertificateOfConformance.objects.first()
        self.assertEqual(coc_v1.version, 1)
        self.assertEqual(coc_v1.status, CertificateStatus.ACTIVE)

        # 2. Reissue (v2)
        response = self.client.post(url, {
            'reissue': 'true',
            'reissue_reason': 'Updated customer shipping address and packaging code per ECN-102.'
        }, follow=True)

        self.assertEqual(CertificateOfConformance.objects.count(), 2)
        coc_v1.refresh_from_db()
        self.assertEqual(coc_v1.status, CertificateStatus.SUPERSEDED)

        coc_v2 = CertificateOfConformance.objects.filter(status=CertificateStatus.ACTIVE).first()
        self.assertEqual(coc_v2.version, 2)
        self.assertEqual(coc_v1.superseded_by, coc_v2)
        self.assertEqual(coc_v2.reissue_reason, 'Updated customer shipping address and packaging code per ECN-102.')

        # Verify audit log
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.ActionType.COC_REISSUED,
            object_id=str(coc_v2.id)
        ).exists())

    def test_coc_download_revalidates_eligibility_and_blocks_quarantined(self):
        """Downloading CoC revalidates eligibility; if traveler was quarantined, download is blocked."""
        self.client.login(username='qm_coc', password='password123')
        self.client.post(reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id}))
        coc = CertificateOfConformance.objects.first()

        download_url = reverse('quality:coc_download', kwargs={'coc_id': coc.id})

        # Successful download when valid
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Quarantine traveler after CoC issuance
        self.traveler.status = JobTravelerStatus.QUARANTINED
        self.traveler.save()

        # Subsequent download attempt is blocked
        response = self.client.get(download_url, follow=True)
        self.assertRedirects(response, reverse('quality:coc_detail', kwargs={'coc_id': coc.id}))
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.ActionType.SECURITY_ALERT,
            details__contains="traveler TRV-WO-2026-800 is quarantined"
        ).exists())

    def test_coc_public_verification_endpoint_privacy_and_validity(self):
        """Public QR verification displays authenticity without leaking private credentials."""
        self.client.login(username='qm_coc', password='password123')
        self.client.post(reverse('quality:coc_generate', kwargs={'traveler_id': self.traveler.id}))
        coc = CertificateOfConformance.objects.first()

        # Unauthenticated client visits public verification URL
        self.client.logout()
        verify_url = reverse('quality:coc_verify', kwargs={'token': coc.verification_token})
        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AUTHENTIC CERTIFICATE OF CONFORMANCE')
        self.assertContains(response, coc.certificate_number)
        self.assertContains(response, self.part.part_number)
        self.assertContains(response, self.lot.heat_number)
        self.assertContains(response, coc.pdf_sha256_hash)
        # Verify private passwords or audit trails are not disclosed
        self.assertNotContains(response, 'password123')
        self.assertNotContains(response, 'pbkdf2_sha256')

        # Invalid token check
        invalid_url = reverse('quality:coc_verify', kwargs={'token': 'UNKNOWN-FAKE-TOKEN-999'})
        bad_response = self.client.get(invalid_url)
        self.assertEqual(bad_response.status_code, 200)
        self.assertContains(bad_response, 'UNVERIFIED CERTIFICATE')


class MRBDispositionTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.qm = User.objects.create_user(
            username='qm_mrb', employee_id='EMP-M102', role=UserRole.QUALITY_MANAGER, password='password123'
        )
        self.operator = User.objects.create_user(
            username='op_mrb', employee_id='EMP-M105', role=UserRole.QA_FLOOR_INSPECTOR, password='password123'
        )

        # Department & Workstation
        self.dept = Department.objects.create(name='Machining Dept', code='MCH')
        self.ws = Workstation.objects.create(
            machine_code='CNC-03',
            name='CNC Lathe 03',
            department=self.dept,
            qr_code_identifier='WS-QR-CNC-03'
        )

        # Material & Part
        self.grade = MaterialGrade.objects.create(code='EN-24', name='High-Tensile Steel EN24')
        self.lot = RawMaterialIntake.objects.create(
            lot_number='LOT-2026-MRB-01',
            supplier_name='Jindal Steel',
            purchase_order_no='PO-MRB-001',
            material_grade=self.grade,
            heat_number='HEAT-MRB-883',
            quantity_received=Decimal('150.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.QUARANTINED,
            lab_status=LabStatus.FAILED,
            barcode_identifier='BAR-LOT-MRB-01',
            mtc_file='mtc_documents/dummy.pdf',
            received_by=self.qm,
        )

        self.part = Part.objects.create(
            part_number='PART-MRB-501',
            part_name='Heavy Flange Coupling',
            material_grade=self.grade,
            drawing_number='DWG-MRB-501',
            revision_level='Rev C'
        )

        # Work Order & Quarantined Job Traveler
        self.wo = WorkOrder.objects.create(
            work_order_number='WO-2026-MRB-001',
            part=self.part,
            raw_material_lot=self.lot,
            target_quantity=40,
            completed_quantity=0,
            status=WorkOrderStatus.RELEASED,
        )

        self.traveler = JobTraveler.objects.create(
            work_order=self.wo,
            traveler_barcode='TRV-WO-2026-MRB-001',
            status=JobTravelerStatus.QUARANTINED
        )

    def test_mrb_queue_view_displays_quarantined_items(self):
        """MRB review queue displays quarantined travelers and raw material intake lots."""
        self.client.login(username='qm_mrb', password='password123')
        response = self.client.get(reverse('quality:mrb_queue'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.traveler.traveler_barcode)
        self.assertContains(response, self.lot.lot_number)

    def test_mrb_disposition_rework_creates_rework_order_and_traveler(self):
        """MRB Rework disposition creates a dedicated Rework Order & Traveler (BRD Section 6.3)."""
        self.client.login(username='qm_mrb', password='password123')
        disp_url = reverse('quality:mrb_disposition_traveler', kwargs={'traveler_id': self.traveler.id})

        response = self.client.post(disp_url, {
            'disposition_type': MRBDispositionType.REWORK,
            'defect_description': 'Internal bore diameter undersized by 0.08mm due to worn reamer.',
            'engineering_justification': 'Component wall thickness allows clean re-machining and boring pass.',
            'rework_instructions': 'Setup on CNC Lathe 03, use boring bar T03 to open bore to 45.00mm +/-0.02.',
        }, follow=True)

        self.assertEqual(MRBDisposition.objects.count(), 1)
        disp = MRBDisposition.objects.first()

        self.assertRedirects(response, reverse('quality:mrb_detail', kwargs={'disposition_id': disp.id}))
        self.assertEqual(disp.disposition_type, MRBDispositionType.REWORK)
        self.assertIsNotNone(disp.rework_traveler)
        self.assertTrue(disp.rework_traveler.traveler_barcode.startswith('RWK-TRV-WO-2026-MRB-001'))

        # Verify Audit Log
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.ActionType.MRB_DISPOSITION,
            object_id=str(disp.id)
        ).exists())

    def test_mrb_disposition_scrap_updates_scrapped_quantity(self):
        """MRB Scrap disposition writes off batch quantity and logs scrap cost code."""
        self.client.login(username='qm_mrb', password='password123')
        disp_url = reverse('quality:mrb_disposition_traveler', kwargs={'traveler_id': self.traveler.id})

        response = self.client.post(disp_url, {
            'disposition_type': MRBDispositionType.SCRAP,
            'defect_description': 'Critical flange cracked during heavy roughing cut.',
            'engineering_justification': 'Irreparable structural crack exceeding allowable limit; non-reworkable.',
            'scrap_cost_code': 'SCRAP-DEF-402',
            'scrap_verified_at_bin': 'on',
        }, follow=True)

        self.assertEqual(MRBDisposition.objects.count(), 1)
        disp = MRBDisposition.objects.first()

        self.wo.refresh_from_db()
        self.assertEqual(self.wo.scrapped_quantity, 40)
        self.assertEqual(disp.scrap_cost_code, 'SCRAP-DEF-402')
        self.assertTrue(disp.scrap_verified_at_bin)

    def test_mrb_disposition_customer_concession_releases_quarantine(self):
        """MRB Customer Concession requires written approval document and releases quarantine hold."""
        self.client.login(username='qm_mrb', password='password123')
        disp_url = reverse('quality:mrb_disposition_traveler', kwargs={'traveler_id': self.traveler.id})

        doc_file = SimpleUploadedFile("customer_concession_dev_01.pdf", b"%PDF-1.4 customer approved deviation", content_type="application/pdf")

        response = self.client.post(disp_url, {
            'disposition_type': MRBDispositionType.CUSTOMER_CONCESSION,
            'defect_description': 'External chamfer 1.0mm x 45 deg instead of 1.5mm x 45 deg.',
            'engineering_justification': 'Customer OEM reviewed mating assembly and issued approved deviation waiver.',
            'customer_approval_doc': doc_file,
        }, follow=True)

        self.assertEqual(MRBDisposition.objects.count(), 1)
        disp = MRBDisposition.objects.first()

        # Verify quarantine released
        self.traveler.refresh_from_db()
        self.assertEqual(self.traveler.status, JobTravelerStatus.ACTIVE)
        self.assertTrue(bool(disp.customer_approval_doc))

    def test_mrb_disposition_raw_lot_rtv(self):
        """MRB Raw Material lot disposition records Return to Vendor (RTV) and debit note."""
        self.client.login(username='qm_mrb', password='password123')
        disp_url = reverse('quality:mrb_disposition_lot', kwargs={'lot_id': self.lot.id})

        response = self.client.post(disp_url, {
            'disposition_type': MRBDispositionType.RTV,
            'defect_description': 'Spectro analysis failed: Carbon content 0.62% exceeds maximum 0.45%.',
            'engineering_justification': 'Out of specification chemistry rejected by internal metallurgy lab.',
            'debit_note_number': 'DBN-SUP-2026-9041',
        }, follow=True)

        self.assertEqual(MRBDisposition.objects.count(), 1)
        disp = MRBDisposition.objects.first()

        self.assertEqual(disp.disposition_type, MRBDispositionType.RTV)
        self.assertEqual(disp.debit_note_number, 'DBN-SUP-2026-9041')
        self.assertEqual(disp.raw_material_lot, self.lot)

    def test_unauthorized_operator_blocked_from_mrb(self):
        """Shopfloor operators without can_mrb_disposition cannot execute MRB dispositions."""
        self.client.login(username='op_mrb', password='password123')
        queue_res = self.client.get(reverse('quality:mrb_queue'))
        self.assertEqual(queue_res.status_code, 200)
        self.assertContains(queue_res, "Awaiting MRB Member")
        self.assertNotContains(queue_res, "Execute MRB Disposition")

        disp_url = reverse('quality:mrb_disposition_traveler', kwargs={'traveler_id': self.traveler.id})
        get_res = self.client.get(disp_url, follow=True)
        self.assertContains(get_res, "Permission Denied")

        post_res = self.client.post(disp_url, {
            'disposition_type': MRBDispositionType.SCRAP,
        }, follow=True)
        self.assertContains(post_res, "Permission Denied")
        self.assertFalse(MRBDisposition.objects.exists())



