from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.inventory.models import (
    IntakeStatus,
    LabStatus,
    MaterialGrade,
    QuantityUnit,
    RawMaterialIntake,
)
from apps.master_data.models import Department, Workstation
from apps.production.models import (
    JobTraveler,
    JobTravelerStatus,
    OperationStatus,
    TravelerOperation,
    WorkOrder,
    WorkOrderStatus,
)
from apps.quality.models import (
    InspectionTemplate,
    InspectionTemplateRevision,
    Part,
    RevisionStatus,
)


class ProductionRoutingAndLockoutTests(TestCase):
    def setUp(self):
        # Users
        self.plant_mgr = User.objects.create_user(
            username='pm_prod', employee_id='EMP-PM-PROD', role=UserRole.PLANT_MANAGER
        )
        self.quality_mgr = User.objects.create_user(
            username='qm_prod', employee_id='EMP-QM-PROD', role=UserRole.QUALITY_MANAGER
        )
        self.supervisor = User.objects.create_user(
            username='sup_prod', employee_id='EMP-SUP-PROD', role=UserRole.SHIFT_SUPERVISOR
        )
        self.inspector = User.objects.create_user(
            username='insp_prod', employee_id='EMP-INSP-PROD', role=UserRole.QA_FLOOR_INSPECTOR
        )

        # Department & Workstations
        self.dept_machining = Department.objects.create(name='Machining Division', code='MACH')
        self.dept_heat = Department.objects.create(name='Heat Treatment Facility', code='HEAT')

        self.ws_saw = Workstation.objects.create(
            department=self.dept_machining, name='Band Sawing Cell', machine_code='SAW-01',
            qr_code_identifier='QR-WS-SAW-01', is_active=True
        )
        self.ws_cnc = Workstation.objects.create(
            department=self.dept_machining, name='CNC Turning Center', machine_code='CNC-01',
            qr_code_identifier='QR-WS-CNC-01', is_active=True
        )
        self.ws_oven = Workstation.objects.create(
            department=self.dept_heat, name='Vacuum Heat Oven', machine_code='OVEN-01',
            qr_code_identifier='QR-WS-OVEN-01', is_active=True
        )
        self.ws_grind = Workstation.objects.create(
            department=self.dept_machining, name='Cylindrical Grinder', machine_code='GRIND-01',
            qr_code_identifier='QR-WS-GRIND-01', is_active=True
        )

        # Material Grades
        self.grade_4140 = MaterialGrade.objects.create(
            code='AISI-4140', name='Chromoly Alloy Steel', description='ASTM A29'
        )
        self.grade_en8 = MaterialGrade.objects.create(
            code='EN-8D', name='Medium Carbon Steel', description='IS 5517'
        )

        # Component Part
        self.part = Part.objects.create(
            part_number='PART-SH-401',
            part_name='Drive Shaft',
            material_grade=self.grade_4140,
            drawing_number='DWG-SH401',
            revision_level='Rev A',
        )

        # Cleared Raw Material Lot
        self.lot_cleared = RawMaterialIntake.objects.create(
            lot_number='LOT-PROD-001',
            heat_number='H-8801',
            supplier_name='Tata Steel',
            purchase_order_no='PO-PROD-101',
            material_grade=self.grade_4140,
            quantity_received=Decimal('1000.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.IN_STORE,
            mtc_verified=True,
            mtc_verified_by=self.quality_mgr,
            mtc_verified_at=timezone.now(),
            lab_status=LabStatus.PASSED,
            barcode_identifier='RAW-LOT-PROD-001-H-8801',
            received_by=self.supervisor,
        )

        # Incompatible Grade Lot
        self.lot_en8 = RawMaterialIntake.objects.create(
            lot_number='LOT-EN8-001',
            heat_number='H-9901',
            supplier_name='Jindal Steel',
            purchase_order_no='PO-PROD-102',
            material_grade=self.grade_en8,
            quantity_received=Decimal('500.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.IN_STORE,
            mtc_verified=True,
            lab_status=LabStatus.PASSED,
            barcode_identifier='RAW-LOT-EN8-001-H-9901',
            received_by=self.supervisor,
        )

        # Quarantined Lot
        self.lot_quarantined = RawMaterialIntake.objects.create(
            lot_number='LOT-QUAR-001',
            heat_number='H-7701',
            supplier_name='Kalyani Steels',
            purchase_order_no='PO-PROD-103',
            material_grade=self.grade_4140,
            quantity_received=Decimal('500.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.QUARANTINED,
            mtc_verified=True,
            barcode_identifier='RAW-LOT-QUAR-001-H-7701',
            received_by=self.supervisor,
        )

        from apps.master_data.models import MachinePMLog, ShiftType
        for ws in [self.ws_saw, self.ws_cnc, self.ws_oven, self.ws_grind]:
            MachinePMLog.objects.create(
                workstation=ws,
                log_date=timezone.now().date(),
                shift=ShiftType.MORNING,
                completed_by=self.supervisor,
                zero_point_verified=True,
                lubrication_level_ok=True,
                safety_interlocks_ok=True,
                spindle_runout_ok=True,
                pneumatic_pressure_ok=True,
                emergency_stop_tested=True,
                remarks="All checks passed.",
            )

    def test_material_grade_incompatibility_validation(self):
        """Cannot create a work order if part grade does not match raw stock lot grade."""
        wo = WorkOrder(
            work_order_number='WO-TEST-BAD-GRADE',
            part=self.part,  # Requires AISI-4140
            raw_material_lot=self.lot_en8,  # Is EN-8D
            target_quantity=50,
        )
        with self.assertRaises(ValidationError) as ctx:
            wo.clean()
        self.assertIn("Material Incompatibility", str(ctx.exception))

    def test_cannot_release_work_order_with_quarantined_material(self):
        """Release is strictly blocked if raw material lot is in quarantine."""
        wo = WorkOrder.objects.create(
            work_order_number='WO-TEST-QUAR',
            part=self.part,
            raw_material_lot=self.lot_quarantined,
            target_quantity=50,
            status=WorkOrderStatus.DRAFT,
        )
        with self.assertRaises(ValidationError) as ctx:
            wo.release(self.supervisor)
        self.assertIn("QUARANTINE", str(ctx.exception).upper())
        wo.refresh_from_db()
        self.assertEqual(wo.status, WorkOrderStatus.DRAFT)

    def test_releasing_cleared_work_order_generates_traveler(self):
        """Releasing work order generates digital JobTraveler with TRV barcode."""
        wo = WorkOrder.objects.create(
            work_order_number='WO-2026-001',
            part=self.part,
            raw_material_lot=self.lot_cleared,
            target_quantity=50,
            status=WorkOrderStatus.DRAFT,
        )
        traveler = wo.release(self.supervisor)
        wo.refresh_from_db()

        self.assertEqual(wo.status, WorkOrderStatus.RELEASED)
        self.assertEqual(wo.released_by, self.supervisor)
        self.assertIsNotNone(wo.released_at)
        self.assertEqual(traveler.traveler_barcode, 'TRV-WO-2026-001')
        self.assertEqual(traveler.status, JobTravelerStatus.ACTIVE)

    def test_sequential_routing_interlock_blocks_skipping_operations(self):
        """
        BRD Section 7.1:
        Cannot start Op 20 while Op 10 is still incomplete.
        """
        wo = WorkOrder.objects.create(
            work_order_number='WO-SEQ-TEST',
            part=self.part,
            raw_material_lot=self.lot_cleared,
            target_quantity=25,
            status=WorkOrderStatus.RELEASED,
        )
        traveler = JobTraveler.objects.create(
            work_order=wo,
            traveler_barcode=f"TRV-{wo.work_order_number}",
            current_operation_sequence=10,
        )
        op10 = TravelerOperation.objects.create(
            traveler=traveler,
            operation_sequence=10,
            operation_name='Op 10: Sawing',
            workstation=self.ws_saw,
            status=OperationStatus.READY,
        )
        op20 = TravelerOperation.objects.create(
            traveler=traveler,
            operation_sequence=20,
            operation_name='Op 20: CNC Turning',
            workstation=self.ws_cnc,
            status=OperationStatus.PENDING,
        )

        # Op 10 can start
        can_start_10, _ = op10.can_start()
        self.assertTrue(can_start_10)

        # Op 20 CANNOT start because Op 10 is not completed
        can_start_20, reason_20 = op20.can_start()
        self.assertFalse(can_start_20)
        self.assertIn("Sequential Routing Lockout", reason_20)

        # Attempting start_operation on Op 20 raises ValidationError
        with self.assertRaises(ValidationError):
            op20.start_operation(self.supervisor)

        # Start and complete Op 10
        op10.start_operation(self.supervisor)
        self.assertEqual(op10.status, OperationStatus.RUNNING)

        op10.complete_operation(self.supervisor, remarks="Billet cutting completed.")
        self.assertEqual(op10.status, OperationStatus.COMPLETED)

        # Now Op 20 is unlocked and READY
        op20.refresh_from_db()
        self.assertEqual(op20.status, OperationStatus.READY)
        can_start_20_now, _ = op20.can_start()
        self.assertTrue(can_start_20_now)

        # Op 20 can now successfully start
        op20.start_operation(self.supervisor)
        self.assertEqual(op20.status, OperationStatus.RUNNING)

    def test_process_hold_cooling_timer_interlock(self):
        """
        BRD Section 8.2:
        Mandatory cooling/curing hold locks downstream operations until timer expires.
        """
        wo = WorkOrder.objects.create(
            work_order_number='WO-HOLD-TEST',
            part=self.part,
            raw_material_lot=self.lot_cleared,
            target_quantity=20,
            status=WorkOrderStatus.RELEASED,
        )
        traveler = JobTraveler.objects.create(
            work_order=wo,
            traveler_barcode=f"TRV-{wo.work_order_number}",
        )
        op30 = TravelerOperation.objects.create(
            traveler=traveler,
            operation_sequence=30,
            operation_name='Op 30: Vacuum Heat Treatment',
            workstation=self.ws_oven,
            requires_hold_time=True,
            hold_duration_minutes=240,  # 4 hours
            status=OperationStatus.RUNNING,
        )
        op40 = TravelerOperation.objects.create(
            traveler=traveler,
            operation_sequence=40,
            operation_name='Op 40: Cylindrical Grinding',
            workstation=self.ws_grind,
            status=OperationStatus.PENDING,
        )

        # Complete Op 30 - sets hold timer
        op30.complete_operation(self.supervisor, remarks="Quenched and discharged.")
        op30.refresh_from_db()
        self.assertIsNotNone(op30.hold_start_time)
        self.assertIsNotNone(op30.hold_release_time)

        # Check Op 40 hold status (hold is active)
        hold_active, remaining_min = op40.is_hold_active()
        self.assertTrue(hold_active)
        self.assertGreater(remaining_min, 0)

        # Op 40 cannot start while cooling hold is active
        can_start_40, reason_40 = op40.can_start()
        self.assertFalse(can_start_40)
        self.assertIn("Mandatory Process Hold Active", reason_40)

        # Simulate hold timer expiration (simulate past time)
        op30.hold_release_time = timezone.now() - timedelta(minutes=5)
        op30.save(update_fields=['hold_release_time'])

        # Now hold is no longer active
        hold_active_expired, _ = op40.is_hold_active()
        self.assertFalse(hold_active_expired)

        # Op 40 is cleared to start
        can_start_40_cleared, msg_cleared = op40.can_start()
        self.assertTrue(can_start_40_cleared)
        self.assertIn("cleared to start", msg_cleared)

    def test_workstation_pm_lockout_blocks_traveler_operation(self):
        """
        BRD Section 2.2 & 7.1:
        If assigned workstation PM is overdue, traveler operation cannot be started.
        """
        ws_locked = Workstation.objects.create(
            department=self.dept_machining, name='Overdue Lathe', machine_code='LATHE-NO-PM',
            qr_code_identifier='QR-LATHE-NO-PM', is_active=True
        )
        wo = WorkOrder.objects.create(
            work_order_number='WO-PM-TEST',
            part=self.part,
            raw_material_lot=self.lot_cleared,
            target_quantity=10,
            status=WorkOrderStatus.RELEASED,
        )
        traveler = JobTraveler.objects.create(
            work_order=wo,
            traveler_barcode=f"TRV-{wo.work_order_number}",
        )
        op = TravelerOperation.objects.create(
            traveler=traveler,
            operation_sequence=10,
            operation_name='Op 10: Machining on Unmaintained Machine',
            workstation=ws_locked,
            status=OperationStatus.READY,
        )

        can_start, reason = op.can_start()
        self.assertFalse(can_start)
        self.assertIn("Assigned Workstation Lockout", reason)
        self.assertIn("Machine PM Lockout", reason)


class ProductionRBACViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.supervisor = User.objects.create_user(
            username='sup', password='password123', employee_id='EMP-SUP-V', role=UserRole.SHIFT_SUPERVISOR
        )
        self.inspector = User.objects.create_user(
            username='insp', password='password123', employee_id='EMP-INSP-V', role=UserRole.QA_FLOOR_INSPECTOR
        )

        self.dept = Department.objects.create(name='Machining', code='MACH-RBAC')
        self.ws = Workstation.objects.create(department=self.dept, name='Lathe', machine_code='LATHE-01', qr_code_identifier='QR-LATHE-01')

        self.grade = MaterialGrade.objects.create(code='AISI-4140', name='Alloy Steel')
        self.part = Part.objects.create(
            part_number='PART-P1', part_name='Pinion', material_grade=self.grade, drawing_number='DWG-P1'
        )
        self.lot = RawMaterialIntake.objects.create(
            lot_number='LOT-V-01', heat_number='H-V01', supplier_name='Tata', purchase_order_no='PO-V-01',
            material_grade=self.grade, quantity_received=100, unit=QuantityUnit.KG,
            barcode_identifier='RAW-LOT-V-01-H-V01',
            status=IntakeStatus.IN_STORE, mtc_verified=True, lab_status=LabStatus.PASSED, received_by=self.supervisor
        )

        self.work_order = WorkOrder.objects.create(
            work_order_number='WO-V-001', part=self.part, raw_material_lot=self.lot, target_quantity=10,
            status=WorkOrderStatus.DRAFT
        )

    def test_inspector_cannot_create_work_order_view(self):
        """Floor Inspector redirected when attempting to access work order create view."""
        self.client.login(username='insp', password='password123')
        resp = self.client.get(reverse('production:work_order_create'))
        self.assertRedirects(resp, reverse('dashboard:index'))

    def test_supervisor_can_access_work_order_create_view(self):
        """Shift Supervisor can access work order create view."""
        self.client.login(username='sup', password='password123')
        resp = self.client.get(reverse('production:work_order_create'))
        self.assertEqual(resp.status_code, 200)

    def test_inspector_cannot_release_work_order_view(self):
        """Floor Inspector cannot release work order."""
        self.client.login(username='insp', password='password123')
        resp = self.client.post(reverse('production:work_order_release', kwargs={'pk': self.work_order.pk}))
        self.assertRedirects(resp, reverse('dashboard:index'))

    def test_supervisor_can_release_work_order_and_creates_traveler(self):
        """Supervisor can release work order, which redirects to traveler detail."""
        self.client.login(username='sup', password='password123')
        resp = self.client.post(reverse('production:work_order_release', kwargs={'pk': self.work_order.pk}))
        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.status, WorkOrderStatus.RELEASED)
        self.assertTrue(hasattr(self.work_order, 'traveler'))
        self.assertRedirects(resp, reverse('production:traveler_detail', kwargs={'pk': self.work_order.traveler.pk}))
