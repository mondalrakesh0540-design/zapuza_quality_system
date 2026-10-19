from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.audit_trail.models import AuditLog
from apps.dispatch.models import DispatchManifest, DispatchManifestStatus
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
    CertificateOfConformance,
    CertificateStatus,
    FloorInspection,
    FloorInspectionStatus,
    InspectionParameter,
    InspectionTemplate,
    InspectionTemplateRevision,
    ParameterType,
    Part,
    RevisionStatus,
    TemplateType,
    ThresholdType,
)


class DispatchShippingInterlockTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.plant_mgr = User.objects.create_user(
            username='plant_mgr_disp', employee_id='EMP-D101', role=UserRole.PLANT_MANAGER, password='password123'
        )
        self.qm = User.objects.create_user(
            username='qm_disp', employee_id='EMP-D102', role=UserRole.QUALITY_MANAGER, password='password123'
        )

        # Department & Workstation
        self.dept = Department.objects.create(name='Machining Dept', code='MCH')
        self.ws = Workstation.objects.create(
            machine_code='CNC-01',
            name='CNC Lathe 01',
            department=self.dept,
            qr_code_identifier='WS-QR-CNC-01'
        )
        MachinePMLog.objects.create(
            workstation=self.ws,
            completed_by=self.plant_mgr,
            is_passed=True,
            log_date=timezone.now().date()
        )

        # Raw Material & Part
        self.grade = MaterialGrade.objects.create(code='AISI-4140', name='High-Tensile Alloy Steel 4140')
        self.lot = RawMaterialIntake.objects.create(
            lot_number='LOT-2026-DISP-01',
            supplier_name='Apex Forgings',
            purchase_order_no='PO-DISP-001',
            material_grade=self.grade,
            heat_number='HEAT-DISP-992',
            quantity_received=Decimal('100.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.IN_STORE,
            lab_status=LabStatus.PASSED,
            barcode_identifier='BAR-LOT-DISP-01',
            mtc_file='mtc_documents/dummy.pdf',
            received_by=self.plant_mgr,
        )

        self.part = Part.objects.create(
            part_number='PART-DISP-401',
            part_name='Transmission Drive Shaft',
            material_grade=self.grade,
            drawing_number='DWG-DISP-401',
            revision_level='Rev B'
        )

        # Work Order & Job Traveler
        self.wo = WorkOrder.objects.create(
            work_order_number='WO-2026-DISP-001',
            part=self.part,
            raw_material_lot=self.lot,
            target_quantity=50,
            completed_quantity=50,
            status=WorkOrderStatus.RELEASED,
            released_by=self.plant_mgr,
            released_at=timezone.now()
        )

        self.traveler = JobTraveler.objects.create(
            work_order=self.wo,
            traveler_barcode='TRV-WO-2026-DISP-001',
            status=JobTravelerStatus.ACTIVE
        )

        # Operations: Op 10 (CNC Turning) and Op 20 (Final Pre-Dispatch Inspection)
        self.op10 = TravelerOperation.objects.create(
            traveler=self.traveler,
            operation_sequence=10,
            operation_name='CNC Turning & Profiling',
            workstation=self.ws,
            status=OperationStatus.COMPLETED
        )

        self.op20 = TravelerOperation.objects.create(
            traveler=self.traveler,
            operation_sequence=20,
            operation_name='Final Pre-Dispatch Inspection (PDI)',
            workstation=self.ws,
            status=OperationStatus.COMPLETED
        )

        # Inspection Template & Approved Revision
        self.template = InspectionTemplate.objects.create(
            part=self.part,
            template_type=TemplateType.FINAL_PDI,
            title='Final PDI Inspection Plan',
            template_code='TPL-DISP-PDI'
        )
        self.revision = InspectionTemplateRevision.objects.create(
            template=self.template,
            revision_label='Rev A',
            status=RevisionStatus.APPROVED,
            created_by=self.qm,
            approved_by=self.qm,
            approved_at=timezone.now()
        )

        # PDI Floor Inspection (APPROVED)
        self.pdi_insp = FloorInspection.objects.create(
            inspection_number='INSP-PDI-DISP-001',
            traveler_operation=self.op20,
            template_revision=self.revision,
            workstation=self.ws,
            inspector=self.qm,
            station_qr_scanned=self.ws.qr_code_identifier,
            traveler_barcode_scanned=self.traveler.traveler_barcode,
            status=FloorInspectionStatus.APPROVED,
            overall_in_tolerance=True,
            reviewed_by=self.qm,
            reviewed_at=timezone.now()
        )

        # Certificate of Conformance (ACTIVE)
        self.coc = CertificateOfConformance.objects.create(
            certificate_number='COC-2026-DISP-001',
            traveler=self.traveler,
            work_order=self.wo,
            status=CertificateStatus.ACTIVE,
            issued_by=self.qm,
            issued_at=timezone.now(),
        )

    def test_shipping_interlock_blocked_if_pdi_missing_or_unapproved(self):
        """Shipping gate blocks dispatch if final PDI is missing or awaiting review."""
        self.pdi_insp.status = FloorInspectionStatus.PENDING_REVIEW
        self.pdi_insp.save()

        can_clear, reasons = DispatchManifest.validate_shipping_interlock(self.traveler)
        self.assertFalse(can_clear)
        self.assertTrue(any('PDI Pending Review' in r for r in reasons))

        # Test POST to dispatch creation view is blocked
        self.client.login(username='plant_mgr_disp', password='password123')
        create_url = reverse('dispatch:dispatch_create', kwargs={'traveler_id': self.traveler.id})
        response = self.client.post(create_url, {
            'customer_name': 'Brembo India Automotive',
            'customer_po_number': 'PO-BRM-8891',
            'shipping_destination': 'Chakan Plant 2, Pune',
            'transport_vehicle_number': 'MH-12-QZ-4012',
            'driver_name': 'Rajesh Shinde',
            'dispatch_quantity': 50,
        }, follow=True)

        self.assertRedirects(response, reverse('dispatch:dispatch_queue'))
        self.assertFalse(DispatchManifest.objects.exists())

    def test_shipping_interlock_blocked_if_operations_incomplete(self):
        """Shipping gate blocks dispatch if any operation is not COMPLETED."""
        self.op10.status = OperationStatus.RUNNING
        self.op10.save()

        can_clear, reasons = DispatchManifest.validate_shipping_interlock(self.traveler)
        self.assertFalse(can_clear)
        self.assertTrue(any('Incomplete Operations' in r for r in reasons))

    def test_shipping_interlock_blocked_without_active_coc(self):
        """Shipping gate blocks dispatch if Certificate of Conformance is revoked or missing."""
        self.coc.status = CertificateStatus.REVOKED
        self.coc.save()

        can_clear, reasons = DispatchManifest.validate_shipping_interlock(self.traveler)
        self.assertFalse(can_clear)
        self.assertTrue(any('Missing Certificate of Conformance' in r for r in reasons))

    def test_shipping_interlock_blocked_if_traveler_quarantined(self):
        """Shipping gate strictly blocks quarantined travelers."""
        self.traveler.status = JobTravelerStatus.QUARANTINED
        self.traveler.save()

        can_clear, reasons = DispatchManifest.validate_shipping_interlock(self.traveler)
        self.assertFalse(can_clear)
        self.assertTrue(any('Quarantine Lockout' in r for r in reasons))

    def test_successful_gate_pass_issuance_and_manifest_generation(self):
        """When all 5 interlocks pass, gate pass and shipping manifest are generated."""
        self.client.login(username='plant_mgr_disp', password='password123')
        create_url = reverse('dispatch:dispatch_create', kwargs={'traveler_id': self.traveler.id})

        response = self.client.post(create_url, {
            'customer_name': 'Brembo India Automotive Pvt Ltd',
            'customer_po_number': 'PO-BRM-8891',
            'shipping_destination': 'Brembo Warehouse, Chakan Industrial Area, Pune',
            'transport_vehicle_number': 'MH-12-QZ-4012',
            'driver_name': 'Rajesh Shinde',
            'driver_contact': '+91 98220 11223',
            'driver_license': 'MH12-20180029341',
            'container_seal_number': 'SEAL-ZAP-88410',
            'dispatch_quantity': 50,
            'remarks': 'Palletized with VCI film and tamper-evident tags.'
        }, follow=True)

        self.assertEqual(DispatchManifest.objects.count(), 1)
        manifest = DispatchManifest.objects.first()
        self.assertRedirects(response, reverse('dispatch:dispatch_gate_pass', kwargs={'manifest_id': manifest.id}))

        # Verify traveler status updated to COMPLETED
        self.traveler.refresh_from_db()
        self.assertEqual(self.traveler.status, JobTravelerStatus.COMPLETED)

        # Verify audit log
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.ActionType.DISPATCH_CLEARED,
            object_id=str(manifest.id)
        ).exists())

        # Verify gate pass view rendering
        gate_pass_url = reverse('dispatch:dispatch_gate_pass', kwargs={'manifest_id': manifest.id})
        gate_res = self.client.get(gate_pass_url)
        self.assertEqual(gate_res.status_code, 200)
        self.assertContains(gate_res, manifest.manifest_number)
        self.assertContains(gate_res, 'MH-12-QZ-4012')
        self.assertContains(gate_res, 'Rajesh Shinde')
        self.assertContains(gate_res, self.part.part_number)

        # Verify crate label view rendering
        crate_label_url = reverse('dispatch:dispatch_crate_label', kwargs={'manifest_id': manifest.id})
        crate_res = self.client.get(crate_label_url)
        self.assertEqual(crate_res.status_code, 200)
        self.assertContains(crate_res, 'Exterior Shipping Crate QR Label')
        self.assertContains(crate_res, manifest.qr_verification_token)

    def test_customer_public_shipping_qr_verification(self):
        """Exterior crate QR token allows customer verification without login."""
        manifest = DispatchManifest.objects.create(
            manifest_number='GP-2026-9901',
            traveler=self.traveler,
            work_order=self.wo,
            certificate=self.coc,
            customer_name='Brembo India Automotive',
            customer_po_number='PO-BRM-8891',
            shipping_destination='Chakan, Pune',
            dispatch_quantity=50,
            transport_vehicle_number='MH-12-QZ-4012',
            driver_name='Rajesh Shinde',
            cleared_by=self.plant_mgr,
        )

        self.client.logout()
        verify_url = reverse('dispatch:customer_verify', kwargs={'token': manifest.qr_verification_token})
        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AUTHENTIC CERTIFIED SHIPMENT & DIGITAL QUALITY BIRTH CERTIFICATE')
        self.assertContains(response, manifest.manifest_number)
        self.assertContains(response, self.part.part_number)
        self.assertContains(response, self.lot.heat_number)
        self.assertContains(response, self.coc.certificate_number)
        # Ensure no sensitive credentials leaked
        self.assertNotContains(response, 'password123')

        # Invalid token check
        bad_res = self.client.get(reverse('dispatch:customer_verify', kwargs={'token': 'INVALID_TOKEN_999'}))
        self.assertEqual(bad_res.status_code, 200)
        self.assertContains(bad_res, 'UNVERIFIED SHIPMENT')
