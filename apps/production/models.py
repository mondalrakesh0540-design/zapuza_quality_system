from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.inventory.models import RawMaterialIntake
from apps.master_data.models import Workstation
from apps.quality.models import InspectionTemplateRevision, Part


class WorkOrderStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft (Planned)'
    RELEASED = 'RELEASED', 'Released to Shopfloor'
    IN_PROGRESS = 'IN_PROGRESS', 'In Production'
    COMPLETED = 'COMPLETED', 'Fully Completed'
    ON_HOLD = 'ON_HOLD', 'Quality Hold'


class WorkOrder(models.Model):
    """
    Shopfloor manufacturing work order.
    Conforms to BRD Section 7.1: Released to generate unique Job Traveler.
    """
    work_order_number = models.CharField(max_length=50, unique=True, help_text="e.g. WO-2026-001")
    part = models.ForeignKey(
        Part,
        on_delete=models.PROTECT,
        related_name='work_orders'
    )
    raw_material_lot = models.ForeignKey(
        RawMaterialIntake,
        on_delete=models.PROTECT,
        related_name='work_orders'
    )
    target_quantity = models.PositiveIntegerField(help_text="Planned component batch quantity")
    completed_quantity = models.PositiveIntegerField(default=0)
    scrapped_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=30,
        choices=WorkOrderStatus.choices,
        default=WorkOrderStatus.DRAFT
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_work_orders'
    )
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Production Work Order'
        verbose_name_plural = 'Production Work Orders'

    def __str__(self):
        return f"{self.work_order_number} - {self.part.part_number} (Qty: {self.target_quantity})"

    def clean(self):
        # Validate raw material grade compatibility
        if self.part and self.raw_material_lot:
            if self.part.material_grade != self.raw_material_lot.material_grade:
                raise ValidationError(
                    f"Material Incompatibility: Part requires {self.part.material_grade.code}, "
                    f"but selected lot '{self.raw_material_lot.lot_number}' is {self.raw_material_lot.material_grade.code}."
                )

    def release(self, user):
        """
        Enforce Section 3.2 & 7.1:
        Cannot release work order if raw material lot is unverified or quarantined!
        """
        self.raw_material_lot.validate_for_work_order_issue()
        self.status = WorkOrderStatus.RELEASED
        self.released_by = user
        self.released_at = timezone.now()
        self.save(update_fields=['status', 'released_by', 'released_at'])

        # Ensure Job Traveler exists
        traveler, created = JobTraveler.objects.get_or_create(
            work_order=self,
            defaults={'traveler_barcode': f"TRV-{self.work_order_number}"}
        )
        return traveler


class JobTravelerStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active on Shopfloor'
    COMPLETED = 'COMPLETED', 'All Operations Complete'
    QUARANTINED = 'QUARANTINED', 'Quarantined / Defect Hold'


class JobTraveler(models.Model):
    """
    Digital Job Traveler Sheet accompanying physical batch through manufacturing.
    Conforms to BRD Section 7.1.
    """
    work_order = models.OneToOneField(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name='traveler'
    )
    traveler_barcode = models.CharField(
        max_length=100,
        unique=True,
        help_text="Barcode printed on job traveler sheet (e.g. TRV-WO-2026-001)"
    )
    current_operation_sequence = models.PositiveIntegerField(default=10)
    status = models.CharField(
        max_length=30,
        choices=JobTravelerStatus.choices,
        default=JobTravelerStatus.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Digital Job Traveler'
        verbose_name_plural = 'Digital Job Travelers'

    def __str__(self):
        return f"{self.traveler_barcode} ({self.work_order.part.part_number})"

    def get_current_operation(self):
        """Returns the active or next pending operation in sequence."""
        return self.operations.exclude(status=OperationStatus.COMPLETED).order_by('operation_sequence').first()

    def get_pdi_operation(self):
        """
        Retrieves the designated Pre-Dispatch Inspection (PDI) operation on this traveler.
        Matches template_type=FINAL_PDI or operation_name containing 'PDI'.
        """
        from apps.quality.models import TemplateType
        pdi_op = self.operations.filter(
            inspection_template_revision__template__template_type=TemplateType.FINAL_PDI
        ).first()
        if not pdi_op:
            pdi_op = self.operations.filter(operation_name__icontains='PDI').first()
        return pdi_op

    def is_ready_for_pdi(self) -> tuple[bool, str]:
        """
        Server-side validation checking if this job traveler is eligible to undergo Final PDI.
        Enforces Section 7.1, 8.2, and 10.1 of BRD:
        1. Traveler must not be quarantined.
        2. Designated PDI operation must exist.
        3. 100% of operations preceding PDI must be completed.
        4. No hold timer on preceding operations may be active.
        """
        if self.status == JobTravelerStatus.QUARANTINED:
            return False, f"Traveler '{self.traveler_barcode}' is currently locked under QUALITY QUARANTINE."

        pdi_op = self.get_pdi_operation()
        if not pdi_op:
            return False, f"No designated Pre-Dispatch Inspection (PDI) operation found on traveler '{self.traveler_barcode}'."

        prior_ops = self.operations.filter(operation_sequence__lt=pdi_op.operation_sequence)
        incomplete_prior = prior_ops.exclude(status=OperationStatus.COMPLETED).order_by('operation_sequence').first()
        if incomplete_prior:
            return False, (
                f"Sequential Routing Lockout: Preceding step 'Op {incomplete_prior.operation_sequence}: "
                f"{incomplete_prior.operation_name}' is not completed. Final PDI cannot begin until all machining operations are signed off."
            )

        for op in prior_ops:
            hold_active, remaining_min = op.is_hold_active()
            if hold_active:
                return False, (
                    f"Process Hold Active: Op {op.operation_sequence} ({op.operation_name}) has an active "
                    f"cooling/aging hold ({remaining_min} minutes remaining). Final PDI is locked."
                )

        return True, "Traveler is cleared and ready for Final Pre-Dispatch Inspection."

    def get_pdi_inspection(self):
        """Returns the most recent FloorInspection associated with the PDI operation."""
        pdi_op = self.get_pdi_operation()
        if not pdi_op:
            return None
        return pdi_op.inspections.order_by('-created_at').first()

    def is_pdi_approved(self) -> bool:
        """Checks whether Final PDI has been formally approved or concession-approved by Quality."""
        from apps.quality.models import FloorInspectionStatus
        inspection = self.get_pdi_inspection()
        if not inspection:
            return False
        return inspection.status in [FloorInspectionStatus.APPROVED, FloorInspectionStatus.CONCESSION_APPROVED]

    def validate_for_dispatch(self) -> tuple[bool, list[str]]:
        """
        Strict server-side shipping interlock evaluation conforming to BRD Section 10.1.
        Returns: (can_dispatch: bool, lockout_reasons: list[str])
        """
        from apps.quality.models import FloorInspectionStatus
        reasons = []

        if self.status == JobTravelerStatus.QUARANTINED:
            reasons.append(f"Quality Quarantine Lockout: Job Traveler '{self.traveler_barcode}' is under quarantine hold.")

        incomplete_ops = self.operations.exclude(status=OperationStatus.COMPLETED)
        if incomplete_ops.exists():
            op_list = ", ".join(f"Op {op.operation_sequence} ({op.operation_name})" for op in incomplete_ops)
            reasons.append(f"Incomplete Operations: {incomplete_ops.count()} operation(s) are not completed: [{op_list}].")

        for op in self.operations.all():
            hold_active, rem_min = op.is_hold_active()
            if hold_active:
                reasons.append(f"Process Hold Active: Op {op.operation_sequence} ({op.operation_name}) has {rem_min} minutes remaining.")

        pdi_op = self.get_pdi_operation()
        if not pdi_op:
            reasons.append("Missing PDI Routing: No Pre-Dispatch Inspection (PDI) operation is configured for this traveler.")
        else:
            pdi_insp = self.get_pdi_inspection()
            if not pdi_insp:
                reasons.append("Missing PDI Inspection: Final PDI checklist has not been performed on the shopfloor.")
            elif pdi_insp.status == FloorInspectionStatus.PENDING_REVIEW:
                reasons.append(f"PDI Pending Review: Final PDI inspection '{pdi_insp.inspection_number}' is awaiting Quality Manager / Supervisor sign-off.")
            elif pdi_insp.status == FloorInspectionStatus.REJECTED_QUARANTINED:
                reasons.append(f"PDI Rejection: Final PDI inspection '{pdi_insp.inspection_number}' was REJECTED by quality.")
            elif pdi_insp.status not in [FloorInspectionStatus.APPROVED, FloorInspectionStatus.CONCESSION_APPROVED]:
                reasons.append(f"PDI Not Cleared: Final PDI status is '{pdi_insp.get_status_display()}'.")

        unresolved = self.operations.filter(inspections__status=FloorInspectionStatus.PENDING_REVIEW).distinct()
        if unresolved.exists():
            reasons.append(f"Unresolved Quality Review: {unresolved.count()} operation(s) have inspections awaiting supervisor review.")

        return (len(reasons) == 0, reasons)


class OperationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending (Upstream Incomplete)'
    READY = 'READY', 'Ready to Start'
    RUNNING = 'RUNNING', 'Active Machining / Processing'
    HOLD_WAIT = 'HOLD_WAIT', 'Mandatory Process Hold Active'
    COMPLETED = 'COMPLETED', 'Signed Off & Completed'


class TravelerOperation(models.Model):
    """
    Individual sequential routing operation on a job traveler.
    Conforms to BRD Section 7.1 (Sequential Routing) & 8.2 (Process Hold Timers).
    """
    traveler = models.ForeignKey(
        JobTraveler,
        on_delete=models.CASCADE,
        related_name='operations'
    )
    operation_sequence = models.PositiveIntegerField(
        help_text="Numerical sequence: 10, 20, 30, 40, 50, 60..."
    )
    operation_name = models.CharField(
        max_length=150,
        help_text="e.g. Op 10: Raw Material Sawing, Op 20: CNC Rough Turning"
    )
    workstation = models.ForeignKey(
        Workstation,
        on_delete=models.PROTECT,
        related_name='assigned_operations'
    )
    inspection_template_revision = models.ForeignKey(
        InspectionTemplateRevision,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Mandatory checklist revision required for this operation sign-off"
    )

    # Process Hold / Cooling / Chemical Curing Timers (BRD Section 8.1 & 8.2)
    requires_hold_time = models.BooleanField(
        default=False,
        help_text="Whether this operation enforces a cooling, curing, or resting hold after execution."
    )
    hold_duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Mandatory hold countdown duration in minutes (e.g. 240 for 4 hours)"
    )
    hold_start_time = models.DateTimeField(null=True, blank=True)
    hold_release_time = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=OperationStatus.choices,
        default=OperationStatus.PENDING
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_operations'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['traveler', 'operation_sequence']
        unique_together = ('traveler', 'operation_sequence')
        verbose_name = 'Traveler Sequential Operation'
        verbose_name_plural = 'Traveler Sequential Operations'

    def __str__(self):
        return f"{self.traveler.traveler_barcode} - Op {self.operation_sequence}: {self.operation_name}"

    def get_previous_operation(self):
        """Returns immediate prior operation in the sequence."""
        return self.traveler.operations.filter(
            operation_sequence__lt=self.operation_sequence
        ).order_by('-operation_sequence').first()

    def is_previous_operation_completed(self) -> bool:
        prev = self.get_previous_operation()
        if not prev:
            return True  # First operation has no preceding step
        return prev.status == OperationStatus.COMPLETED

    def is_hold_active(self) -> tuple[bool, int]:
        """
        Check if hold timer on this operation or preceding operation is still ticking down.
        Returns: (is_active: bool, remaining_minutes: int)
        """
        now = timezone.now()

        # 1. Check if this operation itself has an unexpired hold
        if self.requires_hold_time and self.hold_release_time:
            if now < self.hold_release_time:
                remaining_sec = int((self.hold_release_time - now).total_seconds())
                remaining_min = max(1, remaining_sec // 60)
                return True, remaining_min

        # 2. Check if preceding operation has an unexpired hold
        prev = self.get_previous_operation()
        if prev and prev.requires_hold_time and prev.hold_release_time:
            if now < prev.hold_release_time:
                remaining_sec = int((prev.hold_release_time - now).total_seconds())
                remaining_min = max(1, remaining_sec // 60)
                return True, remaining_min

        return False, 0

    def can_start(self, date=None, shift=None) -> tuple[bool, str]:
        """
        Strict server-side sequential routing and machine lockout interlock.
        Enforces Section 7.1, 2.2, and 8.2.
        Returns: (can_start: bool, reason: str)
        """
        # 1. Enforce Sequential Progression (cannot skip steps)
        if not self.is_previous_operation_completed():
            prev = self.get_previous_operation()
            return False, (
                f"Sequential Routing Lockout: Op {prev.operation_sequence} ({prev.operation_name}) "
                f"is incomplete. You cannot start Op {self.operation_sequence} until all prior operations are signed off."
            )

        # 2. Enforce Mandatory Process Hold / Cooling Timers (Section 8.2)
        hold_active, remaining_min = self.is_hold_active()
        if hold_active:
            prev = self.get_previous_operation()
            return False, (
                f"Mandatory Process Hold Active: Lot is undergoing mandatory cooling/curing hold "
                f"from Op {prev.operation_sequence} ({remaining_min} minutes remaining). "
                f"Downstream machining is locked."
            )

        # 3. Enforce Workstation Daily PM and Maintenance Lockouts (Section 2.2)
        can_ws_start, ws_reason = self.workstation.can_start_job(date=date, shift=shift)
        if not can_ws_start:
            return False, f"Assigned Workstation Lockout: {ws_reason}"

        return True, "Operation cleared to start on workstation."

    def start_operation(self, user):
        """Transition operation to RUNNING if cleared."""
        can_run, reason = self.can_start()
        if not can_run:
            raise ValidationError(reason)
        self.status = OperationStatus.RUNNING
        self.save(update_fields=['status'])

    def complete_operation(self, user, remarks=""):
        """Sign off operation and release next step."""
        now = timezone.now()
        self.status = OperationStatus.COMPLETED
        self.completed_by = user
        self.completed_at = now
        self.remarks = remarks

        if self.requires_hold_time and self.hold_duration_minutes > 0:
            self.hold_start_time = now
            self.hold_release_time = now + timedelta(minutes=self.hold_duration_minutes)

        self.save()

        # Update traveler current operation index
        next_op = self.traveler.operations.filter(
            operation_sequence__gt=self.operation_sequence
        ).order_by('operation_sequence').first()

        if next_op:
            self.traveler.current_operation_sequence = next_op.operation_sequence
            if next_op.status == OperationStatus.PENDING:
                next_op.status = OperationStatus.READY
                next_op.save(update_fields=['status'])
        else:
            self.traveler.status = JobTravelerStatus.COMPLETED

        self.traveler.save()
