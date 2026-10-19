from django.core.exceptions import PermissionDenied
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole
from apps.audit_trail.models import AuditLog


class AuditTrailTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.plant_mgr = User.objects.create_user(
            username='pm_audit',
            employee_id='EMP-PM-AUDIT',
            role=UserRole.PLANT_MANAGER,
            password='password123'
        )
        self.inspector = User.objects.create_user(
            username='insp_audit',
            employee_id='EMP-INSP-AUDIT',
            role=UserRole.QA_FLOOR_INSPECTOR,
            password='password123'
        )

    def test_audit_log_creation(self):
        """Verify AuditLog.log factory records user, timestamp, and metadata."""
        log = AuditLog.log(
            action=AuditLog.ActionType.PM_SIGN_OFF,
            user=self.plant_mgr,
            model_name='Workstation',
            object_id='4',
            object_repr='CNC-04',
            details='Daily PM signed off'
        )
        self.assertIsNotNone(log.pk)
        self.assertEqual(log.user, self.plant_mgr)
        self.assertEqual(log.action, AuditLog.ActionType.PM_SIGN_OFF)
        self.assertIn("EMP-PM-AUDIT", log.user_identifier)

    def test_audit_log_immutability_prevents_updates(self):
        """
        BRD Section 13.3:
        Audit log entries are immutable and cannot be altered by any user level.
        """
        log = AuditLog.log(
            action=AuditLog.ActionType.CREATE,
            user=self.plant_mgr,
            details='Initial log'
        )

        log.details = 'Tampered log content'
        with self.assertRaises(PermissionDenied):
            log.save()

    def test_audit_log_immutability_prevents_deletions(self):
        """
        BRD Section 13.3:
        Audit log entries cannot be deleted by any user level.
        """
        log = AuditLog.log(
            action=AuditLog.ActionType.CREATE,
            user=self.plant_mgr,
            details='Delete target log'
        )

        with self.assertRaises(PermissionDenied):
            log.delete()

    def test_audit_log_view_rbac(self):
        """
        Plant Manager & Quality Manager can view audit log; floor inspector is denied.
        """
        # Inspector denied
        self.client.force_login(self.inspector)
        resp_insp = self.client.get(reverse('audit_trail:audit_log_list'))
        self.assertRedirects(resp_insp, reverse('dashboard:index'))

        # Plant Manager allowed
        self.client.force_login(self.plant_mgr)
        resp_pm = self.client.get(reverse('audit_trail:audit_log_list'))
        self.assertEqual(resp_pm.status_code, 200)
        self.assertContains(resp_pm, "Immutable System Audit Trail")
