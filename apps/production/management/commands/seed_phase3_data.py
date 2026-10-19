from decimal import Decimal
import os
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.inventory.models import MaterialGrade, RawMaterialIntake
from apps.master_data.models import ToolType, Workstation
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
    InspectionParameter,
    InspectionTemplate,
    InspectionTemplateRevision,
    ParameterType,
    Part,
    RevisionStatus,
    TemplateType,
    ThresholdType,
)


class Command(BaseCommand):
    help = "Seeds Phase 3 data: parts, inspection templates, blueprints with pins, work orders, and job travelers."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("--- Seeding Phase 3 Quality & Production Master Data ---"))

        # 1. Fetch Users
        mgr = User.objects.filter(username='quality_mgr').first() or User.objects.filter(role='QUALITY_MANAGER').first()
        eng = User.objects.filter(username='engineer').first() or User.objects.filter(role='QUALITY_ENGINEER').first()
        sup = User.objects.filter(username='supervisor').first() or User.objects.filter(role='SHIFT_SUPERVISOR').first()

        # 2. Fetch Grade
        grade_4140 = MaterialGrade.objects.filter(code='AISI-4140').first()
        if not grade_4140:
            self.stdout.write(self.style.ERROR("Grade AISI-4140 not found. Run seed_phase2_data first."))
            return

        # 3. Create Part
        part, _ = Part.objects.get_or_create(
            part_number='PART-SH-401',
            defaults={
                'part_name': 'Precision Transmission Drive Shaft',
                'material_grade': grade_4140,
                'drawing_number': 'DWG-2026-SH401',
                'revision_level': 'Rev A',
                'description': 'High-tensile alloy steel drive shaft for heavy automotive transmission gearbox.',
                'is_active': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Component Part: {part.part_number} ({part.part_name})"))

        # 4. Create Inspection Template
        tpl, _ = InspectionTemplate.objects.get_or_create(
            template_code='TPL-SH401-PDI',
            defaults={
                'part': part,
                'title': 'Pre-Dispatch Final Inspection Plan - Drive Shaft',
                'template_type': TemplateType.FINAL_PDI,
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Inspection Template: {tpl.template_code}"))

        # 5. Create Template Revision (Approved by QM)
        rev, _ = InspectionTemplateRevision.objects.get_or_create(
            template=tpl,
            revision_label='Rev A',
            defaults={
                'status': RevisionStatus.APPROVED,
                'created_by': eng or mgr,
                'approved_by': mgr,
                'approved_at': timezone.now(),
                'approval_notes': 'Dimensions, tolerances, and CTQ designations formally approved for production.',
            }
        )
        # Ensure approved status
        if rev.status != RevisionStatus.APPROVED:
            rev.status = RevisionStatus.APPROVED
            rev.approved_by = mgr
            rev.approved_at = timezone.now()
            rev.save()
        self.stdout.write(self.style.SUCCESS(f"Template Revision: {rev.revision_label} (Status: {rev.status})"))

        # 6. Generate Blueprint Drawing Image & Create Blueprint Record
        media_bp_dir = os.path.join(settings.MEDIA_ROOT, 'blueprints')
        os.makedirs(media_bp_dir, exist_ok=True)
        bp_path = os.path.join(media_bp_dir, 'blueprint_drive_shaft.png')

        # Draw an engineering blueprint diagram
        img = Image.new('RGB', (900, 520), color=(14, 43, 82))  # Blueprint dark blue
        draw = ImageDraw.Draw(img)

        # Drawing border & grid
        for x in range(20, 880, 40):
            draw.line([(x, 20), (x, 500)], fill=(24, 60, 110), width=1)
        for y in range(20, 500, 40):
            draw.line([(20, y), (880, y)], fill=(24, 60, 110), width=1)
        draw.rectangle([(20, 20), (880, 500)], outline=(255, 255, 255), width=2)

        # Shaft silhouette
        # Section 1: left journal
        draw.rectangle([(100, 210), (280, 310)], fill=(30, 80, 145), outline=(255, 255, 255), width=2)
        # Section 2: center hub
        draw.rectangle([(280, 160), (580, 360)], fill=(38, 95, 170), outline=(255, 255, 255), width=2)
        # Section 3: right journal
        draw.rectangle([(580, 210), (780, 310)], fill=(30, 80, 145), outline=(255, 255, 255), width=2)
        # Centerline
        draw.line([(60, 260), (820, 260)], fill=(255, 200, 50), width=1)

        # Title Block in bottom right corner
        draw.rectangle([(550, 420), (875, 495)], fill=(10, 30, 60), outline=(255, 255, 255), width=2)
        draw.text((560, 428), "DWG: DWG-2026-SH401  REV: A", fill=(255, 255, 255))
        draw.text((560, 448), "PART: TRANSMISSION DRIVE SHAFT", fill=(255, 255, 255))
        draw.text((560, 468), "ZAPUZA TECHNOLOGIES LLP", fill=(255, 215, 0))

        # Annotations
        draw.text((120, 170), "Pin 1: Ø25.00 [CTQ]", fill=(255, 200, 50))
        draw.text((360, 120), "Pin 2: Length 150.00", fill=(255, 255, 255))
        draw.text((610, 170), "Pin 3: Runout 0.02 [CTQ]", fill=(255, 200, 50))

        img.save(bp_path, 'PNG')

        bp, created = Blueprint.objects.get_or_create(
            template_revision=rev,
            title='Sheet 1: Transmission Shaft Dimensions & Tolerances',
            defaults={'drawing_file': 'blueprints/blueprint_drive_shaft.png'}
        )
        if not created and not bp.drawing_file:
            bp.drawing_file = 'blueprints/blueprint_drive_shaft.png'
            bp.save()
        self.stdout.write(self.style.SUCCESS(f"Engineering Blueprint: {bp.title}"))

        # 7. Create Inspection Parameters
        p1, _ = InspectionParameter.objects.get_or_create(
            template_revision=rev,
            sequence_order=1,
            defaults={
                'parameter_name': 'Shaft Journal Outer Diameter Ø25.000',
                'parameter_type': ParameterType.DIMENSION,
                'nominal_value': Decimal('25.000'),
                'upper_tolerance': Decimal('0.050'),
                'lower_tolerance': Decimal('-0.020'),
                'unit': 'mm',
                'is_ctq': True,
                'required_tool_type': ToolType.MICROMETER,
            }
        )

        p2, _ = InspectionParameter.objects.get_or_create(
            template_revision=rev,
            sequence_order=2,
            defaults={
                'parameter_name': 'Overall Shaft Length 150.00',
                'parameter_type': ParameterType.DIMENSION,
                'nominal_value': Decimal('150.000'),
                'upper_tolerance': Decimal('0.200'),
                'lower_tolerance': Decimal('-0.200'),
                'unit': 'mm',
                'is_ctq': False,
                'required_tool_type': ToolType.CALIPER,
            }
        )

        p3, _ = InspectionParameter.objects.get_or_create(
            template_revision=rev,
            sequence_order=3,
            defaults={
                'parameter_name': 'Surface Finish Roughness Ra 0.8',
                'parameter_type': ParameterType.THRESHOLD,
                'threshold_type': ThresholdType.MAX,
                'threshold_limit': Decimal('0.800'),
                'unit': 'Ra',
                'is_ctq': False,
                'required_tool_type': ToolType.OTHER,
            }
        )

        p4, _ = InspectionParameter.objects.get_or_create(
            template_revision=rev,
            sequence_order=4,
            defaults={
                'parameter_name': 'Radial Runout Tolerance 0.020 MAX',
                'parameter_type': ParameterType.THRESHOLD,
                'threshold_type': ThresholdType.MAX,
                'threshold_limit': Decimal('0.020'),
                'unit': 'mm',
                'is_ctq': True,
                'required_tool_type': ToolType.OTHER,
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Inspection Parameters: 4 parameters created (2 CTQ)."))

        # 8. Create Blueprint Pins (Normalized Coordinates)
        BlueprintPin.objects.get_or_create(
            blueprint=bp,
            pin_number=1,
            defaults={
                'parameter': p1,
                'label': 'Pin 1: Shaft Journal Ø25.00',
                'coordinate_x': Decimal('0.2100'),
                'coordinate_y': Decimal('0.5000'),
            }
        )

        BlueprintPin.objects.get_or_create(
            blueprint=bp,
            pin_number=2,
            defaults={
                'parameter': p2,
                'label': 'Pin 2: Overall Length 150.00',
                'coordinate_x': Decimal('0.4800'),
                'coordinate_y': Decimal('0.2900'),
            }
        )

        BlueprintPin.objects.get_or_create(
            blueprint=bp,
            pin_number=3,
            defaults={
                'parameter': p4,
                'label': 'Pin 3: Radial Runout 0.02 MAX',
                'coordinate_x': Decimal('0.7500'),
                'coordinate_y': Decimal('0.5000'),
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Blueprint Pins: 3 pins mapped to drawing coordinates."))

        # 9. Create Work Order & Job Traveler
        lot_001 = RawMaterialIntake.objects.filter(lot_number='LOT-2026-001').first()
        if not lot_001:
            self.stdout.write(self.style.ERROR("Lot LOT-2026-001 not found. Run seed_phase2_data first."))
            return

        work_order, wo_created = WorkOrder.objects.get_or_create(
            work_order_number='WO-2026-001',
            defaults={
                'part': part,
                'raw_material_lot': lot_001,
                'target_quantity': 50,
                'status': WorkOrderStatus.RELEASED,
                'released_by': sup,
                'released_at': timezone.now(),
            }
        )

        traveler, trv_created = JobTraveler.objects.get_or_create(
            work_order=work_order,
            defaults={
                'traveler_barcode': f"TRV-{work_order.work_order_number}",
                'current_operation_sequence': 10,
                'status': JobTravelerStatus.ACTIVE,
            }
        )

        # 10. Populate Sequential Operations
        ws_cnc = Workstation.objects.filter(machine_code='CNC-04').first()
        ws_vmc = Workstation.objects.filter(machine_code='VMC-02').first()
        ws_oven = Workstation.objects.filter(machine_code='OVEN-01').first()
        ws_grind = Workstation.objects.filter(machine_code='GRIND-03').first()
        ws_line = Workstation.objects.filter(machine_code='LINE-01').first()

        ops_specs = [
            (10, 'Op 10: Raw Material Cutting & Billet Prep', ws_vmc or ws_cnc, False, 0, None, OperationStatus.READY),
            (20, 'Op 20: CNC Rough Turning & Profiling', ws_cnc, False, 0, None, OperationStatus.PENDING),
            (30, 'Op 30: Vacuum Heat Treatment & Quench', ws_oven, True, 240, None, OperationStatus.PENDING),
            (40, 'Op 40: Precision Cylindrical Grinding', ws_grind, False, 0, None, OperationStatus.PENDING),
            (50, 'Op 50: Final Pre-Dispatch Inspection (PDI) & Wash', ws_line, False, 0, rev, OperationStatus.PENDING),
        ]

        for seq, name, ws, hold, hold_min, template_rev, status in ops_specs:
            if ws:
                TravelerOperation.objects.get_or_create(
                    traveler=traveler,
                    operation_sequence=seq,
                    defaults={
                        'operation_name': name,
                        'workstation': ws,
                        'requires_hold_time': hold,
                        'hold_duration_minutes': hold_min,
                        'inspection_template_revision': template_rev,
                        'status': status,
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Work Order {work_order.work_order_number} released with Job Traveler {traveler.traveler_barcode} (5 sequential operations)."))
        self.stdout.write(self.style.SUCCESS("--- Phase 3 Data Seeding Successfully Completed ---"))
