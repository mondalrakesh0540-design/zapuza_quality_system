from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.master_data.models import Workstation, ShiftType
from apps.production.models import JobTraveler


class ShiftHandoverStatus(models.TextChoices):
    PENDING_ACK = 'PENDING_ACK', 'Awaiting Incoming Shift Acknowledgment'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Formally Acknowledged & Signed Off'


class ShiftHandoverLog(models.Model):
    """
    Mandatory Digital Shift Handover Logbook.
    Conforms to BRD Section 12.2.
    Captures open job status, machine health, tooling wear, scrap count, and pending quality checks.
    Incoming workers must review and digitally acknowledge before running production.
    """
    log_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g. SHL-2026-0001"
    )
    workstation = models.ForeignKey(
        Workstation,
        on_delete=models.PROTECT,
        related_name='shift_handovers'
    )
    outgoing_shift = models.CharField(
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.MORNING
    )
    incoming_shift = models.CharField(
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.EVENING
    )
    outgoing_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='outgoing_shift_handovers'
    )
    incoming_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='acknowledged_shift_handovers'
    )
    active_traveler = models.ForeignKey(
        JobTraveler,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shift_handovers'
    )
    parts_produced_count = models.PositiveIntegerField(
        default=0,
        help_text="Total acceptable parts produced during the outgoing shift"
    )
    scrap_count = models.PositiveIntegerField(
        default=0,
        help_text="Defective / scrapped components segregated during shift"
    )
    tool_wear_status = models.TextField(
        help_text="Insert wear status, tool offset adjustments, drill/cutter replacements"
    )
    machine_health_notes = models.TextField(
        help_text="Spindle temperature, hydraulic pressure, vibration, coolant level notes"
    )
    open_quality_alerts = models.TextField(
        blank=True,
        help_text="Active CTQ warnings, first-piece clearances, or critical tolerances"
    )
    pending_pdi_reviews = models.TextField(
        blank=True,
        help_text="Checklists awaiting supervisor review or laboratory test results"
    )
    status = models.CharField(
        max_length=30,
        choices=ShiftHandoverStatus.choices,
        default=ShiftHandoverStatus.PENDING_ACK
    )
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    incoming_notes = models.TextField(
        blank=True,
        help_text="Remarks added by incoming operator during sign-off"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Digital Shift Handover Log'
        verbose_name_plural = 'Digital Shift Handover Logs'

    def __str__(self):
        return f"{self.log_number} - {self.workstation.machine_code} ({self.get_outgoing_shift_display()} -> {self.get_incoming_shift_display()})"

    def acknowledge(self, incoming_user, remarks=""):
        self.incoming_operator = incoming_user
        self.is_acknowledged = True
        self.status = ShiftHandoverStatus.ACKNOWLEDGED
        self.acknowledged_at = timezone.now()
        self.incoming_notes = remarks
        self.save(update_fields=['incoming_operator', 'is_acknowledged', 'status', 'acknowledged_at', 'incoming_notes'])
