import hashlib
import secrets
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from apps.inventory.models import MaterialGrade
from apps.master_data.models import ToolType


class Part(models.Model):
    """
    Manufactured part or component specification.
    e.g. Drive Shaft, Spur Gear, Flange Hub.
    """
    part_number = models.CharField(max_length=50, unique=True, help_text="e.g. PART-SH-401")
    part_name = models.CharField(max_length=150, help_text="e.g. Precision Transmission Drive Shaft")
    material_grade = models.ForeignKey(
        MaterialGrade,
        on_delete=models.PROTECT,
        related_name='manufactured_parts'
    )
    drawing_number = models.CharField(max_length=100, help_text="e.g. DWG-2026-SH401")
    revision_level = models.CharField(max_length=20, default='Rev A')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['part_number']
        verbose_name = 'Manufactured Part'
        verbose_name_plural = 'Manufactured Parts'

    def __str__(self):
        return f"{self.part_number} - {self.part_name} ({self.revision_level})"


class TemplateType(models.TextChoices):
    IN_PROCESS = 'IN_PROCESS', 'In-Process Inspection Checklist'
    FINAL_PDI = 'FINAL_PDI', 'Pre-Dispatch Inspection (PDI) Checklist'


class InspectionTemplate(models.Model):
    """
    Inspection checklist container mapped to a part.
    Tracks revisions under strict engineering change control.
    """
    part = models.ForeignKey(
        Part,
        on_delete=models.CASCADE,
        related_name='templates'
    )
    template_type = models.CharField(
        max_length=30,
        choices=TemplateType.choices,
        default=TemplateType.FINAL_PDI
    )
    title = models.CharField(max_length=150, help_text="e.g. Final PDI Inspection Plan")
    template_code = models.CharField(max_length=50, unique=True, help_text="e.g. TPL-SH401-PDI")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['template_code']
        verbose_name = 'Inspection Checklist Template'
        verbose_name_plural = 'Inspection Checklist Templates'

    def __str__(self):
        return f"{self.template_code} - {self.title} ({self.part.part_number})"

    def get_latest_revision(self):
        return self.revisions.order_by('-created_at').first()

    def get_approved_revision(self):
        return self.revisions.filter(status=RevisionStatus.APPROVED).order_by('-approved_at').first()


class RevisionStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft (Work in Progress)'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Quality Manager Review'
    APPROVED = 'APPROVED', 'Approved for Production'
    SUPERSEDED = 'SUPERSEDED', 'Superseded by Newer Revision'


class InspectionTemplateRevision(models.Model):
    """
    Specific revision of an inspection checklist (Rev A, Rev B...).
    Conforms to BRD Section 4.1: Must be approved by Quality Manager before floor release.
    """
    template = models.ForeignKey(
        InspectionTemplate,
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    revision_label = models.CharField(max_length=20, default='Rev A', help_text="e.g. Rev A, Rev B")
    status = models.CharField(
        max_length=30,
        choices=RevisionStatus.choices,
        default=RevisionStatus.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_template_revisions'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_template_revisions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['template', '-created_at']
        unique_together = ('template', 'revision_label')
        verbose_name = 'Template Revision'
        verbose_name_plural = 'Template Revisions'

    def __str__(self):
        return f"{self.template.template_code} [{self.revision_label}] - {self.get_status_display()}"

    @property
    def is_locked(self) -> bool:
        """Approved or superseded revisions are permanently locked from modifications."""
        return self.status in [RevisionStatus.APPROVED, RevisionStatus.SUPERSEDED]

    def approve(self, manager_user, notes=""):
        """
        Enforce Section 4.1: Quality Manager approval gate.
        Supersedes prior approved revisions and activates this revision for shopfloor use.
        """
        if not (manager_user.is_quality_manager or manager_user.is_superuser):
            raise ValidationError("Access Denied: Only a Quality Manager can formally approve inspection templates.")

        # Supersede any currently approved revision for this template
        InspectionTemplateRevision.objects.filter(
            template=self.template,
            status=RevisionStatus.APPROVED
        ).update(status=RevisionStatus.SUPERSEDED)

        self.status = RevisionStatus.APPROVED
        self.approved_by = manager_user
        self.approved_at = timezone.now()
        self.approval_notes = notes
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'approval_notes'])


class Blueprint(models.Model):
    """
    Uploaded engineering drawing blueprint file (PDF or high-res image).
    Conforms to BRD Section 4.2.
    """
    template_revision = models.ForeignKey(
        InspectionTemplateRevision,
        on_delete=models.CASCADE,
        related_name='blueprints'
    )
    title = models.CharField(max_length=150, help_text="e.g. Sheet 1: Machining Dimensions & Tolerances")
    drawing_file = models.FileField(
        upload_to='blueprints/',
        help_text="Engineering drawing blueprint (PDF or Image)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Engineering Blueprint'
        verbose_name_plural = 'Engineering Blueprints'

    def __str__(self):
        return f"{self.title} ({self.template_revision.template.template_code} {self.template_revision.revision_label})"


class ParameterType(models.TextChoices):
    DIMENSION = 'DIMENSION', 'Dimension with Plus/Minus Tolerances'
    THRESHOLD = 'THRESHOLD', 'Maximum or Minimum Threshold'
    VISUAL = 'VISUAL', 'Visual Pass/Fail Check'


class ThresholdType(models.TextChoices):
    MAX = 'MAX', 'Maximum Allowable Limit (<=)'
    MIN = 'MIN', 'Minimum Allowable Limit (>=)'


class InspectionParameter(models.Model):
    """
    Individual inspection check parameter on a checklist revision.
    Conforms to BRD Section 4.2 & 4.3 (Tolerances and CTQ Tagging).
    """
    template_revision = models.ForeignKey(
        InspectionTemplateRevision,
        on_delete=models.CASCADE,
        related_name='parameters'
    )
    parameter_name = models.CharField(max_length=150, help_text="e.g. Shaft Outer Diameter Ø25.00")
    parameter_type = models.CharField(
        max_length=30,
        choices=ParameterType.choices,
        default=ParameterType.DIMENSION
    )

    # 1. Dimension Fields (Nominal +/- Tolerances)
    nominal_value = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True,
        help_text="Target nominal size (e.g. 25.000)"
    )
    upper_tolerance = models.DecimalField(
        max_digits=8, decimal_places=3,
        null=True, blank=True,
        help_text="Upper allowable deviation (e.g. +0.050)"
    )
    lower_tolerance = models.DecimalField(
        max_digits=8, decimal_places=3,
        null=True, blank=True,
        help_text="Lower allowable deviation (e.g. -0.020)"
    )

    # 2. Threshold Fields (Max or Min Limits)
    threshold_type = models.CharField(
        max_length=20,
        choices=ThresholdType.choices,
        null=True, blank=True
    )
    threshold_limit = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True,
        help_text="Limit value (e.g. Ra 0.8 MAX or Runout 0.02 MAX)"
    )

    unit = models.CharField(max_length=20, default='mm', help_text="e.g. mm, Ra, degrees")
    is_ctq = models.BooleanField(
        default=False,
        help_text="Critical-to-Quality parameter. Highlighted in orange; carries zero-concession rule."
    )
    required_tool_type = models.CharField(
        max_length=30,
        choices=ToolType.choices,
        default=ToolType.CALIPER,
        help_text="Mandatory instrument category for this check"
    )
    sequence_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['template_revision', 'sequence_order']
        verbose_name = 'Inspection Parameter'
        verbose_name_plural = 'Inspection Parameters'

    def __str__(self):
        ctq_str = " [CTQ]" if self.is_ctq else ""
        return f"{self.sequence_order}. {self.parameter_name}{ctq_str} ({self.get_parameter_type_display()})"

    @property
    def upper_limit(self) -> Decimal | None:
        if self.parameter_type == ParameterType.DIMENSION and self.nominal_value is not None:
            upper = self.upper_tolerance if self.upper_tolerance is not None else Decimal('0.000')
            return self.nominal_value + upper
        elif self.parameter_type == ParameterType.THRESHOLD and self.threshold_type == ThresholdType.MAX:
            return self.threshold_limit
        return None

    @property
    def lower_limit(self) -> Decimal | None:
        if self.parameter_type == ParameterType.DIMENSION and self.nominal_value is not None:
            lower = self.lower_tolerance if self.lower_tolerance is not None else Decimal('0.000')
            return self.nominal_value + lower
        elif self.parameter_type == ParameterType.THRESHOLD and self.threshold_type == ThresholdType.MIN:
            return self.threshold_limit
        return None

    def evaluate_reading(self, measured_value=None, visual_passed=None) -> tuple[bool, str]:
        """
        Server-side tolerance validation conforming to Section 4.2 & 5.4.
        Returns: (is_passed: bool, message: str)
        """
        if self.parameter_type == ParameterType.VISUAL:
            if visual_passed is None:
                return False, "Visual inspection result not recorded."
            return (visual_passed is True, "Visual inspection passed." if visual_passed else "Visual defect detected.")

        if measured_value is None:
            return False, "Measurement value is missing."

        val = Decimal(str(measured_value))

        if self.parameter_type == ParameterType.DIMENSION:
            low = self.lower_limit
            high = self.upper_limit
            if low is not None and val < low:
                return False, f"Out of Tolerance: {val} {self.unit} is below lower limit ({low} {self.unit})."
            if high is not None and val > high:
                return False, f"Out of Tolerance: {val} {self.unit} exceeds upper limit ({high} {self.unit})."
            return True, f"In Tolerance: {val} {self.unit} within [{low} to {high} {self.unit}]."

        elif self.parameter_type == ParameterType.THRESHOLD:
            if self.threshold_type == ThresholdType.MAX and self.threshold_limit is not None:
                if val > self.threshold_limit:
                    return False, f"Exceeds Maximum: {val} {self.unit} > limit ({self.threshold_limit} {self.unit})."
            elif self.threshold_type == ThresholdType.MIN and self.threshold_limit is not None:
                if val < self.threshold_limit:
                    return False, f"Below Minimum: {val} {self.unit} < limit ({self.threshold_limit} {self.unit})."
            return True, f"Threshold satisfied: {val} {self.unit} meets specification."

        return True, "Parameter evaluation passed."


class BlueprintPin(models.Model):
    """
    Interactive color-coded coordinate pin placed on engineering drawing.
    Conforms to BRD Section 4.2.
    Stores normalized X/Y coordinates (0.0 to 1.0) for responsive scaling.
    """
    blueprint = models.ForeignKey(
        Blueprint,
        on_delete=models.CASCADE,
        related_name='pins'
    )
    parameter = models.OneToOneField(
        InspectionParameter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pin'
    )
    pin_number = models.PositiveIntegerField(help_text="e.g. Pin 1, Pin 2")
    label = models.CharField(max_length=100, help_text="e.g. Pin 1: Journal Diameter")
    
    # Normalized coordinates (0.0 to 1.0 corresponding to 0% to 100% of drawing width/height)
    coordinate_x = models.DecimalField(
        max_digits=6, decimal_places=4,
        help_text="Normalized horizontal coordinate (0.0000 to 1.0000)"
    )
    coordinate_y = models.DecimalField(
        max_digits=6, decimal_places=4,
        help_text="Normalized vertical coordinate (0.0000 to 1.0000)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['pin_number']
        unique_together = ('blueprint', 'pin_number')
        verbose_name = 'Blueprint Inspection Pin'
        verbose_name_plural = 'Blueprint Inspection Pins'

    def __str__(self):
        return f"Pin {self.pin_number}: {self.label} ({self.coordinate_x:.2%}, {self.coordinate_y:.2%})"

    @property
    def percentage_x(self) -> float:
        return float(self.coordinate_x) * 100

    @property
    def percentage_y(self) -> float:
        return float(self.coordinate_y) * 100


class FloorInspectionStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Awaiting Supervisor Review'
    APPROVED = 'APPROVED', 'Approved (Cleared to Next Operation)'
    CONCESSION_APPROVED = 'CONCESSION_APPROVED', 'Approved Under Concession'
    REJECTED_QUARANTINED = 'REJECTED_QUARANTINED', 'Rejected & Quarantined'


class FloorInspection(models.Model):
    """
    Electronic floor inspection record captured by QA Floor Inspector.
    Conforms to BRD Section 5.1, 5.4, & 6.1.
    """
    inspection_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g. INSP-2026-001"
    )
    traveler_operation = models.ForeignKey(
        'production.TravelerOperation',
        on_delete=models.PROTECT,
        related_name='inspections'
    )
    template_revision = models.ForeignKey(
        InspectionTemplateRevision,
        on_delete=models.PROTECT,
        related_name='floor_inspections'
    )
    workstation = models.ForeignKey(
        'master_data.Workstation',
        on_delete=models.PROTECT,
        related_name='floor_inspections'
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='conducted_inspections'
    )
    station_qr_scanned = models.CharField(max_length=100)
    traveler_barcode_scanned = models.CharField(max_length=100)
    is_demo_scan = models.BooleanField(default=False)

    status = models.CharField(
        max_length=30,
        choices=FloorInspectionStatus.choices,
        default=FloorInspectionStatus.PENDING_REVIEW
    )
    overall_in_tolerance = models.BooleanField(default=True)
    has_ctq_defect = models.BooleanField(default=False)
    inspector_notes = models.TextField(blank=True)

    # Supervisor Review Fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_inspections'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    supervisor_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Floor Inspection'
        verbose_name_plural = 'Floor Inspections'

    def __str__(self):
        return f"{self.inspection_number} - {self.traveler_operation.operation_name} ({self.get_status_display()})"

    def recalculate_tolerance_and_ctq(self) -> None:
        """
        Recalculates tolerance adherence and CTQ failure flags directly from persisted measurements.
        Never relies on unverified client payloads.
        """
        all_passed = True
        ctq_failed = False
        for m in self.measurements.select_related('parameter').all():
            is_in_tol, _ = m.parameter.evaluate_reading(m.measured_value, m.visual_passed)
            if not is_in_tol:
                all_passed = False
                if m.parameter.is_ctq:
                    ctq_failed = True

        self.overall_in_tolerance = all_passed
        self.has_ctq_defect = ctq_failed
        self.save(update_fields=['overall_in_tolerance', 'has_ctq_defect'])

    def validate_for_concession(self) -> None:
        """
        Strict server-side Zero-Concession Rule enforcement (BRD Section 4.3 & 6.1).
        Recalculates CTQ failures directly from database measurements.
        Rejects concession if ANY CTQ dimension failed tolerance.
        """
        failed_ctq = []
        for m in self.measurements.select_related('parameter').all():
            is_in_tol, _ = m.parameter.evaluate_reading(m.measured_value, m.visual_passed)
            if not is_in_tol and m.parameter.is_ctq:
                failed_ctq.append(f"{m.parameter.parameter_name} (reading: {m.measured_value} {m.parameter.unit})")

        if failed_ctq:
            raise ValidationError(
                f"Zero-Concession Violation: Critical-to-Quality (CTQ) parameter(s) [{', '.join(failed_ctq)}] failed tolerance. "
                f"Under BRD Section 4.3, zero concessions are permitted on CTQ dimensions. "
                f"This production batch cannot be conceded and must be rejected."
            )

    @transaction.atomic
    def approve(self, user, notes="", request=None):
        """
        Supervisor formal approval clearing the lot to downstream operations.
        """
        if not (user.can_review_inspections or user.is_superuser):
            raise ValidationError("Access Denied: You do not have permission to approve floor inspections.")

        if self.status != FloorInspectionStatus.PENDING_REVIEW:
            raise ValidationError(f"Invalid State: Inspection is already finalized as '{self.get_status_display()}'.")

        self.status = FloorInspectionStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.supervisor_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'supervisor_notes'])

        # Mark traveler operation completed
        self.traveler_operation.complete_operation(
            user=user,
            remarks=f"Passed floor inspection {self.inspection_number}. {notes}".strip()
        )

        from apps.audit_trail.models import AuditLog
        AuditLog.log(
            action=AuditLog.ActionType.INSPECTION_APPROVED,
            user=user,
            request=request,
            model_name='FloorInspection',
            object_id=str(self.id),
            object_repr=self.inspection_number,
            details=f"Inspection {self.inspection_number} approved by {user.employee_id} on {self.traveler_operation.operation_name}."
        )

    @transaction.atomic
    def grant_concession(self, user, reason_code, justification, request=None):
        """
        Quality Manager concession workflow with strict CTQ zero-concession enforcement.
        """
        if not (user.can_issue_concessions or user.is_superuser):
            raise ValidationError("Access Denied: Only Quality Managers or authorized supervisors can grant concessions.")

        if self.status != FloorInspectionStatus.PENDING_REVIEW:
            raise ValidationError(f"Invalid State: Inspection is already finalized as '{self.get_status_display()}'.")

        # Recalculate CTQ failures directly from database
        self.validate_for_concession()

        concession_num = f"CONC-{timezone.now().year}-{ConcessionRecord.objects.count() + 1:04d}"
        ConcessionRecord.objects.create(
            inspection=self,
            concession_number=concession_num,
            reason_code=reason_code,
            engineering_justification=justification,
            granted_by=user,
        )

        self.status = FloorInspectionStatus.CONCESSION_APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.supervisor_notes = f"Approved under Concession {concession_num}: {justification}"
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'supervisor_notes'])

        # Sign off the operation
        self.traveler_operation.complete_operation(
            user=user,
            remarks=f"Completed under approved concession {concession_num}."
        )

        from apps.audit_trail.models import AuditLog
        AuditLog.log(
            action=AuditLog.ActionType.CONCESSION_ISSUED,
            user=user,
            request=request,
            model_name='FloorInspection',
            object_id=str(self.id),
            object_repr=self.inspection_number,
            new_value={'concession_number': concession_num, 'reason_code': reason_code},
            details=f"Concession {concession_num} issued for {self.inspection_number} on {self.traveler_operation.operation_name}. Justification: {justification}"
        )

    @transaction.atomic
    def reject_and_quarantine(self, user, reason="", request=None):
        """
        Rejects non-conforming batch and tags Job Traveler as QUARANTINED.
        """
        if not (user.can_review_inspections or user.is_superuser):
            raise ValidationError("Access Denied: You do not have permission to review floor inspections.")

        if self.status != FloorInspectionStatus.PENDING_REVIEW:
            raise ValidationError(f"Invalid State: Inspection is already finalized as '{self.get_status_display()}'.")

        self.status = FloorInspectionStatus.REJECTED_QUARANTINED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.supervisor_notes = f"REJECTED & QUARANTINED: {reason}"
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'supervisor_notes'])

        # Quarantine the Job Traveler batch for this work order
        traveler = self.traveler_operation.traveler
        from apps.production.models import JobTravelerStatus
        traveler.status = JobTravelerStatus.QUARANTINED
        traveler.save(update_fields=['status'])

        from apps.audit_trail.models import AuditLog
        AuditLog.log(
            action=AuditLog.ActionType.INSPECTION_REJECTED,
            user=user,
            request=request,
            model_name='FloorInspection',
            object_id=str(self.id),
            object_repr=self.inspection_number,
            details=f"Inspection {self.inspection_number} REJECTED. Job Traveler {traveler.traveler_barcode} tagged as QUARANTINED. Reason: {reason}"
        )
        AuditLog.log(
            action=AuditLog.ActionType.QUARANTINE_MOVED,
            user=user,
            request=request,
            model_name='JobTraveler',
            object_id=str(traveler.id),
            object_repr=traveler.traveler_barcode,
            details=f"Job Traveler {traveler.traveler_barcode} placed in Digital Rejection Holding Area due to failed inspection {self.inspection_number} on {self.traveler_operation.operation_name}."
        )


class InspectionMeasurement(models.Model):
    """
    Individual parameter measurement captured on shopfloor tablet.
    Conforms to BRD Section 4.2 & 5.4.
    """
    inspection = models.ForeignKey(
        FloorInspection,
        on_delete=models.CASCADE,
        related_name='measurements'
    )
    parameter = models.ForeignKey(
        InspectionParameter,
        on_delete=models.PROTECT,
        related_name='measurements'
    )
    measuring_tool = models.ForeignKey(
        'master_data.InspectionTool',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='measurements'
    )
    measured_value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True
    )
    visual_passed = models.BooleanField(null=True, blank=True)
    is_in_tolerance = models.BooleanField(default=True)
    tolerance_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['parameter__sequence_order']
        unique_together = ('inspection', 'parameter')
        verbose_name = 'Inspection Measurement Reading'
        verbose_name_plural = 'Inspection Measurement Readings'

    def __str__(self):
        val_str = f"{self.measured_value}" if self.measured_value is not None else ("PASS" if self.visual_passed else "FAIL")
        status_str = "OK" if self.is_in_tolerance else "OUT OF SPEC"
        return f"{self.inspection.inspection_number} - {self.parameter.parameter_name}: {val_str} ({status_str})"

    def clean(self):
        # Enforce Tool Calibration Validity on the server
        if self.measuring_tool:
            self.measuring_tool.validate_for_measurement()

    def save(self, *args, **kwargs):
        # Server-side calculation of tolerance
        if self.parameter:
            passed, msg = self.parameter.evaluate_reading(self.measured_value, self.visual_passed)
            self.is_in_tolerance = passed
            self.tolerance_message = msg
        super().save(*args, **kwargs)


def validate_defect_photo_file(file):
    import os
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f"Invalid file format: '{ext}'. Only image files ({', '.join(valid_extensions)}) are permitted for defect photos.")
    max_size = 5 * 1024 * 1024  # 5MB
    if file.size > max_size:
        raise ValidationError(f"File size exceeds 5MB limit ({file.size / (1024*1024):.2f}MB).")


class InspectionDefectPhoto(models.Model):
    """
    Mandatory photographic proof of non-conformance.
    Conforms to BRD Section 5.4.
    """
    inspection = models.ForeignKey(
        FloorInspection,
        on_delete=models.CASCADE,
        related_name='defect_photos'
    )
    parameter = models.ForeignKey(
        InspectionParameter,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='defect_photos'
    )
    photo_file = models.FileField(
        upload_to='inspection_defects/',
        validators=[validate_defect_photo_file],
        help_text="Mandatory photographic evidence of out-of-spec dimension or defect"
    )
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Inspection Defect Photo'
        verbose_name_plural = 'Inspection Defect Photos'

    def __str__(self):
        param_str = f" ({self.parameter.parameter_name})" if self.parameter else ""
        return f"{self.inspection.inspection_number} Defect Photo{param_str}"


class ConcessionReason(models.TextChoices):
    NON_CRITICAL_OVERSIZE = 'NON_CRITICAL_OVERSIZE', 'Minor Oversize (Fits with clearance / Non-critical)'
    SURFACE_BLEMISH = 'SURFACE_BLEMISH', 'Minor Cosmetic Surface Blemish'
    ENGINEERING_DEVIATION = 'ENGINEERING_DEVIATION', 'Approved Customer / Engineering Design Deviation'
    FIT_FUNCTION_ACCEPTABLE = 'FIT_FUNCTION_ACCEPTABLE', 'Fit and Function Evaluated as Acceptable'
    OTHER = 'OTHER', 'Other Engineering Concession'


class ConcessionRecord(models.Model):
    """
    Formal engineering waiver record for minor non-CTQ deviations.
    Conforms to BRD Section 6.1.
    """
    inspection = models.OneToOneField(
        FloorInspection,
        on_delete=models.CASCADE,
        related_name='concession_record'
    )
    concession_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g. CONC-2026-001"
    )
    reason_code = models.CharField(
        max_length=50,
        choices=ConcessionReason.choices,
        default=ConcessionReason.ENGINEERING_DEVIATION
    )
    engineering_justification = models.TextField(
        help_text="Detailed engineering justification for why the batch is safe and functional for customer application."
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='granted_concessions'
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-granted_at']
        verbose_name = 'Concession Record'
        verbose_name_plural = 'Concession Records'

    def __str__(self):
        return f"{self.concession_number} ({self.get_reason_code_display()}) - {self.inspection.inspection_number}"


class CertificateStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active / Valid'
    SUPERSEDED = 'SUPERSEDED', 'Superseded by Reissue'
    REVOKED = 'REVOKED', 'Revoked'


def generate_verification_token():
    return secrets.token_urlsafe(24)


class CertificateOfConformance(models.Model):
    """
    Certificate of Conformance (CoC) confirming finished component lot compliance.
    Conforms to BRD Section 11.1 & 11.2 (Shipping Interlock & Certificate Generation).
    """
    certificate_number = models.CharField(
        max_length=60,
        unique=True,
        help_text="Unique certificate identifier, e.g. COC-2026-0001"
    )
    traveler = models.ForeignKey(
        'production.JobTraveler',
        on_delete=models.PROTECT,
        related_name='certificates',
        help_text="Job traveler associated with this certificate"
    )
    work_order = models.ForeignKey(
        'production.WorkOrder',
        on_delete=models.PROTECT,
        related_name='certificates',
        help_text="Manufacturing work order linked to this batch"
    )
    status = models.CharField(
        max_length=20,
        choices=CertificateStatus.choices,
        default=CertificateStatus.ACTIVE
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Revision sequence (e.g. 1 for initial issue, 2 for re-issue)"
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='issued_certificates',
        help_text="Authorized Quality Manager or Engineer who approved generation"
    )
    issued_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp of formal certificate issuance"
    )
    verification_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_verification_token,
        help_text="Cryptographically secure URL token for customer verification"
    )
    pdf_sha256_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="Hex digest of generated PDF file for tamper verification"
    )
    pdf_file = models.FileField(
        upload_to='certificates_of_conformance/',
        null=True,
        blank=True,
        help_text="Archived immutable binary PDF certificate"
    )
    reissue_reason = models.TextField(
        blank=True,
        help_text="Engineering justification for reissuance if superseded"
    )
    superseded_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_versions',
        help_text="Link to superseding certificate if reissued"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']
        verbose_name = 'Certificate of Conformance'
        verbose_name_plural = 'Certificates of Conformance'

    def __str__(self):
        return f"{self.certificate_number} (v{self.version}) - {self.traveler.traveler_barcode} [{self.get_status_display()}]"

    @classmethod
    def validate_eligibility(cls, traveler) -> tuple[bool, list[str]]:
        """
        Rigorous server-side verification of CoC eligibility per BRD Sections 10 & 11.
        Returns: (is_eligible: bool, failure_reasons: list[str])
        """
        from apps.production.models import JobTravelerStatus, OperationStatus
        from apps.quality.models import FloorInspectionStatus

        reasons = []

        # 1. Traveler Quarantine Interlock
        if traveler.status == JobTravelerStatus.QUARANTINED:
            reasons.append(f"Quarantine Hold: Job Traveler '{traveler.traveler_barcode}' is currently quarantined.")

        # 2. Sequential Routing Completion
        incomplete_ops = traveler.operations.exclude(status=OperationStatus.COMPLETED)
        if incomplete_ops.exists():
            op_names = ", ".join(f"Op {op.operation_sequence} ({op.operation_name})" for op in incomplete_ops)
            reasons.append(f"Incomplete Operations: Traveler has incomplete operations: [{op_names}].")

        # 3. Active Process Holds
        for op in traveler.operations.all():
            hold_active, rem_min = op.is_hold_active()
            if hold_active:
                reasons.append(f"Active Process Hold: Op {op.operation_sequence} has {rem_min} min remaining.")

        # 4. Final PDI Inspection Cleared
        pdi_op = traveler.get_pdi_operation()
        if not pdi_op:
            reasons.append("Missing PDI Operation: No Pre-Dispatch Inspection (PDI) operation is configured on traveler.")
        else:
            pdi_insp = traveler.get_pdi_inspection()
            if not pdi_insp:
                reasons.append("Missing PDI Inspection: Final PDI checklist has not been performed on shopfloor.")
            elif pdi_insp.status == FloorInspectionStatus.PENDING_REVIEW:
                reasons.append(f"PDI Pending Review: Final PDI '{pdi_insp.inspection_number}' is awaiting Quality Manager approval.")
            elif pdi_insp.status == FloorInspectionStatus.REJECTED_QUARANTINED:
                reasons.append(f"PDI Rejected: Final PDI '{pdi_insp.inspection_number}' was REJECTED by Quality.")
            elif pdi_insp.status not in [FloorInspectionStatus.APPROVED, FloorInspectionStatus.CONCESSION_APPROVED]:
                reasons.append(f"PDI Not Cleared: Final PDI status is '{pdi_insp.get_status_display()}'.")
            else:
                # 5. CTQ Zero-Concession Recalculation Check
                # Recalculate CTQ directly from persisted measurements
                ctq_failures = pdi_insp.measurements.filter(parameter__is_ctq=True, is_in_tolerance=False)
                if ctq_failures.exists():
                    bad_ctqs = ", ".join(m.parameter.parameter_name for m in ctq_failures)
                    reasons.append(f"CTQ Failure: Critical-to-Quality parameters failed tolerance [{bad_ctqs}]. Zero concessions allowed.")

        # 6. Raw Material Traceability & MTC Verification
        wo = traveler.work_order
        if not wo.raw_material_lot:
            reasons.append("Missing Raw Material Lot: Work order has no linked raw material intake lot.")
        else:
            lot = wo.raw_material_lot
            if not lot.heat_number or not lot.heat_number.strip():
                reasons.append("Missing Heat Number: Raw material lot has no mill heat number recorded.")
            if not lot.mtc_verified:
                reasons.append(f"Unverified MTC: Mill Test Certificate for lot '{lot.lot_number}' has not been verified by Quality.")

        return (len(reasons) == 0, reasons)

    def clean(self):
        super().clean()
        if self.traveler:
            eligible, reasons = CertificateOfConformance.validate_eligibility(self.traveler)
            if not eligible:
                raise ValidationError(f"CoC Eligibility Error: {'; '.join(reasons)}")

            # Prevent duplicate active certificates for the same traveler
            existing_active = CertificateOfConformance.objects.filter(
                traveler=self.traveler,
                status=CertificateStatus.ACTIVE
            ).exclude(pk=self.pk)
            if existing_active.exists() and self.status == CertificateStatus.ACTIVE:
                raise ValidationError(
                    f"Active Certificate Already Exists: Certificate {existing_active.first().certificate_number} "
                    f"is currently active for traveler '{self.traveler.traveler_barcode}'. Use reissue workflow to supersede."
                )


class MRBDispositionType(models.TextChoices):
    REWORK = 'REWORK', 'Rework Order Generation'
    SCRAP = 'SCRAP', 'Scrap Disposition & Write-Off'
    RTV = 'RTV', 'Return to Vendor (RTV Debit Note)'
    CUSTOMER_CONCESSION = 'CUSTOMER_CONCESSION', 'Customer Special Concession'


class MRBDisposition(models.Model):
    """
    Material Review Board (MRB) formal disposition record for quarantined lots.
    Conforms to BRD Section 6.3.
    Reviewed by Plant Manager, Quality Head, Production Lead.
    """
    disposition_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g. MRB-2026-0001"
    )
    traveler = models.ForeignKey(
        'production.JobTraveler',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mrb_dispositions'
    )
    raw_material_lot = models.ForeignKey(
        'inventory.RawMaterialIntake',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mrb_dispositions'
    )
    disposition_type = models.CharField(
        max_length=30,
        choices=MRBDispositionType.choices
    )
    defect_description = models.TextField(
        help_text="Detailed failure mode, non-conformance observation, or dimensional discrepancy."
    )
    engineering_justification = models.TextField(
        help_text="Technical justification for the selected disposition decision."
    )
    # Rework specific
    rework_instructions = models.TextField(
        blank=True,
        help_text="Detailed machining/polishing/reprocessing steps for rework traveler."
    )
    rework_traveler = models.ForeignKey(
        'production.JobTraveler',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_mrb_dispositions'
    )
    # Scrap specific
    scrap_cost_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="General Ledger / Accounting scrap cost code, e.g. SCRAP-DEF-402"
    )
    scrap_verified_at_bin = models.BooleanField(
        default=False,
        help_text="Physical verification that the non-conforming lot was deposited in the scrap bin."
    )
    # RTV specific
    debit_note_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Accounting debit note reference issued to supplier"
    )
    # Customer Concession specific
    customer_approval_doc = models.FileField(
        upload_to='customer_concessions/',
        null=True,
        blank=True,
        help_text="Mandatory customer written concession letter / engineering deviation document"
    )
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='authorized_mrb_dispositions'
    )
    authorized_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-authorized_at']
        verbose_name = 'Material Review Board Disposition'
        verbose_name_plural = 'Material Review Board Dispositions'

    def __str__(self):
        target = self.traveler.traveler_barcode if self.traveler else (self.raw_material_lot.lot_number if self.raw_material_lot else "N/A")
        return f"{self.disposition_number} [{self.get_disposition_type_display()}] - {target}"
