from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Department(models.Model):
    """
    Physical facility section or plant floor department.
    e.g., Main Machining Shop, Heat Treatment Bay, Final Assembly Line.
    """
    code = models.CharField(max_length=20, unique=True, help_text="e.g. MACH, HEAT, ASSY")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Plant Department'
        verbose_name_plural = 'Plant Departments'

    def __str__(self):
        return f"{self.code} - {self.name}"


class WorkstationStatus(models.TextChoices):
    IDLE = 'IDLE', 'Idle / Available'
    RUNNING = 'RUNNING', 'In Production'
    SETUP_MODE = 'SETUP_MODE', 'Setup Mode (First Piece Pending)'
    MAINTENANCE_LOCKED = 'MAINTENANCE_LOCKED', 'Maintenance Locked'


class Workstation(models.Model):
    """
    Individual production machinery or shopfloor workstation.
    e.g., CNC Lathe #04, VMC Station #02, Heat Treat Oven #01.
    """
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='workstations'
    )
    machine_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique identifier, e.g. CNC-04, VMC-02"
    )
    name = models.CharField(max_length=100, help_text="e.g. CNC Lathe #04")
    qr_code_identifier = models.CharField(
        max_length=100,
        unique=True,
        help_text="Exact string encoded in physical QR plate mounted on machine frame"
    )
    status = models.CharField(
        max_length=30,
        choices=WorkstationStatus.choices,
        default=WorkstationStatus.IDLE
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['machine_code']
        verbose_name = 'Machine / Workstation'
        verbose_name_plural = 'Machines & Workstations'

    def __str__(self):
        return f"{self.machine_code} ({self.name}) - {self.department.code}"

    def get_latest_pm_log(self, date=None, shift=None):
        """Retrieve PM log for a specific date (default today) and optional shift."""
        target_date = date or timezone.now().date()
        qs = self.pm_logs.filter(log_date=target_date)
        if shift:
            qs = qs.filter(shift=shift)
        return qs.order_by('-created_at').first()

    def is_daily_pm_completed(self, date=None, shift=None) -> bool:
        """
        Server-side validation checking if mandatory daily PM checklist is signed and passed.
        """
        latest_pm = self.get_latest_pm_log(date=date, shift=shift)
        if not latest_pm:
            return False
        return latest_pm.is_passed

    def can_start_job(self, date=None, shift=None) -> tuple[bool, str]:
        """
        Strict server-side lock:
        Evaluates whether an operator or inspector can start or select a job on this workstation.
        Returns: (can_start: bool, reason: str)
        """
        if not self.is_active:
            return False, f"Machine '{self.machine_code}' is currently marked as INACTIVE."

        if self.status == WorkstationStatus.MAINTENANCE_LOCKED:
            return False, f"Machine '{self.machine_code}' is currently locked under MAINTENANCE LOCKOUT."

        if not self.is_daily_pm_completed(date=date, shift=shift):
            target_date = date or timezone.now().date()
            return False, (
                f"Machine PM Lockout: Daily Preventive Maintenance (PM) check for '{self.machine_code}' "
                f"is overdue for {target_date:%Y-%m-%d}. Job selection is disabled on this workstation."
            )

        return True, f"Machine '{self.machine_code}' is cleared for production."


class ShiftType(models.TextChoices):
    MORNING = 'MORNING', 'Morning Shift (06:00 - 14:00)'
    EVENING = 'EVENING', 'Evening Shift (14:00 - 22:00)'
    NIGHT = 'NIGHT', 'Night Shift (22:00 - 06:00)'


class MachinePMLog(models.Model):
    """
    Daily and shift-based setup verification and Preventive Maintenance (PM) checklist.
    Conforms to Section 2.2 of the BRD.
    """
    workstation = models.ForeignKey(
        Workstation,
        on_delete=models.CASCADE,
        related_name='pm_logs'
    )
    log_date = models.DateField(default=timezone.now, db_index=True)
    shift = models.CharField(
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.MORNING
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='completed_pm_logs'
    )
    # Required daily safety & zero-point checklist items
    zero_point_verified = models.BooleanField(
        default=False,
        help_text="Safety zero-point and machine datum verified"
    )
    lubrication_level_ok = models.BooleanField(
        default=False,
        help_text="Spindle/way lube reservoirs at adequate level"
    )
    safety_interlocks_ok = models.BooleanField(
        default=False,
        help_text="Door safety interlocks and light curtains tested"
    )
    spindle_runout_ok = models.BooleanField(
        default=False,
        help_text="Spindle runout & tool holder seating verified"
    )
    pneumatic_pressure_ok = models.BooleanField(
        default=False,
        help_text="Main air supply pressure within operating range"
    )
    emergency_stop_tested = models.BooleanField(
        default=False,
        help_text="Physical E-stop button tested and functional"
    )
    is_passed = models.BooleanField(
        default=False,
        help_text="Overall PM status. Automatically calculated unless overridden by supervisor"
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-log_date', '-created_at']
        unique_together = ('workstation', 'log_date', 'shift')
        verbose_name = 'Machine Daily PM Log'
        verbose_name_plural = 'Machine Daily PM Logs'

    def __str__(self):
        status_str = "PASSED" if self.is_passed else "FAILED"
        return f"{self.workstation.machine_code} PM ({self.log_date} {self.shift}) - {status_str}"

    def clean(self):
        """
        Server-side validation: All mandatory checks must pass for the PM check to pass.
        """
        all_checks = [
            self.zero_point_verified,
            self.lubrication_level_ok,
            self.safety_interlocks_ok,
            self.spindle_runout_ok,
            self.pneumatic_pressure_ok,
            self.emergency_stop_tested,
        ]
        if all(all_checks):
            self.is_passed = True
        else:
            self.is_passed = False

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ToolType(models.TextChoices):
    CALIPER = 'CALIPER', 'Vernier / Digital Caliper'
    MICROMETER = 'MICROMETER', 'Outside / Inside Micrometer'
    HEIGHT_GAUGE = 'HEIGHT_GAUGE', 'Digital Height Gauge'
    PLUG_GAUGE = 'PLUG_GAUGE', 'Thread / Pin Plug Gauge'
    BORE_GAUGE = 'BORE_GAUGE', 'Dial Bore Gauge'
    CMM = 'CMM', 'Coordinate Measuring Machine'
    OTHER = 'OTHER', 'Other Gauge / Instrument'


class ToolStatus(models.TextChoices):
    CALIBRATED = 'CALIBRATED', 'Calibrated & Valid'
    EXPIRED = 'EXPIRED', 'Calibration Expired'
    OUT_OF_SERVICE = 'OUT_OF_SERVICE', 'Out of Service / Damaged'


class InspectionTool(models.Model):
    """
    Measuring Gauges & Equipment Register.
    Conforms to Section 2.1(4) and Section 2.3 of the BRD.
    """
    tool_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique digital ID, e.g. VC-104, MIC-02, PG-04"
    )
    name = models.CharField(max_length=100, help_text="e.g. Mitutoyo Digital Caliper 0-150mm")
    tool_type = models.CharField(max_length=30, choices=ToolType.choices, default=ToolType.CALIPER)
    serial_number = models.CharField(max_length=100, unique=True)
    calibration_date = models.DateField(help_text="Date of last calibration certificate")
    calibration_expiry_date = models.DateField(help_text="Date calibration certificate expires", db_index=True)
    status = models.CharField(
        max_length=30,
        choices=ToolStatus.choices,
        default=ToolStatus.CALIBRATED
    )
    storage_location = models.CharField(max_length=100, default='Tool Crib', help_text="Crib bin or workstation station")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tool_id']
        verbose_name = 'Measuring Tool / Gauge'
        verbose_name_plural = 'Measuring Tools & Equipment Register'

    def __str__(self):
        return f"{self.tool_id} - {self.name} (Exp: {self.calibration_expiry_date})"

    @property
    def is_calibration_valid(self) -> bool:
        """
        Check whether the gauge is calibrated and current date is before expiry.
        """
        today = timezone.now().date()
        if self.status != ToolStatus.CALIBRATED:
            return False
        return self.calibration_expiry_date >= today

    @property
    def days_until_expiry(self) -> int:
        today = timezone.now().date()
        return (self.calibration_expiry_date - today).days

    def validate_for_measurement(self):
        """
        Enforce Section 2.3:
        If gauge calibration interval has expired or status is invalid,
        blocks measurement entry with exact 'Expired Tool Calibration' error.
        """
        if not self.is_calibration_valid:
            today = timezone.now().date()
            if self.calibration_expiry_date < today or self.status == ToolStatus.EXPIRED:
                raise ValidationError(
                    f"Expired Tool Calibration: The selected gauge '{self.tool_id}' ({self.name}) "
                    f"expired on {self.calibration_expiry_date:%Y-%m-%d}. "
                    "Entry blocked. Please obtain a calibrated tool from the tool crib."
                )
            else:
                raise ValidationError(
                    f"Tool Calibration Error: The selected gauge '{self.tool_id}' is marked as {self.get_status_display()}. "
                    "Entry blocked. Please obtain a calibrated tool from the tool crib."
                )
