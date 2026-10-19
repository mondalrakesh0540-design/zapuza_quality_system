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
    MaterialLabTest,
    QuantityUnit,
    RawMaterialIntake,
    SNCRDisposition,
    SNCRReasonCategory,
    SupplierNCR,
)


class InventoryAndTraceabilityTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.plant_mgr = User.objects.create_user(
            username='pm_inv',
            employee_id='EMP-PM-INV',
            role=UserRole.PLANT_MANAGER,
            password='password123'
        )
        self.quality_mgr = User.objects.create_user(
            username='qm_inv',
            employee_id='EMP-QM-INV',
            role=UserRole.QUALITY_MANAGER,
            password='password123'
        )
        self.quality_eng = User.objects.create_user(
            username='qe_inv',
            employee_id='EMP-QE-INV',
            role=UserRole.QUALITY_ENGINEER,
            password='password123'
        )
        self.supervisor = User.objects.create_user(
            username='sup_inv',
            employee_id='EMP-SUP-INV',
            role=UserRole.SHIFT_SUPERVISOR,
            password='password123'
        )
        self.inspector = User.objects.create_user(
            username='insp_inv',
            employee_id='EMP-INSP-INV',
            role=UserRole.QA_FLOOR_INSPECTOR,
            password='password123'
        )

        self.grade_4140 = MaterialGrade.objects.create(
            code='AISI-4140',
            name='Alloy Steel 4140',
            carbon_min=Decimal('0.380'),
            carbon_max=Decimal('0.430'),
            manganese_min=Decimal('0.750'),
            manganese_max=Decimal('1.000'),
            silicon_min=Decimal('0.150'),
            silicon_max=Decimal('0.350'),
            yield_strength_min=Decimal('415.00'),
            tensile_strength_min=Decimal('655.00'),
            hardness_max=Decimal('220.00'),
            requires_lab_testing=True
        )

        self.dummy_file = SimpleUploadedFile(
            "dummy_mtc.pdf",
            b"%PDF-1.4 sample mtc certificate bytes",
            content_type="application/pdf"
        )

        self.lot_cleared = RawMaterialIntake.objects.create(
            lot_number='LOT-TEST-001',
            heat_number='H-8042',
            supplier_name='Jindal Steel',
            purchase_order_no='PO-891',
            material_grade=self.grade_4140,
            quantity_received=Decimal('5000.00'),
            unit=QuantityUnit.KG,
            mtc_file=self.dummy_file,
            mtc_verified=True,
            mtc_verified_by=self.quality_mgr,
            mtc_verified_at=timezone.now(),
            lab_status=LabStatus.PASSED,
            status=IntakeStatus.IN_STORE,
            barcode_identifier='RAW-LOT-TEST-001-H-8042',
            received_by=self.supervisor
        )

        self.lot_in_testing = RawMaterialIntake.objects.create(
            lot_number='LOT-TEST-002',
            heat_number='H-9102',
            supplier_name='Tata Steel',
            purchase_order_no='PO-904',
            material_grade=self.grade_4140,
            quantity_received=Decimal('3500.00'),
            unit=QuantityUnit.KG,
            mtc_file=self.dummy_file,
            mtc_verified=False,  # Unverified!
            lab_status=LabStatus.IN_LAB_TESTING,
            status=IntakeStatus.IN_STORE,
            barcode_identifier='RAW-LOT-TEST-002-H-9102',
            received_by=self.supervisor
        )

        self.lot_quarantined = RawMaterialIntake.objects.create(
            lot_number='LOT-TEST-003',
            heat_number='H-7701',
            supplier_name='Kalyani Steels',
            purchase_order_no='PO-855',
            material_grade=self.grade_4140,
            quantity_received=Decimal('2000.00'),
            unit=QuantityUnit.KG,
            mtc_file=self.dummy_file,
            mtc_verified=True,
            lab_status=LabStatus.FAILED,
            status=IntakeStatus.QUARANTINED,
            barcode_identifier='RAW-LOT-TEST-003-H-7701',
            received_by=self.supervisor
        )

    def test_material_grade_chemical_and_mechanical_tolerance_checks(self):
        """Verify automated pass/fail calculation on spectro chemical and strength values."""
        # Within limits
        passed, fails = self.grade_4140.evaluate_chemical(c=Decimal('0.400'), mn=Decimal('0.800'), si=Decimal('0.250'))
        self.assertTrue(passed)
        self.assertEqual(len(fails), 0)

        # Carbon out of tolerance (> 0.430)
        passed_fail, fails = self.grade_4140.evaluate_chemical(c=Decimal('0.520'))
        self.assertFalse(passed_fail)
        self.assertIn("Carbon", fails[0])

        # Hardness exceeds maximum allowed (> 220.00)
        passed_mech, mech_fails = self.grade_4140.evaluate_mechanical(hardness_val=Decimal('250.00'))
        self.assertFalse(passed_mech)
        self.assertIn("Hardness", mech_fails[0])

    def test_server_side_work_order_issue_protection(self):
        """
        BRD Section 3.2 & 3.3:
        Server-side protection: Unverified, in-testing, or quarantined stock cannot be issued.
        """
        # Cleared lot issues successfully
        can_issue, reason = self.lot_cleared.can_issue_to_production()
        self.assertTrue(can_issue)
        try:
            self.lot_cleared.validate_for_work_order_issue()
        except ValidationError:
            self.fail("Cleared lot raised ValidationError unexpectedly.")

        # Lot in testing is blocked by lab status
        can_issue_test, reason_test = self.lot_in_testing.can_issue_to_production()
        self.assertFalse(can_issue_test)
        with self.assertRaises(ValidationError):
            self.lot_in_testing.validate_for_work_order_issue()

        # Quarantined lot is blocked under all circumstances
        can_issue_q, reason_q = self.lot_quarantined.can_issue_to_production()
        self.assertFalse(can_issue_q)
        self.assertIn("Quarantine Lockout", reason_q)
        with self.assertRaises(ValidationError):
            self.lot_quarantined.validate_for_work_order_issue()

    def test_dock_intake_creation_requires_mtc_file(self):
        """
        BRD Section 3.2:
        Intake cannot be saved without an attached readable MTC file.
        """
        self.client.force_login(self.supervisor)
        # Attempt without MTC file
        resp_no_mtc = self.client.post(reverse('inventory:intake_create'), {
            'heat_number': 'H-NEW-99',
            'supplier_name': 'New Supplier',
            'purchase_order_no': 'PO-999',
            'material_grade': self.grade_4140.id,
            'quantity_received': '1000',
            'unit': QuantityUnit.KG
        })
        self.assertEqual(resp_no_mtc.status_code, 200)
        self.assertFalse(RawMaterialIntake.objects.filter(heat_number='H-NEW-99').exists())

        # Attempt with MTC file
        mtc = SimpleUploadedFile("test_mtc.pdf", b"test pdf content", content_type="application/pdf")
        resp_with_mtc = self.client.post(reverse('inventory:intake_create'), {
            'heat_number': 'H-NEW-99',
            'supplier_name': 'New Supplier',
            'purchase_order_no': 'PO-999',
            'material_grade': self.grade_4140.id,
            'quantity_received': '1000',
            'unit': QuantityUnit.KG,
            'mtc_file': mtc
        })
        self.assertRedirects(resp_with_mtc, reverse('inventory:intake_detail', args=[RawMaterialIntake.objects.get(heat_number='H-NEW-99').pk]))
        self.assertTrue(RawMaterialIntake.objects.filter(heat_number='H-NEW-99').exists())

    def test_mtc_verification_by_quality_engineer(self):
        """Quality Engineer verifies and approves MTC."""
        self.client.force_login(self.quality_eng)
        resp = self.client.post(reverse('inventory:mtc_verify', args=[self.lot_in_testing.pk]), {
            'action': 'verify'
        })
        self.assertRedirects(resp, reverse('inventory:intake_detail', args=[self.lot_in_testing.pk]))
        self.lot_in_testing.refresh_from_db()
        self.assertTrue(self.lot_in_testing.mtc_verified)
        self.assertEqual(self.lot_in_testing.mtc_verified_by, self.quality_eng)

    def test_laboratory_test_updates_lot_lab_status(self):
        """Entering lab test results automatically updates parent lot lab status."""
        self.client.force_login(self.quality_eng)

        # Enter passing lab test
        resp_pass = self.client.post(reverse('inventory:lab_test_create', args=[self.lot_in_testing.pk]), {
            'carbon_actual': '0.410',
            'manganese_actual': '0.850',
            'silicon_actual': '0.250',
            'yield_strength_actual': '450.0',
            'tensile_strength_actual': '690.0',
            'hardness_actual': '190.0',
        })
        self.assertRedirects(resp_pass, reverse('inventory:intake_detail', args=[self.lot_in_testing.pk]))
        self.lot_in_testing.refresh_from_db()
        self.assertEqual(self.lot_in_testing.lab_status, LabStatus.PASSED)

    def test_sncr_logging_quarantines_lot(self):
        """
        BRD Section 3.3:
        Logging an SNCR immediately tags stock as 'Supplier Quarantine' and locks it from work orders.
        """
        self.client.force_login(self.supervisor)
        resp = self.client.post(reverse('inventory:sncr_create', args=[self.lot_cleared.pk]), {
            'reason_category': SNCRReasonCategory.CHEMICAL_OUT_OF_SPEC,
            'disposition': SNCRDisposition.SUPPLIER_QUARANTINE_HOLD,
            'defect_description': 'Customer notified chemistry defect in raw stock heat batch.',
            'corrective_action_requested': 'Vendor 8D report.'
        })
        self.assertRedirects(resp, reverse('inventory:sncr_list'))
        self.lot_cleared.refresh_from_db()
        self.assertEqual(self.lot_cleared.status, IntakeStatus.QUARANTINED)
        self.assertTrue(self.lot_cleared.ncrs.exists())

        # Now work order issuance must be strictly blocked
        can_issue, _ = self.lot_cleared.can_issue_to_production()
        self.assertFalse(can_issue)

    def test_forward_recall_heat_traceability_view(self):
        """
        BRD Section 7.2:
        Forward recall query by heat number reveals complete provenance and status.
        """
        self.client.force_login(self.inspector)
        resp = self.client.get(reverse('inventory:traceability_query'), {'heat_number': 'H-8042'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "H-8042")
        self.assertContains(resp, "Jindal Steel")
        self.assertContains(resp, "LOT-TEST-001")

        # Quarantined lot query
        resp_q = self.client.get(reverse('inventory:traceability_query'), {'heat_number': 'H-7701'})
        self.assertEqual(resp_q.status_code, 200)
        self.assertContains(resp_q, "SUPPLIER QUARANTINE")
