from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import UserRole
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

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds Phase 2 material grades, incoming raw stock lots, MTC records, lab tests, and SNCRs.'

    def handle(self, *args, **options):
        self.stdout.write("--- Starting Phase 2 Inventory & Traceability Seeding ---")

        # Get relevant users
        pm_user = User.objects.filter(role=UserRole.PLANT_MANAGER).first()
        qm_user = User.objects.filter(role=UserRole.QUALITY_MANAGER).first()
        qe_user = User.objects.filter(role=UserRole.QUALITY_ENGINEER).first()
        sup_user = User.objects.filter(role=UserRole.SHIFT_SUPERVISOR).first()
        insp_user = User.objects.filter(role=UserRole.QA_FLOOR_INSPECTOR).first()

        creator = sup_user or qm_user or pm_user

        # 1. Material Grades
        grade_4140, _ = MaterialGrade.objects.get_or_create(
            code='AISI-4140',
            defaults={
                'name': 'High-Tensile Chromium-Molybdenum Alloy Steel',
                'carbon_min': Decimal('0.380'),
                'carbon_max': Decimal('0.430'),
                'manganese_min': Decimal('0.750'),
                'manganese_max': Decimal('1.000'),
                'silicon_min': Decimal('0.150'),
                'silicon_max': Decimal('0.350'),
                'phosphorus_max': Decimal('0.035'),
                'sulfur_max': Decimal('0.040'),
                'yield_strength_min': Decimal('415.00'),
                'tensile_strength_min': Decimal('655.00'),
                'hardness_max': Decimal('220.00'),
                'requires_lab_testing': True,
                'description': 'Standard shaft and gear alloy steel with high fatigue strength.'
            }
        )

        grade_en8d, _ = MaterialGrade.objects.get_or_create(
            code='EN-8D',
            defaults={
                'name': 'Medium Carbon Unalloyed Machinery Steel',
                'carbon_min': Decimal('0.400'),
                'carbon_max': Decimal('0.450'),
                'manganese_min': Decimal('0.700'),
                'manganese_max': Decimal('0.900'),
                'silicon_min': Decimal('0.100'),
                'silicon_max': Decimal('0.350'),
                'phosphorus_max': Decimal('0.040'),
                'sulfur_max': Decimal('0.040'),
                'yield_strength_min': Decimal('320.00'),
                'tensile_strength_min': Decimal('550.00'),
                'hardness_max': Decimal('200.00'),
                'requires_lab_testing': True,
                'description': 'General purpose shafts, bolts, studs, and axle components.'
            }
        )

        grade_316l, _ = MaterialGrade.objects.get_or_create(
            code='SS-316L',
            defaults={
                'name': 'Marine-Grade Low Carbon Austenitic Stainless Steel',
                'carbon_min': Decimal('0.010'),
                'carbon_max': Decimal('0.030'),
                'manganese_min': Decimal('1.000'),
                'manganese_max': Decimal('2.000'),
                'silicon_min': Decimal('0.200'),
                'silicon_max': Decimal('0.750'),
                'phosphorus_max': Decimal('0.045'),
                'sulfur_max': Decimal('0.030'),
                'yield_strength_min': Decimal('220.00'),
                'tensile_strength_min': Decimal('520.00'),
                'hardness_max': Decimal('215.00'),
                'requires_lab_testing': True,
                'description': 'Corrosion-resistant stainless steel for valve and chemical applications.'
            }
        )
        self.stdout.write("  [Material Grades] AISI-4140, EN-8D, SS-316L specifications verified.")

        # Dummy MTC content
        dummy_mtc_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Certified Mill Test Certificate - Jindal Steel) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"

        # 2. Lot 1: H-8042 (CLEARED FOR PRODUCTION)
        lot1, created1 = RawMaterialIntake.objects.get_or_create(
            lot_number='LOT-2026-001',
            defaults={
                'heat_number': 'H-8042',
                'supplier_name': 'Jindal Steel & Power Ltd',
                'purchase_order_no': 'PO-2026-891',
                'material_grade': grade_4140,
                'quantity_received': Decimal('5000.00'),
                'unit': QuantityUnit.KG,
                'mtc_verified': True,
                'mtc_verified_by': qm_user,
                'mtc_verified_at': timezone.now(),
                'lab_status': LabStatus.PASSED,
                'status': IntakeStatus.IN_STORE,
                'barcode_identifier': 'RAW-LOT-2026-001-H-8042',
                'received_by': creator,
                'notes': 'Dock delivery inspected. Visual check free of heavy rust or deep seams.'
            }
        )
        if created1 or not lot1.mtc_file:
            lot1.mtc_file.save('MTC_H-8042_Jindal_Cert.pdf', ContentFile(dummy_mtc_content), save=True)

        # Lab test for Lot 1 (conforming)
        if not lot1.lab_tests.exists():
            MaterialLabTest.objects.create(
                intake=lot1,
                tested_by=qe_user or creator,
                test_date=timezone.now().date(),
                carbon_actual=Decimal('0.405'),
                manganese_actual=Decimal('0.820'),
                silicon_actual=Decimal('0.230'),
                phosphorus_actual=Decimal('0.018'),
                sulfur_actual=Decimal('0.015'),
                yield_strength_actual=Decimal('460.00'),
                tensile_strength_actual=Decimal('695.00'),
                hardness_actual=Decimal('195.00'),
                evaluation_summary='All chemical spectro and mechanical properties conform to AISI-4140 specification.'
            )
        self.stdout.write("  [Lot 1] LOT-2026-001 (Heat #H-8042): CLEARED FOR WORK ORDERS.")

        # 3. Lot 2: H-9102 (IN LAB TESTING & MTC UNVERIFIED)
        lot2, created2 = RawMaterialIntake.objects.get_or_create(
            lot_number='LOT-2026-002',
            defaults={
                'heat_number': 'H-9102',
                'supplier_name': 'Tata Steel Long Products',
                'purchase_order_no': 'PO-2026-904',
                'material_grade': grade_en8d,
                'quantity_received': Decimal('3500.00'),
                'unit': QuantityUnit.KG,
                'mtc_verified': False,
                'lab_status': LabStatus.IN_LAB_TESTING,
                'status': IntakeStatus.IN_STORE,
                'barcode_identifier': 'RAW-LOT-2026-002-H-9102',
                'received_by': creator,
                'notes': 'Material in holding bay. Spectro samples sent to metallurgical laboratory.'
            }
        )
        if created2 or not lot2.mtc_file:
            lot2.mtc_file.save('MTC_H-9102_TataSteel_Cert.pdf', ContentFile(dummy_mtc_content), save=True)
        self.stdout.write("  [Lot 2] LOT-2026-002 (Heat #H-9102): IN LAB TESTING (WORK ORDER ISSUANCE BLOCKED).")

        # 4. Lot 3: H-7701 (REJECTED / QUARANTINED WITH SNCR)
        lot3, created3 = RawMaterialIntake.objects.get_or_create(
            lot_number='LOT-2026-003',
            defaults={
                'heat_number': 'H-7701',
                'supplier_name': 'Kalyani Steels Ltd',
                'purchase_order_no': 'PO-2026-855',
                'material_grade': grade_4140,
                'quantity_received': Decimal('2000.00'),
                'unit': QuantityUnit.KG,
                'mtc_verified': True,
                'mtc_verified_by': qm_user,
                'mtc_verified_at': timezone.now(),
                'lab_status': LabStatus.FAILED,
                'status': IntakeStatus.QUARANTINED,
                'barcode_identifier': 'RAW-LOT-2026-003-H-7701',
                'received_by': creator,
                'notes': 'Chemical spectro failure: Carbon level 0.520% exceeds max 0.430%.'
            }
        )
        if created3 or not lot3.mtc_file:
            lot3.mtc_file.save('MTC_H-7701_Kalyani_Cert.pdf', ContentFile(dummy_mtc_content), save=True)

        if not lot3.lab_tests.exists():
            MaterialLabTest.objects.create(
                intake=lot3,
                tested_by=qe_user or creator,
                test_date=timezone.now().date(),
                carbon_actual=Decimal('0.520'),  # High carbon!
                manganese_actual=Decimal('0.850'),
                silicon_actual=Decimal('0.240'),
                phosphorus_actual=Decimal('0.022'),
                sulfur_actual=Decimal('0.020'),
                yield_strength_actual=Decimal('510.00'),
                tensile_strength_actual=Decimal('740.00'),
                hardness_actual=Decimal('245.00'),  # Hardness exceeds 220
                evaluation_summary='Carbon 0.520% exceeds maximum 0.430%; Hardness 245 exceeds maximum allowed 220.'
            )

        if not lot3.ncrs.exists():
            SupplierNCR.objects.create(
                sncr_number='SNCR-2026-001',
                intake=lot3,
                logged_by=qm_user or creator,
                reason_category=SNCRReasonCategory.CHEMICAL_OUT_OF_SPEC,
                disposition=SNCRDisposition.SUPPLIER_QUARANTINE_HOLD,
                defect_description='Spectro chemical analysis revealed excessive carbon content (0.520% vs max 0.430%). Risk of quench cracking.',
                corrective_action_requested='Vendor 8D failure investigation report required within 7 business days. Debit note for stock value.'
            )
        self.stdout.write("  [Lot 3] LOT-2026-003 (Heat #H-7701): QUARANTINED WITH SNCR-2026-001.")

        self.stdout.write(self.style.SUCCESS("--- Phase 2 Inventory Data Seeding Successfully Completed ---"))
