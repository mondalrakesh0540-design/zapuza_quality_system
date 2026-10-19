from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    PLANT_MANAGER = 'PLANT_MANAGER', 'Plant Manager'
    QUALITY_ENGINEER = 'QUALITY_ENGINEER', 'Quality Engineer'
    QUALITY_MANAGER = 'QUALITY_MANAGER', 'Quality Manager'
    SHIFT_SUPERVISOR = 'SHIFT_SUPERVISOR', 'Shift Supervisor'
    QA_FLOOR_INSPECTOR = 'QA_FLOOR_INSPECTOR', 'QA Floor Inspector'


class User(AbstractUser):
    """
    Custom User model for Factory Operations & Quality Control System.
    Strictly implements the five core shopfloor roles mandated by the BRD.
    """
    employee_id = models.CharField(
        max_length=30,
        unique=True,
        help_text="Unique plant employee badge or ID code (e.g., EMP-101)"
    )
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.QA_FLOOR_INSPECTOR,
        help_text="Primary shopfloor role governing system permissions"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact number for SMS/escalation alerts"
    )
    shift_preference = models.CharField(
        max_length=20,
        choices=[
            ('MORNING', 'Morning Shift (06:00 - 14:00)'),
            ('EVENING', 'Evening Shift (14:00 - 22:00)'),
            ('NIGHT', 'Night Shift (22:00 - 06:00)'),
            ('GENERAL', 'General / Management'),
        ],
        default='GENERAL'
    )
    is_shift_active = models.BooleanField(
        default=True,
        help_text="Whether this user is currently authorized to log floor actions"
    )

    class Meta:
        ordering = ['employee_id']
        verbose_name = 'Factory User'
        verbose_name_plural = 'Factory Users'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()} - {self.employee_id})"

    @property
    def is_plant_manager(self) -> bool:
        return self.role == UserRole.PLANT_MANAGER or self.is_superuser

    @property
    def is_quality_engineer(self) -> bool:
        return self.role == UserRole.QUALITY_ENGINEER or self.is_superuser

    @property
    def is_quality_manager(self) -> bool:
        return self.role == UserRole.QUALITY_MANAGER or self.is_superuser

    @property
    def is_shift_supervisor(self) -> bool:
        return self.role == UserRole.SHIFT_SUPERVISOR or self.is_superuser

    @property
    def is_qa_floor_inspector(self) -> bool:
        return self.role == UserRole.QA_FLOOR_INSPECTOR or self.is_superuser

    def has_role(self, *roles) -> bool:
        """Check if user belongs to any of the specified roles or is a superuser."""
        if self.is_superuser:
            return True
        return self.role in roles

    # Specific business permission helpers based on BRD matrix
    @property
    def can_manage_templates(self) -> bool:
        """Quality Engineers create blueprints/checklists; Quality Managers review."""
        return self.role in [UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER] or self.is_superuser

    @property
    def can_approve_templates(self) -> bool:
        """Only Quality Managers can formally approve new inspection templates before deployment."""
        return self.role == UserRole.QUALITY_MANAGER or self.is_superuser

    @property
    def can_perform_inspection(self) -> bool:
        """QA Floor Inspectors and Quality Engineers can execute floor inspections."""
        return self.role in [UserRole.QA_FLOOR_INSPECTOR, UserRole.QUALITY_ENGINEER] or self.is_superuser

    @property
    def can_review_inspections(self) -> bool:
        """Shift Supervisors and Quality Managers review pending inspection results."""
        return self.role in [UserRole.SHIFT_SUPERVISOR, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_issue_concessions(self) -> bool:
        """Only Quality Managers (or authorized supervisors) can issue concessions for non-CTQ items."""
        return self.role in [UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_sign_off_pm(self) -> bool:
        """Supervisors, maintenance authorized inspectors, and plant managers can sign off daily PM."""
        return self.role in [UserRole.SHIFT_SUPERVISOR, UserRole.QA_FLOOR_INSPECTOR, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_clear_shipping(self) -> bool:
        """Shift Supervisors, Quality Managers, and Plant Managers can issue dispatch clearance."""
        return self.role in [UserRole.SHIFT_SUPERVISOR, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_manage_work_orders(self) -> bool:
        """Shift Supervisors, Plant Managers, and Quality Managers can create work orders."""
        return self.role in [UserRole.SHIFT_SUPERVISOR, UserRole.PLANT_MANAGER, UserRole.QUALITY_MANAGER] or self.is_superuser

    @property
    def can_release_work_orders(self) -> bool:
        """Shift Supervisors and Plant Managers can release work orders to shopfloor."""
        return self.role in [UserRole.SHIFT_SUPERVISOR, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_execute_routing(self) -> bool:
        """Shift Supervisors, QA Floor Inspectors, and Plant Managers can start/sign-off operations."""
        return self.role in [UserRole.SHIFT_SUPERVISOR, UserRole.QA_FLOOR_INSPECTOR, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_issue_coc(self) -> bool:
        """Quality Managers, Quality Engineers, and Plant Managers can issue Certificates of Conformance."""
        return self.role in [UserRole.QUALITY_MANAGER, UserRole.QUALITY_ENGINEER, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_mrb_disposition(self) -> bool:
        """Quality Managers and Plant Managers authorize Material Review Board (MRB) dispositions."""
        return self.role in [UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER] or self.is_superuser

    @property
    def can_log_handover(self) -> bool:
        """Shift Supervisors, QA Floor Inspectors, and Plant Managers participate in shift handovers."""
        return self.role in [UserRole.SHIFT_SUPERVISOR, UserRole.QA_FLOOR_INSPECTOR, UserRole.PLANT_MANAGER, UserRole.QUALITY_MANAGER] or self.is_superuser
