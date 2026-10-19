from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.audit_trail.models import AuditLog
from apps.handover.models import ShiftHandoverLog, ShiftHandoverStatus
from apps.inventory.models import (
    IntakeStatus,
    LabStatus,
    MaterialGrade,
    QuantityUnit,
    RawMaterialIntake,
)
from apps.master_data.models import Department, ShiftType, Workstation
from apps.production.models import JobTraveler, JobTravelerStatus, WorkOrder, WorkOrderStatus
from apps.quality.models import Part


class ShiftHandoverTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.out_operator = User.objects.create_user(
            username='out_op', employee_id='EMP-H101', role=UserRole.QA_FLOOR_INSPECTOR, password='password123'
        )
        self.in_operator = User.objects.create_user(
            username='in_op', employee_id='EMP-H102', role=UserRole.QA_FLOOR_INSPECTOR, password='password123'
        )
        self.unauth_user = User.objects.create_user(
            username='unauth_guest', employee_id='EMP-H999', role=UserRole.QUALITY_ENGINEER, password='password123'
        )

        # Department & Workstation
        self.dept = Department.objects.create(name='Machining Dept', code='MCH')
        self.ws = Workstation.objects.create(
            machine_code='CNC-02',
            name='CNC Lathe 02',
            department=self.dept,
            qr_code_identifier='WS-QR-CNC-02'
        )

        # Material & Part
        self.grade = MaterialGrade.objects.create(code='EN-8D', name='Medium Carbon Steel EN8D')
        self.lot = RawMaterialIntake.objects.create(
            lot_number='LOT-2026-HND-01',
            supplier_name='Tata Steel',
            purchase_order_no='PO-HND-001',
            material_grade=self.grade,
            heat_number='HEAT-HND-771',
            quantity_received=Decimal('200.00'),
            unit=QuantityUnit.KG,
            status=IntakeStatus.IN_STORE,
            lab_status=LabStatus.PASSED,
            barcode_identifier='BAR-LOT-HND-01',
            mtc_file='mtc_documents/dummy.pdf',
            received_by=self.out_operator,
        )

        self.part = Part.objects.create(
            part_number='PART-HND-201',
            part_name='Spur Gear Hub',
            material_grade=self.grade,
            drawing_number='DWG-HND-201',
            revision_level='Rev A'
        )

        # Work Order & Job Traveler
        self.wo = WorkOrder.objects.create(
            work_order_number='WO-2026-HND-001',
            part=self.part,
            raw_material_lot=self.lot,
            target_quantity=100,
            completed_quantity=45,
            status=WorkOrderStatus.RELEASED,
        )

        self.traveler = JobTraveler.objects.create(
            work_order=self.wo,
            traveler_barcode='TRV-WO-2026-HND-001',
            status=JobTravelerStatus.ACTIVE
        )

    def test_handover_creation_by_authorized_operator(self):
        """Outgoing operator creates shift handover log capturing tool wear, machine health, and counts."""
        self.client.login(username='out_op', password='password123')
        create_url = reverse('handover:handover_create')

        response = self.client.post(create_url, {
            'workstation': self.ws.id,
            'outgoing_shift': ShiftType.MORNING,
            'incoming_shift': ShiftType.EVENING,
            'active_traveler': self.traveler.id,
            'parts_produced_count': 45,
            'scrap_count': 2,
            'tool_wear_status': 'Roughing insert T01 replaced at 11:30. Offsets updated by -0.015mm on X-axis.',
            'machine_health_notes': 'Spindle vibration stable, coolant concentration checked at 8% refractometer.',
            'open_quality_alerts': 'Monitor pitch diameter on Pin 3 after every 15 cycles.',
            'pending_pdi_reviews': 'First-piece inspection report signed off by QA.',
        }, follow=True)

        self.assertEqual(ShiftHandoverLog.objects.count(), 1)
        log = ShiftHandoverLog.objects.first()

        self.assertRedirects(response, reverse('handover:handover_detail', kwargs={'log_id': log.id}))
        self.assertEqual(log.status, ShiftHandoverStatus.PENDING_ACK)
        self.assertFalse(log.is_acknowledged)
        self.assertEqual(log.parts_produced_count, 45)
        self.assertEqual(log.scrap_count, 2)
        self.assertEqual(log.outgoing_operator, self.out_operator)

        # Audit trail verification
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.ActionType.SHIFT_HANDOVER,
            object_id=str(log.id)
        ).exists())

    def test_incoming_operator_digital_acknowledgment(self):
        """Incoming operator reviews handover notes and signs off before machine startup."""
        log = ShiftHandoverLog.objects.create(
            log_number='SHL-CNC-02-1001',
            workstation=self.ws,
            outgoing_shift=ShiftType.MORNING,
            incoming_shift=ShiftType.EVENING,
            outgoing_operator=self.out_operator,
            active_traveler=self.traveler,
            parts_produced_count=45,
            scrap_count=2,
            tool_wear_status='Insert T01 changed.',
            machine_health_notes='Coolant normal.',
            status=ShiftHandoverStatus.PENDING_ACK,
        )

        self.client.login(username='in_op', password='password123')
        ack_url = reverse('handover:handover_acknowledge', kwargs={'log_id': log.id})

        response = self.client.post(ack_url, {
            'incoming_notes': 'Verified tool offsets and chuck pressure at 25 bar. Cleared for evening production.'
        }, follow=True)

        log.refresh_from_db()
        self.assertTrue(log.is_acknowledged)
        self.assertEqual(log.status, ShiftHandoverStatus.ACKNOWLEDGED)
        self.assertEqual(log.incoming_operator, self.in_operator)
        self.assertIsNotNone(log.acknowledged_at)
        self.assertIn('Verified tool offsets', log.incoming_notes)

        # Audit trail verification
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.ActionType.SHIFT_HANDOVER_ACK,
            object_id=str(log.id)
        ).exists())

    def test_handover_list_and_detail_views(self):
        """Handover list page displays records and filters correctly."""
        log = ShiftHandoverLog.objects.create(
            log_number='SHL-CNC-02-1002',
            workstation=self.ws,
            outgoing_shift=ShiftType.MORNING,
            incoming_shift=ShiftType.EVENING,
            outgoing_operator=self.out_operator,
            parts_produced_count=30,
            scrap_count=1,
            tool_wear_status='Normal wear.',
            machine_health_notes='All gauges green.',
            status=ShiftHandoverStatus.PENDING_ACK,
        )

        self.client.login(username='out_op', password='password123')
        list_res = self.client.get(reverse('handover:handover_list'))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, log.log_number)
        self.assertContains(list_res, self.ws.machine_code)

        detail_res = self.client.get(reverse('handover:handover_detail', kwargs={'log_id': log.id}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, log.log_number)
        self.assertContains(detail_res, 'Normal wear.')
