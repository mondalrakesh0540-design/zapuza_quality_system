from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class MaterialGrade(models.Model):
    """
    Master specification for raw material grades.
    Defines chemical spectro tolerances and mechanical property requirements.
    """
    code = models.CharField(max_length=30, unique=True, help_text="e.g. AISI-4140, EN-8D, SS-316L")
    name = models.CharField(max_length=100, help_text="e.g. High-Tensile Alloy Steel 4140")
    
    # Chemical Composition Limits (%)
    carbon_min = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.380'))
    carbon_max = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.430'))
    manganese_min = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.750'))
    manganese_max = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('1.000'))
    silicon_min = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.150'))
    silicon_max = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.350'))
    phosphorus_max = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.035'))
    sulfur_max = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.040'))

    # Mechanical Properties Limits
    yield_strength_min = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('415.00'), help_text="Min Yield Strength (MPa)")
    tensile_strength_min = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('655.00'), help_text="Min Tensile Strength (MPa)")
    hardness_max = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('220.00'), help_text="Max Hardness (BHN / HBW)")

    requires_lab_testing = models.BooleanField(
        default=True,
        help_text="Whether this material grade requires mandatory internal lab testing before release."
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Material Grade Specification'
        verbose_name_plural = 'Material Grade Specifications'

    def __str__(self):
        return f"{self.code} - {self.name}"

    def evaluate_chemical(self, c=None, mn=None, si=None, p=None, s=None) -> tuple[bool, list[str]]:
        """
        Compares spectro chemical readings against grade limits.
        Returns: (is_passed: bool, failure_reasons: list[str])
        """
        failures = []
        if c is not None:
            c = Decimal(str(c))
            if c < self.carbon_min or c > self.carbon_max:
                failures.append(f"Carbon {c}% outside allowed range [{self.carbon_min}% - {self.carbon_max}%]")
        if mn is not None:
            mn = Decimal(str(mn))
            if mn < self.manganese_min or mn > self.manganese_max:
                failures.append(f"Manganese {mn}% outside allowed range [{self.manganese_min}% - {self.manganese_max}%]")
        if si is not None:
            si = Decimal(str(si))
            if si < self.silicon_min or si > self.silicon_max:
                failures.append(f"Silicon {si}% outside allowed range [{self.silicon_min}% - {self.silicon_max}%]")
        if p is not None:
            p = Decimal(str(p))
            if p > self.phosphorus_max:
                failures.append(f"Phosphorus {p}% exceeds maximum {self.phosphorus_max}%")
        if s is not None:
            s = Decimal(str(s))
            if s > self.sulfur_max:
                failures.append(f"Sulfur {s}% exceeds maximum {self.sulfur_max}%")

        return (len(failures) == 0, failures)

    def evaluate_mechanical(self, yield_val=None, tensile_val=None, hardness_val=None) -> tuple[bool, list[str]]:
        """
        Compares mechanical testing values against grade limits.
        Returns: (is_passed: bool, failure_reasons: list[str])
        """
        failures = []
        if yield_val is not None:
            yield_val = Decimal(str(yield_val))
            if yield_val < self.yield_strength_min:
                failures.append(f"Yield Strength {yield_val} MPa below minimum {self.yield_strength_min} MPa")
        if tensile_val is not None:
            tensile_val = Decimal(str(tensile_val))
            if tensile_val < self.tensile_strength_min:
                failures.append(f"Tensile Strength {tensile_val} MPa below minimum {self.tensile_strength_min} MPa")
        if hardness_val is not None:
            hardness_val = Decimal(str(hardness_val))
            if hardness_val > self.hardness_max:
                failures.append(f"Hardness {hardness_val} exceeds maximum allowed {self.hardness_max}")

        return (len(failures) == 0, failures)


class IntakeStatus(models.TextChoices):
    IN_STORE = 'IN_STORE', 'In Raw Store (Available)'
    QUARANTINED = 'QUARANTINED', 'Supplier Quarantine'
    EXHAUSTED = 'EXHAUSTED', 'Exhausted / Consumed'


class LabStatus(models.TextChoices):
    NOT_REQUIRED = 'NOT_REQUIRED', 'Not Required'
    IN_LAB_TESTING = 'IN_LAB_TESTING', 'In Lab Testing (Pending)'
    PASSED = 'PASSED', 'Lab Cleared (Passed)'
    FAILED = 'FAILED', 'Lab Rejected (Failed)'


class QuantityUnit(models.TextChoices):
    KG = 'KG', 'Kilograms (kg)'
    TONNES = 'TONNES', 'Metric Tonnes'
    BARS = 'BARS', 'Bars / Billets'
    PIECES = 'PIECES', 'Pieces / Forgings'


class RawMaterialIntake(models.Model):
    """
    Raw material intake and heat traceability tracking.
    Conforms to BRD Section 3.1 & 3.2.
    """
    lot_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique plant intake lot ID, e.g. LOT-2026-001"
    )
    heat_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Mill heat/cast number stamped on metal (e.g., H-8042)"
    )
    supplier_name = models.CharField(max_length=150, help_text="Steel mill or material supplier")
    purchase_order_no = models.CharField(max_length=50, help_text="Plant PO reference")
    material_grade = models.ForeignKey(
        MaterialGrade,
        on_delete=models.PROTECT,
        related_name='intake_lots'
    )
    quantity_received = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20, choices=QuantityUnit.choices, default=QuantityUnit.KG)
    
    # MTC Attachment and Verification
    mtc_file = models.FileField(
        upload_to='mtc_documents/',
        help_text="Uploaded Mill Test Certificate (PDF or scanned image)"
    )
    mtc_verified = models.BooleanField(
        default=False,
        help_text="Verified by Quality Lead against internal engineering specifications"
    )
    mtc_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_mtcs'
    )
    mtc_verified_at = models.DateTimeField(null=True, blank=True)

    # Laboratory Testing Status
    lab_status = models.CharField(
        max_length=30,
        choices=LabStatus.choices,
        default=LabStatus.NOT_REQUIRED
    )
    status = models.CharField(
        max_length=30,
        choices=IntakeStatus.choices,
        default=IntakeStatus.IN_STORE
    )
    barcode_identifier = models.CharField(
        max_length=100,
        unique=True,
        help_text="Barcode / QR tag attached to physical raw bundles"
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='received_intakes'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Raw Material Intake Lot'
        verbose_name_plural = 'Raw Material Intake Lots'

    def __str__(self):
        return f"{self.lot_number} (Heat #{self.heat_number}) - {self.material_grade.code}"

    def clean(self):
        # Generate barcode if missing
        if not self.barcode_identifier and self.lot_number:
            self.barcode_identifier = f"RAW-{self.lot_number}-{self.heat_number}"

    def can_issue_to_production(self) -> tuple[bool, str]:
        """
        Enforce Section 3.2 & 3.3 Server Interlock:
        Prevents issuing unverified, in-testing, or quarantined raw stock to production work orders.
        """
        if self.status == IntakeStatus.QUARANTINED:
            return False, (
                f"Quarantine Lockout: Material Lot '{self.lot_number}' (Heat #{self.heat_number}) "
                f"is tagged as SUPPLIER QUARANTINE. Cannot be issued to production work orders under any circumstances."
            )

        if not self.mtc_verified:
            return False, (
                f"MTC Verification Lockout: Material Lot '{self.lot_number}' Mill Test Certificate (MTC) "
                f"has not been verified and signed off by Quality."
            )

        if self.lab_status == LabStatus.IN_LAB_TESTING:
            return False, (
                f"Laboratory Hold: Material Lot '{self.lot_number}' is currently 'In Lab Testing'. "
                f"Stock release is blocked until chemical/mechanical spectro tests pass."
            )

        if self.lab_status == LabStatus.FAILED:
            return False, (
                f"Laboratory Rejection: Material Lot '{self.lot_number}' failed internal lab analysis."
            )

        if self.status == IntakeStatus.EXHAUSTED:
            return False, f"Material Lot '{self.lot_number}' stock is fully exhausted."

        return True, f"Lot '{self.lot_number}' is verified and cleared for work orders."

    def validate_for_work_order_issue(self):
        """Raises ValidationError if not cleared for production issuance."""
        can_issue, reason = self.can_issue_to_production()
        if not can_issue:
            raise ValidationError(reason)


class MaterialLabTest(models.Model):
    """
    Internal laboratory spectro-chemical analysis and mechanical testing results.
    Conforms to BRD Section 3.2.
    """
    intake = models.ForeignKey(
        RawMaterialIntake,
        on_delete=models.CASCADE,
        related_name='lab_tests'
    )
    tested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='conducted_lab_tests'
    )
    test_date = models.DateField(default=timezone.now)

    # Actual Chemical Composition (%)
    carbon_actual = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    manganese_actual = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    silicon_actual = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    phosphorus_actual = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    sulfur_actual = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)

    # Actual Mechanical Values
    yield_strength_actual = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Measured Yield (MPa)")
    tensile_strength_actual = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Measured Tensile (MPa)")
    hardness_actual = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Measured Hardness")

    is_passed = models.BooleanField(default=False)
    evaluation_summary = models.TextField(blank=True)
    lab_report_file = models.FileField(upload_to='lab_reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-test_date', '-created_at']
        verbose_name = 'Material Lab Test'
        verbose_name_plural = 'Material Lab Tests'

    def __str__(self):
        status_str = "PASSED" if self.is_passed else "FAILED"
        return f"Lab Test for {self.intake.lot_number} ({self.test_date}) - {status_str}"

    def evaluate_against_grade(self) -> tuple[bool, list[str]]:
        """Evaluates actuals against parent grade specifications."""
        grade = self.intake.material_grade
        chem_ok, chem_fails = grade.evaluate_chemical(
            c=self.carbon_actual,
            mn=self.manganese_actual,
            si=self.silicon_actual,
            p=self.phosphorus_actual,
            s=self.sulfur_actual
        )
        mech_ok, mech_fails = grade.evaluate_mechanical(
            yield_val=self.yield_strength_actual,
            tensile_val=self.tensile_strength_actual,
            hardness_val=self.hardness_actual
        )
        all_fails = chem_fails + mech_fails
        is_passed = chem_ok and mech_ok
        return is_passed, all_fails

    def save(self, *args, **kwargs):
        is_passed, failures = self.evaluate_against_grade()
        self.is_passed = is_passed
        if failures:
            self.evaluation_summary = "; ".join(failures)
        else:
            self.evaluation_summary = "All chemical spectro and mechanical properties conform to grade specification."
        super().save(*args, **kwargs)

        # Update intake lot's lab status automatically
        if self.is_passed:
            self.intake.lab_status = LabStatus.PASSED
        else:
            self.intake.lab_status = LabStatus.FAILED
        self.intake.save(update_fields=['lab_status'])


class SNCRReasonCategory(models.TextChoices):
    MTC_MISSING = 'MTC_MISSING', 'Mill Test Certificate (MTC) Missing or Unreadable'
    CHEMICAL_OUT_OF_SPEC = 'CHEMICAL_OUT_OF_SPEC', 'Spectro Chemical Analysis Out-of-Spec'
    MECHANICAL_FAILURE = 'MECHANICAL_FAILURE', 'Tensile / Hardness Mechanical Failure'
    PHYSICAL_SURFACE_DEFECT = 'PHYSICAL_SURFACE_DEFECT', 'Severe Surface Cracks, Seams or Voids'
    DIMENSIONAL_DISCREPANCY = 'DIMENSIONAL_DISCREPANCY', 'Raw Billet/Bar Dimensions Outside Tolerance'


class SNCRDisposition(models.TextChoices):
    SUPPLIER_QUARANTINE_HOLD = 'SUPPLIER_QUARANTINE_HOLD', 'Hold in Supplier Quarantine Bay'
    RETURN_TO_VENDOR = 'RETURN_TO_VENDOR', 'Return to Vendor (RTV) & Debit Note'
    SCRAP_DISPOSITION = 'SCRAP_DISPOSITION', 'Scrap Material at Supplier Cost'


class SupplierNCR(models.Model):
    """
    Supplier Non-Conformance Report (SNCR).
    Conforms to BRD Section 3.3.
    Immediately quarantines failing raw material lots.
    """
    sncr_number = models.CharField(max_length=50, unique=True, help_text="e.g. SNCR-2026-001")
    intake = models.ForeignKey(
        RawMaterialIntake,
        on_delete=models.CASCADE,
        related_name='ncrs'
    )
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='logged_sncrs'
    )
    reason_category = models.CharField(
        max_length=50,
        choices=SNCRReasonCategory.choices,
        default=SNCRReasonCategory.CHEMICAL_OUT_OF_SPEC
    )
    disposition = models.CharField(
        max_length=50,
        choices=SNCRDisposition.choices,
        default=SNCRDisposition.SUPPLIER_QUARANTINE_HOLD
    )
    defect_description = models.TextField(help_text="Detailed explanation of failure")
    corrective_action_requested = models.TextField(blank=True, help_text="Required vendor 8D or RCA report")
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_sncrs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Supplier Non-Conformance Report (SNCR)'
        verbose_name_plural = 'Supplier Non-Conformance Reports (SNCR)'

    def __str__(self):
        return f"{self.sncr_number} - {self.intake.lot_number} ({self.get_reason_category_display()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Automatically ensure the parent intake lot is quarantined!
        if self.intake.status != IntakeStatus.QUARANTINED:
            self.intake.status = IntakeStatus.QUARANTINED
            self.intake.save(update_fields=['status'])
