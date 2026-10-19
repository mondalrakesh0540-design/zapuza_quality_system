from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole


class AccountsModelAndRBACTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.plant_mgr = User.objects.create_user(
            username='pm_test',
            employee_id='EMP-PM',
            role=UserRole.PLANT_MANAGER,
            password='password123'
        )
        self.quality_mgr = User.objects.create_user(
            username='qm_test',
            employee_id='EMP-QM',
            role=UserRole.QUALITY_MANAGER,
            password='password123'
        )
        self.quality_eng = User.objects.create_user(
            username='qe_test',
            employee_id='EMP-QE',
            role=UserRole.QUALITY_ENGINEER,
            password='password123'
        )
        self.supervisor = User.objects.create_user(
            username='sup_test',
            employee_id='EMP-SUP',
            role=UserRole.SHIFT_SUPERVISOR,
            password='password123'
        )
        self.inspector = User.objects.create_user(
            username='insp_test',
            employee_id='EMP-INSP',
            role=UserRole.QA_FLOOR_INSPECTOR,
            password='password123'
        )

    def test_five_roles_exist_and_attributes_correct(self):
        """Verify the five mandatory BRD roles are configured on the custom User model."""
        self.assertTrue(self.plant_mgr.is_plant_manager)
        self.assertTrue(self.quality_mgr.is_quality_manager)
        self.assertTrue(self.quality_eng.is_quality_engineer)
        self.assertTrue(self.supervisor.is_shift_supervisor)
        self.assertTrue(self.inspector.is_qa_floor_inspector)

    def test_role_based_permission_helpers(self):
        """Verify business permission helpers match the BRD authority matrix."""
        # Template management (QE & QM)
        self.assertTrue(self.quality_eng.can_manage_templates)
        self.assertTrue(self.quality_mgr.can_manage_templates)
        self.assertFalse(self.inspector.can_manage_templates)

        # Template formal approval (QM only)
        self.assertTrue(self.quality_mgr.can_approve_templates)
        self.assertFalse(self.quality_eng.can_approve_templates)

        # Inspection execution (Inspector & QE)
        self.assertTrue(self.inspector.can_perform_inspection)
        self.assertTrue(self.quality_eng.can_perform_inspection)
        self.assertFalse(self.supervisor.can_perform_inspection)

        # Concessions (QM & Plant Mgr only)
        self.assertTrue(self.quality_mgr.can_issue_concessions)
        self.assertTrue(self.plant_mgr.can_issue_concessions)
        self.assertFalse(self.supervisor.can_issue_concessions)
        self.assertFalse(self.inspector.can_issue_concessions)

        # Daily PM sign-off (Supervisor, Inspector, Plant Mgr)
        self.assertTrue(self.supervisor.can_sign_off_pm)
        self.assertTrue(self.inspector.can_sign_off_pm)
        self.assertFalse(self.quality_eng.can_sign_off_pm)

    def test_login_and_logout_flow(self):
        """Verify credential login and logout view behaviors."""
        login_resp = self.client.post(reverse('accounts:login'), {
            'username': 'pm_test',
            'password': 'password123'
        })
        self.assertRedirects(login_resp, reverse('dashboard:index'))

        # Logout
        logout_resp = self.client.get(reverse('accounts:logout'))
        self.assertRedirects(logout_resp, reverse('accounts:login'))

    def test_all_five_roles_can_login_and_access_dashboard(self):
        """Verify every one of the 5 roles can log in and access the dashboard."""
        users = [
            (self.plant_mgr, 'Plant Manager'),
            (self.quality_mgr, 'Quality Manager'),
            (self.quality_eng, 'Quality Engineer'),
            (self.supervisor, 'Shift Supervisor'),
            (self.inspector, 'QA Floor Inspector'),
        ]
        for user, role_name in users:
            self.client.force_login(user)
            resp = self.client.get(reverse('dashboard:index'))
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, role_name)
            self.assertContains(resp, user.employee_id)

            # Profile page check
            prof_resp = self.client.get(reverse('accounts:profile'))
            self.assertEqual(prof_resp.status_code, 200)
            self.assertContains(prof_resp, user.employee_id)

    def test_demo_quick_login_for_all_roles(self):
        """Verify demo role switcher logs in the appropriate role user for all 5 roles."""
        roles = [
            UserRole.PLANT_MANAGER,
            UserRole.QUALITY_MANAGER,
            UserRole.QUALITY_ENGINEER,
            UserRole.SHIFT_SUPERVISOR,
            UserRole.QA_FLOOR_INSPECTOR,
        ]
        for role in roles:
            resp = self.client.post(reverse('accounts:login'), {
                'demo_role': role
            })
            self.assertRedirects(resp, reverse('dashboard:index'))
            user = User.objects.get(pk=self.client.session['_auth_user_id'])
            self.assertEqual(user.role, role)

    def test_unauthenticated_user_redirected_to_login(self):
        """Protected views must redirect unauthenticated visitors to login."""
        protected_urls = [
            reverse('dashboard:index'),
            reverse('accounts:profile'),
            reverse('master_data:workstation_list'),
            reverse('master_data:tool_list'),
            reverse('audit_trail:audit_log_list'),
        ]
        for url in protected_urls:
            resp = self.client.get(url)
            self.assertRedirects(resp, f"{reverse('accounts:login')}?next={url}")
