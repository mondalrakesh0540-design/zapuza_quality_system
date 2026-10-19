from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import UserRole
from apps.audit_trail.models import AuditLog
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

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds initial master data, 5 primary roles, workstations, PM logs, and measuring tools for Phase 1.'

    def handle(self, *args, **options):
        self.stdout.write("--- Starting Phase 1 Master Data Seeding ---")

        # 1. Create Core Users for each role
        users_data = [
            {
                'username': 'plant.manager',
                'employee_id': 'EMP-101',
                'first_name': 'Vikram',
                'last_name': 'Mehta',
                'role': UserRole.PLANT_MANAGER,
                'email': 'plant.manager@zapuza.com',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'quality.manager',
                'employee_id': 'EMP-102',
                'first_name': 'Ananya',
                'last_name': 'Sharma',
                'role': UserRole.QUALITY_MANAGER,
                'email': 'quality.manager@zapuza.com',
                'is_staff': True,
            },
            {
                'username': 'quality.engineer',
                'employee_id': 'EMP-103',
                'first_name': 'Rohan',
                'last_name': 'Kulkarni',
                'role': UserRole.QUALITY_ENGINEER,
                'email': 'quality.engineer@zapuza.com',
                'is_staff': False,
            },
            {
                'username': 'shift.supervisor',
                'employee_id': 'EMP-104',
                'first_name': 'Suresh',
                'last_name': 'Patel',
                'role': UserRole.SHIFT_SUPERVISOR,
                'email': 'shift.supervisor@zapuza.com',
                'is_staff': False,
            },
            {
                'username': 'qa.inspector',
                'employee_id': 'EMP-105',
                'first_name': 'Deepak',
                'last_name': 'Verma',
                'role': UserRole.QA_FLOOR_INSPECTOR,
                'email': 'qa.inspector@zapuza.com',
                'is_staff': False,
            },
        ]

        created_users = {}
        for udata in users_data:
            user, created = User.objects.get_or_create(
                username=udata['username'],
                defaults={
                    'employee_id': udata['employee_id'],
                    'first_name': udata['first_name'],
                    'last_name': udata['last_name'],
                    'role': udata['role'],
                    'email': udata['email'],
                    'is_staff': udata.get('is_staff', False),
                    'is_superuser': udata.get('is_superuser', False),
                }
            )
            user.set_password('password123')
            user.save()
            created_users[udata['role']] = user
            status_text = "Created" if created else "Updated password for"
            self.stdout.write(f"  [User] {status_text} {user.username} ({user.get_role_display()})")

        # 2. Departments
        dept_mach, _ = Department.objects.get_or_create(
            code='MACH',
            defaults={'name': 'Main Machining Shop', 'description': 'CNC turning centers, VMCs, and horizontal mills.'}
        )
        dept_heat, _ = Department.objects.get_or_create(
            code='HEAT',
            defaults={'name': 'Heat Treatment Bay', 'description': 'Stress relief, vacuum furnaces, quenching baths.'}
        )
        dept_assy, _ = Department.objects.get_or_create(
            code='ASSY',
            defaults={'name': 'Final Assembly Line', 'description': 'Component assembly, torque verification, packaging.'}
        )
        self.stdout.write("  [Departments] MACH, HEAT, ASSY verified.")

        # 3. Workstations
        ws_cnc4, _ = Workstation.objects.get_or_create(
            machine_code='CNC-04',
            defaults={
                'name': 'CNC Lathe #04',
                'department': dept_mach,
                'qr_code_identifier': 'WS-CNC-04-QR',
                'status': WorkstationStatus.IDLE,
            }
        )
        ws_vmc2, _ = Workstation.objects.get_or_create(
            machine_code='VMC-02',
            defaults={
                'name': 'VMC Station #02',
                'department': dept_mach,
                'qr_code_identifier': 'WS-VMC-02-QR',
                'status': WorkstationStatus.IDLE,
            }
        )
        ws_oven1, _ = Workstation.objects.get_or_create(
            machine_code='OVEN-01',
            defaults={
                'name': 'Heat Treat Oven #01',
                'department': dept_heat,
                'qr_code_identifier': 'WS-OVEN-01-QR',
                'status': WorkstationStatus.IDLE,
            }
        )
        ws_grind3, _ = Workstation.objects.get_or_create(
            machine_code='GRIND-03',
            defaults={
                'name': 'Cylindrical Grinder #03',
                'department': dept_mach,
                'qr_code_identifier': 'WS-GRIND-03-QR',
                'status': WorkstationStatus.MAINTENANCE_LOCKED,
            }
        )
        ws_line1, _ = Workstation.objects.get_or_create(
            machine_code='LINE-01',
            defaults={
                'name': 'Assembly Station #01',
                'department': dept_assy,
                'qr_code_identifier': 'WS-LINE-01-QR',
                'status': WorkstationStatus.IDLE,
            }
        )
        self.stdout.write("  [Workstations] CNC-04, VMC-02, OVEN-01, GRIND-03, LINE-01 registered.")

        # 4. Daily PM Logs for Today
        today = timezone.now().date()
        supervisor = created_users[UserRole.SHIFT_SUPERVISOR]

        # CNC-04 has a valid PASSED PM check for today
        pm_cnc, _ = MachinePMLog.objects.get_or_create(
            workstation=ws_cnc4,
            log_date=today,
            shift=ShiftType.MORNING,
            defaults={
                'completed_by': supervisor,
                'zero_point_verified': True,
                'lubrication_level_ok': True,
                'safety_interlocks_ok': True,
                'spindle_runout_ok': True,
                'pneumatic_pressure_ok': True,
                'emergency_stop_tested': True,
                'is_passed': True,
                'remarks': 'Morning shift startup OK. Spindle runout 0.003mm within 0.005mm spec.'
            }
        )

        # OVEN-01 also has a passed PM check
        pm_oven, _ = MachinePMLog.objects.get_or_create(
            workstation=ws_oven1,
            log_date=today,
            shift=ShiftType.MORNING,
            defaults={
                'completed_by': supervisor,
                'zero_point_verified': True,
                'lubrication_level_ok': True,
                'safety_interlocks_ok': True,
                'spindle_runout_ok': True,
                'pneumatic_pressure_ok': True,
                'emergency_stop_tested': True,
                'is_passed': True,
                'remarks': 'Thermocouple zero-point calibrated, vacuum seals inspected.'
            }
        )

        self.stdout.write("  [Daily PM] Signed off for CNC-04 and OVEN-01. (VMC-02 and LINE-01 left overdue for lockout testing).")

        # 5. Measuring Tools Register
        tools_data = [
            {
                'tool_id': 'VC-104',
                'name': 'Mitutoyo Digital Caliper 0-150mm',
                'tool_type': ToolType.CALIPER,
                'serial_number': 'MT-VC-104-2025',
                'calibration_date': today - timedelta(days=60),
                'calibration_expiry_date': today + timedelta(days=120),
                'status': ToolStatus.CALIBRATED,
                'storage_location': 'Tool Crib - Shelf A-02',
                'notes': 'Certified master caliper for machining bay.'
            },
            {
                'tool_id': 'MIC-02',
                'name': 'Outside Micrometer 25-50mm (0.001mm)',
                'tool_type': ToolType.MICROMETER,
                'serial_number': 'MT-MIC-02-2024',
                'calibration_date': today - timedelta(days=380),
                'calibration_expiry_date': today - timedelta(days=15),  # EXPIRED!
                'status': ToolStatus.EXPIRED,
                'storage_location': 'Tool Crib - Calibration Quarantine Box',
                'notes': 'EXPIRED TOOL: Used for automated testing of Section 2.3 calibration lockout.'
            },
            {
                'tool_id': 'HG-01',
                'name': 'Mitutoyo Digital Height Gauge 0-300mm',
                'tool_type': ToolType.HEIGHT_GAUGE,
                'serial_number': 'MT-HG-01-2025',
                'calibration_date': today - timedelta(days=30),
                'calibration_expiry_date': today + timedelta(days=150),
                'status': ToolStatus.CALIBRATED,
                'storage_location': 'Inspection Granite Table 1',
                'notes': 'Dedicated granite plate gauge.'
            },
            {
                'tool_id': 'PG-04',
                'name': 'Thread Plug Gauge M12 x 1.5 - 6H',
                'tool_type': ToolType.PLUG_GAUGE,
                'serial_number': 'TPG-M12-04-2025',
                'calibration_date': today - timedelta(days=90),
                'calibration_expiry_date': today + timedelta(days=90),
                'status': ToolStatus.CALIBRATED,
                'storage_location': 'Tool Crib - Drawer T-04',
                'notes': 'Thread Go/No-Go plug gauge.'
            },
            {
                'tool_id': 'CMM-01',
                'name': 'Zeiss Spectrum Coordinate Measuring Machine',
                'tool_type': ToolType.CMM,
                'serial_number': 'ZS-CMM-8921-2024',
                'calibration_date': today - timedelta(days=45),
                'calibration_expiry_date': today + timedelta(days=320),
                'status': ToolStatus.CALIBRATED,
                'storage_location': 'Quality Metrology Cleanroom',
                'notes': 'Annual calibration certificate ref #ZEISS-CAL-2026-081.'
            },
        ]

        for tdata in tools_data:
            tool, created = InspectionTool.objects.get_or_create(
                tool_id=tdata['tool_id'],
                defaults=tdata
            )
            status_text = "Registered" if created else "Updated"
            self.stdout.write(f"  [Tool] {status_text} {tool.tool_id} ({tool.name}) - Status: {tool.status}")

        # 6. Initial Audit Log
        AuditLog.log(
            action=AuditLog.ActionType.CREATE,
            user=created_users[UserRole.PLANT_MANAGER],
            model_name='System',
            object_id='1',
            object_repr='Phase 1 Initialization',
            details='Phase 1 baseline master data, workstations, PM logs, and measuring tools seeded.'
        )

        self.stdout.write(self.style.SUCCESS("--- Phase 1 Data Seeding Successfully Completed ---"))
