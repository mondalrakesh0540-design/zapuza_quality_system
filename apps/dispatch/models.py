import secrets
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.production.models import JobTraveler, JobTravelerStatus, OperationStatus
from apps.quality.models import CertificateOfConformance, CertificateStatus, FloorInspectionStatus


def generate_gate_token():
    return secrets.token_urlsafe(20)


class DispatchManifestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Clearance'
    CLEARED = 'CLEARED', 'Cleared for Dispatch'
    DISPATCHED = 'DISPATCHED', 'Dispatched / In-Transit'
    LOCKED = 'LOCKED', 'Locked by Shipping Interlock'


class DispatchManifest(models.Model):
    """
    Final Shipping Gate Pass & Dispatch Manifest.
    Conforms to BRD Section 10 & 11.
    Strictly locked until 100% operations complete, hold times elapsed, PDI approved, and CoC issued.
    """
    manifest_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g. MAN-2026-0001 or GP-2026-0001"
    )
    traveler = models.ForeignKey(
        JobTraveler,
        on_delete=models.PROTECT,
        related_name='dispatch_manifests'
    )
    work_order = models.ForeignKey(
        'production.WorkOrder',
        on_delete=models.PROTECT,
        related_name='dispatch_manifests'
    )
    certificate = models.ForeignKey(
        CertificateOfConformance,
        on_delete=models.PROTECT,
        related_name='dispatch_manifests'
    )
    customer_name = models.CharField(max_length=150, help_text="Customer / OEM company name")
    customer_po_number = models.CharField(max_length=60, help_text="Customer Purchase Order reference")
    shipping_destination = models.TextField(help_text="Delivery plant or warehouse address")
    dispatch_quantity = models.PositiveIntegerField(help_text="Verified physical units packed")
    transport_vehicle_number = models.CharField(max_length=50, help_text="e.g. MH-12-QZ-4012")
    driver_name = models.CharField(max_length=100)
    driver_contact = models.CharField(max_length=30, blank=True)
    driver_license = models.CharField(max_length=50, blank=True)
    container_seal_number = models.CharField(max_length=60, blank=True, help_text="Security container seal tag ID")
    status = models.CharField(
        max_length=30,
        choices=DispatchManifestStatus.choices,
        default=DispatchManifestStatus.CLEARED
    )
    cleared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cleared_dispatches'
    )
    cleared_at = models.DateTimeField(default=timezone.now)
    qr_verification_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_gate_token,
        help_text="Exterior crate QR token for customer digital inspection report verification"
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-cleared_at']
        verbose_name = 'Dispatch Manifest & Gate Pass'
        verbose_name_plural = 'Dispatch Manifests & Gate Passes'

    def __str__(self):
        return f"{self.manifest_number} - {self.customer_name} ({self.traveler.traveler_barcode})"

    @classmethod
    def validate_shipping_interlock(cls, traveler) -> tuple[bool, list[str]]:
        """
        Enforces Section 10.1 & 10.2 Shipping Interlock rules:
        a. 100% of all required machining and manufacturing operations completed.
        b. All process aging and hold times fulfilled without outstanding quality holds.
        c. Final PDI checklist signed and approved by Quality.
        d. Active Certificate of Conformance (CoC) issued.
        e. Traveler not quarantined.
        """
        reasons = []

        if traveler.status == JobTravelerStatus.QUARANTINED:
            reasons.append(f"Quarantine Lockout: Traveler '{traveler.traveler_barcode}' is under quality quarantine hold.")

        incomplete_ops = traveler.operations.exclude(status=OperationStatus.COMPLETED)
        if incomplete_ops.exists():
            op_names = ", ".join(f"Op {op.operation_sequence} ({op.operation_name})" for op in incomplete_ops)
            reasons.append(f"Incomplete Operations: Downstream operations are not finished: [{op_names}].")

        for op in traveler.operations.all():
            hold_active, rem_min = op.is_hold_active()
            if hold_active:
                reasons.append(f"Active Process Hold: Op {op.operation_sequence} has {rem_min} min remaining.")

        pdi_op = traveler.get_pdi_operation()
        if not pdi_op:
            reasons.append("Missing PDI Routing: No Final Pre-Dispatch Inspection operation is defined on traveler.")
        else:
            pdi_insp = traveler.get_pdi_inspection()
            if not pdi_insp:
                reasons.append("Missing PDI Inspection: Final PDI checklist has not been executed.")
            elif pdi_insp.status == FloorInspectionStatus.PENDING_REVIEW:
                reasons.append(f"PDI Pending Review: Final PDI '{pdi_insp.inspection_number}' is awaiting Quality Manager approval.")
            elif pdi_insp.status == FloorInspectionStatus.REJECTED_QUARANTINED:
                reasons.append(f"PDI Rejection: Final PDI '{pdi_insp.inspection_number}' was REJECTED by Quality.")
            elif pdi_insp.status not in [FloorInspectionStatus.APPROVED, FloorInspectionStatus.CONCESSION_APPROVED]:
                reasons.append(f"PDI Not Cleared: Final PDI status is '{pdi_insp.get_status_display()}'.")

        # Certificate of Conformance check
        active_coc = traveler.certificates.filter(status=CertificateStatus.ACTIVE).first()
        if not active_coc:
            reasons.append("Missing Certificate of Conformance: An Active CoC must be generated before dispatch clearance.")

        return (len(reasons) == 0, reasons)

    def clean(self):
        super().clean()
        if self.traveler:
            can_clear, reasons = DispatchManifest.validate_shipping_interlock(self.traveler)
            if not can_clear:
                raise ValidationError(f"Shipping Interlock Violation: {'; '.join(reasons)}")
