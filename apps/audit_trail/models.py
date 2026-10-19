from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models


class AuditLog(models.Model):
    """
    Immutable, tamper-proof system audit trail conforming to Section 13.3 of BRD.
    Records every critical event, previous and new values, user, timestamp, and IP.
    Deletes and updates are strictly prevented at model level.
    """
    class ActionType(models.TextChoices):
        LOGIN = 'LOGIN', 'User Login'
        LOGOUT = 'LOGOUT', 'User Logout'
        CREATE = 'CREATE', 'Record Created'
        UPDATE = 'UPDATE', 'Record Updated'
        PM_SIGN_OFF = 'PM_SIGN_OFF', 'Daily PM Checklist Signed Off'
        PM_LOCKOUT = 'PM_LOCKOUT', 'Workstation PM Lockout Triggered'
        CALIBRATION_LOCKOUT = 'CALIBRATION_LOCKOUT', 'Tool Calibration Lockout Triggered'
        TOOL_REGISTERED = 'TOOL_REGISTERED', 'Tool Registered/Updated'
        INSPECTION_ENTRY = 'INSPECTION_ENTRY', 'Inspection Measurement Entry'
        INSPECTION_APPROVED = 'INSPECTION_APPROVED', 'Floor Inspection Approved'
        INSPECTION_REJECTED = 'INSPECTION_REJECTED', 'Floor Inspection Rejected'
        CONCESSION_ISSUED = 'CONCESSION_ISSUED', 'Concession Issued'
        RAW_INTAKE = 'RAW_INTAKE', 'Raw Material Intake Created'
        MTC_VERIFIED = 'MTC_VERIFIED', 'Supplier MTC Verified'
        LAB_TEST = 'LAB_TEST', 'Material Lab Test Recorded'
        SNCR_LOGGED = 'SNCR_LOGGED', 'Supplier Non-Conformance Report Logged'
        TEMPLATE_CREATED = 'TEMPLATE_CREATED', 'Inspection Template Created'
        TEMPLATE_APPROVED = 'TEMPLATE_APPROVED', 'Inspection Template Approved'
        BLUEPRINT_PINNED = 'BLUEPRINT_PINNED', 'Blueprint Coordinate Pinned'
        WORK_ORDER_RELEASED = 'WORK_ORDER_RELEASED', 'Work Order Released'
        ROUTING_COMPLETED = 'ROUTING_COMPLETED', 'Routing Operation Completed'
        ROUTING_LOCKOUT = 'ROUTING_LOCKOUT', 'Routing Interlock Enforced'
        QUARANTINE_MOVED = 'QUARANTINE_MOVED', 'Lot Moved to Quarantine'
        SHIPPING_INTERLOCK = 'SHIPPING_INTERLOCK', 'Shipping Interlock Enforced'
        DISPATCH_CLEARED = 'DISPATCH_CLEARED', 'Dispatch Cleared'
        COC_GENERATED = 'COC_GENERATED', 'Certificate of Conformance Generated'
        COC_REISSUED = 'COC_REISSUED', 'Certificate of Conformance Reissued'
        MRB_DISPOSITION = 'MRB_DISPOSITION', 'Material Review Board Disposition'
        SHIFT_HANDOVER = 'SHIFT_HANDOVER', 'Shift Handover Logged'
        SHIFT_HANDOVER_ACK = 'SHIFT_HANDOVER_ACK', 'Shift Handover Acknowledged'
        SECURITY_ALERT = 'SECURITY_ALERT', 'Security Violation Attempt'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries'
    )
    user_identifier = models.CharField(
        max_length=100,
        help_text="Immutable capture of user employee ID / username at time of event"
    )
    user_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Role of the user at the time of the event"
    )
    action = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        db_index=True
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        db_index=True
    )
    object_id = models.CharField(
        max_length=100,
        blank=True
    )
    object_repr = models.CharField(
        max_length=255,
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    device_info = models.CharField(
        max_length=255,
        blank=True,
        help_text="User agent or device serial number"
    )
    previous_value = models.JSONField(
        default=dict,
        blank=True,
        help_text="State before modification"
    )
    new_value = models.JSONField(
        default=dict,
        blank=True,
        help_text="State after modification"
    )
    details = models.TextField(
        blank=True,
        help_text="Human-readable event summary or error reason"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.user_identifier} - {self.action} on {self.model_name or 'System'}"

    def save(self, *args, **kwargs):
        # Prevent updating existing audit log entry to ensure strict immutability
        if self.pk:
            raise PermissionDenied("Audit log entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion of audit log entries
        raise PermissionDenied("Audit log entries are tamper-proof and cannot be deleted.")

    @classmethod
    def log(cls, action, user=None, request=None, model_name="", object_id="", object_repr="", previous_value=None, new_value=None, details="", device_info=""):
        """
        Convenience factory method to create an audit record safely.
        """
        user_identifier = "Anonymous"
        user_role = "None"
        ip_address = None
        user_agent = device_info

        if request:
            if hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user
            # Extract real IP or remote addr
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            if not user_agent:
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:250]

        if user and user.is_authenticated:
            user_identifier = f"{getattr(user, 'employee_id', user.username)} ({user.username})"
            user_role = getattr(user, 'role', 'User')

        return cls.objects.create(
            user=user if (user and user.is_authenticated) else None,
            user_identifier=user_identifier,
            user_role=user_role,
            action=action,
            model_name=model_name,
            object_id=str(object_id),
            object_repr=str(object_repr)[:250],
            ip_address=ip_address,
            device_info=user_agent,
            previous_value=previous_value or {},
            new_value=new_value or {},
            details=details,
        )
