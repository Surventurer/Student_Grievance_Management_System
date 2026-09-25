from django.test import TestCase, Client
from django.urls import reverse
from apps.authentication.models import User, TemporaryRegistration, AdminLoginOTP
from apps.students.models import School, Department, StudentProfile, AdminProfile
from apps.admin_panel.models import SystemSettings
from django.utils import timezone
from datetime import timedelta


class AuthViewsIntegrationTests(TestCase):
    """Integration tests for web authentication, registration, 2FA, and session management"""

    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="School of Engineering", code="ENG")
        self.dept = Department.objects.create(name="Computer Science", school=self.school)
        self.settings = SystemSettings.load()
        self.settings.save()

    def test_root_redirect_to_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_student_registration_and_otp_verification_lifecycle(self):
        # 1. Submit Registration Form
        reg_data = {
            'name': 'George Clark',
            'student_id': '2026112233',
            'email': 'george@university.edu',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        res = self.client.post(reverse('authentication:student_registration'), reg_data)
        # Verify redirect or success
        self.assertEqual(res.status_code, 302)

        temp_reg = TemporaryRegistration.objects.filter(email='george@university.edu').first()
        self.assertIsNotNone(temp_reg)
        self.assertFalse(temp_reg.is_verified)
        otp = temp_reg.otp

        # 2. Stage session and verify OTP
        session = self.client.session
        session['verification_student_id'] = temp_reg.student_id
        session['verification_email'] = temp_reg.email
        session['verification_type'] = 'temporary'
        session.save()

        verify_res = self.client.post(reverse('authentication:verify_student_email'), {
            'action': 'verify',
            'otp': otp
        })
        self.assertEqual(verify_res.status_code, 302)

        # 3. Verify User and StudentProfile now exist
        user = User.objects.filter(email='george@university.edu').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_email_verified)
        self.assertTrue(user.is_student)
        self.assertEqual(user.student_profile.student_id, '2026112233')

    def test_student_login_success_and_redirect(self):
        user = User.objects.create_user(
            email='student_login@univ.edu',
            password='Password123!',
            role='student',
            is_email_verified=True
        )
        StudentProfile.objects.create(
            user=user,
            student_id='2026998877',
            name='Student User',
            school=self.school.name,
            department=self.dept.name
        )

        res = self.client.post(reverse('authentication:login_view'), {
            'email': 'student_login@univ.edu',
            'password': 'Password123!'
        })
        self.assertEqual(res.status_code, 302)
        self.assertIn('/students/', res.url)

    def test_deactivated_student_login_rejected(self):
        user = User.objects.create_user(
            email='deactivated@univ.edu',
            password='Password123!',
            role='student',
            is_email_verified=True
        )
        user.soft_delete(reason="Suspended for disciplinary inquiry")

        res = self.client.post(reverse('authentication:login_view'), {
            'email': 'deactivated@univ.edu',
            'password': 'Password123!'
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Account Deactivated")

    def test_staff_2fa_login_flow(self):
        officer = User.objects.create_user(
            email='officer_2fa@univ.edu',
            password='StaffPassword123!',
            role='officer',
            is_email_verified=True
        )
        AdminProfile.objects.create(
            user=officer,
            employee_id='EMP-0099',
            role_level='officer',
            department=self.dept.name,
            name='Officer Jane'
        )

        # Step 1: Submit credentials (triggers OTP generation and prompt)
        res_step1 = self.client.post(reverse('authentication:login_view'), {
            'email': 'officer_2fa@univ.edu',
            'password': 'StaffPassword123!'
        })
        self.assertEqual(res_step1.status_code, 200)
        self.assertTrue(res_step1.context['show_otp_field'])

        # Check that OTP record was created in database
        otp_obj = AdminLoginOTP.objects.filter(user=officer, is_used=False).order_by('-created_at').first()
        self.assertIsNotNone(otp_obj)
        otp = otp_obj.otp

        # Step 2: Submit OTP to complete 2FA login
        res_step2 = self.client.post(reverse('authentication:login_view'), {
            'email': 'officer_2fa@univ.edu',
            'otp': otp
        })
        self.assertEqual(res_step2.status_code, 302)
        self.assertIn('/admin-panel/dashboard/', res_step2.url)

    def test_staff_logout_clears_session(self):
        user = User.objects.create_superuser(email='super_logout@univ.edu', password='pwd')
        self.client.force_login(user)

        res = self.client.get(reverse('authentication:logout_view'))
        self.assertEqual(res.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)
