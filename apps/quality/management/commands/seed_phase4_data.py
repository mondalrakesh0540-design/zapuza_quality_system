from decimal import Decimal
import os
from PIL import Image, ImageDraw
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.inventory.models import RawMaterialIntake
from apps.master_data.models import InspectionTool, MachinePMLog, ShiftType, ToolStatus, ToolType, Workstation
from apps.production.models import (
    JobTraveler,
    JobTravelerStatus,
    OperationStatus,
    TravelerOperation,
    WorkOrder,
    WorkOrderStatus,
)
from apps.quality.models import (
    FloorInspection,
    FloorInspectionStatus,
    InspectionDefectPhoto,
    InspectionMeasurement,
    InspectionParameter,
    InspectionTemplate,
    InspectionTemplateRevision,
    Part,
)


class Command(BaseCommand):
    help = "Seeds Phase 4 data: dual QR inspection records, defect photos, and supervisor review queues."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("--- Seeding Phase 4 Floor Inspection & Review Data ---"))

        # 1. Fetch Users
        inspector = User.objects.filter(username='inspector').first() or User.objects.filter(role='QA_FLOOR_INSPECTOR').first()
        supervisor = User.objects.filter(username='supervisor').first() or User.objects.filter(role='SHIFT_SUPERVISOR').first()

        # 2. Workstations & Daily PM
        today = timezone.now().date()
        for ws in Workstation.objects.filter(is_active=True):
            MachinePMLog.objects.get_or_create(
                workstation=ws,
                log_date=today,
                shift=ShiftType.MORNING,
                defaults={
                    'completed_by': supervisor or inspector,
                    'zero_point_verified': True,
                    'lubrication_level_ok': True,
                    'safety_interlocks_ok': True,
                    'spindle_runout_ok': True,
                    'pneumatic_pressure_ok': True,
                    'emergency_stop_tested': True,
                    'is_passed': True,
                    'remarks': "Daily morning PM passed.",
                }
            )

        # 3. Fetch Part & Template
        part = Part.objects.filter(part_number='PART-SH-401').first()
        template = InspectionTemplate.objects.filter(template_code='TPL-SH401-PDI').first()
        revision = template.get_approved_revision() if template else None

        if not part or not revision:
            self.stdout.write(self.style.ERROR("Phase 3 data missing. Run seed_phase3_data first."))
            return

        # 4. Fetch Calibrated Measuring Tools
        micrometer = InspectionTool.objects.filter(tool_type=ToolType.MICROMETER, status=ToolStatus.CALIBRATED).first() or InspectionTool.objects.filter(tool_type=ToolType.MICROMETER).first()
        caliper = InspectionTool.objects.filter(tool_type=ToolType.CALIPER, status=ToolStatus.CALIBRATED).first() or InspectionTool.objects.filter(tool_type=ToolType.CALIPER).first()

        # 5. Fetch Traveler & Operation
        traveler = JobTraveler.objects.filter(traveler_barcode='TRV-WO-2026-001').first()
        if not traveler:
            self.stdout.write(self.style.ERROR("Traveler TRV-WO-2026-001 not found."))
            return

        op20 = traveler.operations.filter(operation_sequence=20).first()
        if op20:
            op20.inspection_template_revision = revision
            op20.save(update_fields=['inspection_template_revision'])

        # 6. Create a Sample Defect Photo
        defects_dir = os.path.join(settings.MEDIA_ROOT, 'inspection_defects')
        os.makedirs(defects_dir, exist_ok=True)
        sample_photo_path = os.path.join(defects_dir, 'sample_defect_gauge.png')

        img = Image.new('RGB', (640, 480), color=(40, 40, 40))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(80, 80), (560, 400)], outline=(255, 0, 0), width=3)
        draw.text((100, 100), "DIGITAL GAUGE READING OUT OF SPEC", fill=(255, 255, 255))
        draw.text((100, 140), "Measured: 150.230 mm (Limit: 150.200 mm)", fill=(255, 80, 80))
        draw.text((100, 180), "Part: PART-SH-401 Drive Shaft", fill=(200, 200, 200))
        draw.text((100, 220), "Op 20: CNC Rough Turning & Profiling", fill=(200, 200, 200))
        img.save(sample_photo_path, 'PNG')

        # 7. Create Inspection 1: Non-CTQ Deviation (Awaiting Supervisor Review, Eligible for Concession)
        insp1, created1 = FloorInspection.objects.get_or_create(
            inspection_number='INSP-2026-001',
            defaults={
                'traveler_operation': op20,
                'template_revision': revision,
                'workstation': op20.workstation,
                'inspector': inspector,
                'station_qr_scanned': op20.workstation.qr_code_identifier,
                'traveler_barcode_scanned': traveler.traveler_barcode,
                'is_demo_scan': True,
                'status': FloorInspectionStatus.PENDING_REVIEW,
                'inspector_notes': "Slight oversize on overall shaft length (+0.030mm over upper limit). Shaft journal diameter CTQ is perfect 25.020 mm.",
            }
        )

        # Measurements for Inspection 1
        params = list(revision.parameters.all())
        p_diam = next((p for p in params if p.is_ctq), params[0])
        p_len = next((p for p in params if not p.is_ctq and p.parameter_type == 'DIMENSION'), params[1])

        # Diam reading (In spec CTQ)
        InspectionMeasurement.objects.get_or_create(
            inspection=insp1,
            parameter=p_diam,
            defaults={
                'measuring_tool': micrometer,
                'measured_value': Decimal('25.020'),
            }
        )

        # Length reading (Out of spec NON-CTQ: 150.230 mm)
        InspectionMeasurement.objects.get_or_create(
            inspection=insp1,
            parameter=p_len,
            defaults={
                'measuring_tool': caliper,
                'measured_value': Decimal('150.230'),
            }
        )

        # Attach Defect Photo
        InspectionDefectPhoto.objects.get_or_create(
            inspection=insp1,
            parameter=p_len,
            defaults={
                'photo_file': 'inspection_defects/sample_defect_gauge.png',
                'caption': 'Digital Caliper reading 150.230 mm on overall length',
            }
        )

        insp1.recalculate_tolerance_and_ctq()
        self.stdout.write(self.style.SUCCESS(f"Inspection 1: {insp1.inspection_number} created (Pending Review, Concession-eligible)."))

        self.stdout.write(self.style.SUCCESS("--- Phase 4 Data Seeding Successfully Completed ---"))
