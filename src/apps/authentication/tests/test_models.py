from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.authentication.models import (
    User, EmailVerification, PasswordReset, AdminLoginOTP, TemporaryRegistration
)
from apps.students.models import School, Department, StudentProfile, AdminProfile


class UserModelTests(TestCase):
    """Unit tests for Custom User model and UserManager"""

    def test_create_student_user(self):
        user = User.objects.create_user(
            email='student@university.edu',
            password='Password123!',
            role='student'
        )
        self.assertEqual(user.email, 'student@university.edu')
        self.assertTrue(user.check_password('Password123!'))
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_officer)
        self.assertFalse(user.is_superadmin)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='superadmin@university.edu',
            password='AdminPassword123!'
        )
        self.assertEqual(admin.role, 'superadmin')
        self.assertTrue(admin.is_superadmin)
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_email_verified)

    def test_email_required_for_user(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='pwd')

    def test_soft_delete(self):
        user = User.objects.create_user(email='test_delete@university.edu', password='pwd')
        user.soft_delete(reason="Graduated")
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.deactivation_reason, "Graduated")

    def test_has_permission(self):
        student = User.objects.create_user(email='s@univ.edu', password='pwd', role='student')
        officer = User.objects.create_user(email='o@univ.edu', password='pwd', role='officer')
        admin = User.objects.create_user(email='a@univ.edu', password='pwd', role='admin')
        superadmin = User.objects.create_superuser(email='sa@univ.edu', password='pwd')

        # Student permissions
        self.assertTrue(student.has_permission('submit_grievances'))
        self.assertFalse(student.has_permission('manage_department_grievances'))

        # Officer permissions
        self.assertTrue(officer.has_permission('view_assigned_grievances'))
        self.assertFalse(officer.has_permission('manage_department_students'))

        # Admin permissions
        self.assertTrue(admin.has_permission('manage_department_grievances'))
        self.assertFalse(admin.has_permission('submit_grievances'))

        # Superadmin has all permissions
        self.assertTrue(superadmin.has_permission('anything_arbitrary'))


class OTPAndVerificationModelTests(TestCase):
    """Unit tests for verification and OTP models"""

    def setUp(self):
        self.user = User.objects.create_user(email='user_otp@univ.edu', password='pwd')

    def test_email_verification_expiry(self):
        active_ev = EmailVerification.objects.create(
            user=self.user,
            otp='123456',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        self.assertFalse(active_ev.is_expired)

        expired_ev = EmailVerification.objects.create(
            user=self.user,
            otp='654321',
            expires_at=timezone.now() - timedelta(minutes=5)
        )
        self.assertTrue(expired_ev.is_expired)

    def test_admin_login_otp_expiry(self):
        active_otp = AdminLoginOTP.objects.create(
            user=self.user,
            otp='999888',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        self.assertFalse(active_otp.is_expired)

        expired_otp = AdminLoginOTP.objects.create(
            user=self.user,
            otp='111222',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertTrue(expired_otp.is_expired)

    def test_temporary_registration_create_actual_user(self):
        school = School.objects.create(name="School of Engineering", code="SOE")
        dept = Department.objects.create(name="Computer Science", school=school)

        temp_reg = TemporaryRegistration.objects.create(
            name="John Doe",
            student_id="1234567890",
            email="johndoe@univ.edu",
            password="pbkdf2_sha256$hashedpassword",
            contact_no="9876543210",
            school=school.name,
            department=dept.name,
            otp="777888",
            expires_at=timezone.now() + timedelta(minutes=30)
        )
        self.assertFalse(temp_reg.is_expired)

        # Call create_actual_user
        created_user, profile = temp_reg.create_actual_user()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.email, "johndoe@univ.edu")
        self.assertTrue(created_user.is_email_verified)
        self.assertEqual(created_user.role, 'student')
        self.assertEqual(profile.student_id, "1234567890")
        self.assertEqual(profile.department, dept.name)
