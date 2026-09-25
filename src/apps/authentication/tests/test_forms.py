from django.test import TestCase
from apps.authentication.forms import StudentRegistrationForm
from apps.authentication.models import User, TemporaryRegistration
from apps.students.models import School, Department, StudentProfile
from apps.admin_panel.models import SystemSettings


class StudentRegistrationFormTests(TestCase):
    """Unit tests for StudentRegistrationForm validation and temporary registration"""

    def setUp(self):
        self.school = School.objects.create(name="School of Computing", code="SOC")
        self.dept = Department.objects.create(name="Information Technology", school=self.school)
        self.settings = SystemSettings.load()
        self.settings.allowed_email_domains = ""
        self.settings.password_min_length = 8
        self.settings.save()

    def test_valid_registration_form(self):
        data = {
            'name': 'Alice Smith',
            'student_id': '2026001001',
            'email': 'alice@university.edu',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        form = StudentRegistrationForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        temp_reg = form.save()
        self.assertIsInstance(temp_reg, TemporaryRegistration)
        self.assertEqual(temp_reg.email, 'alice@university.edu')
        self.assertEqual(temp_reg.student_id, '2026001001')
        self.assertFalse(temp_reg.is_verified)
        self.assertEqual(len(temp_reg.otp), 6)

    def test_invalid_student_id_format(self):
        # Must be 10 digits
        data = {
            'name': 'Bob Smith',
            'student_id': '12345',  # Only 5 digits
            'email': 'bob@university.edu',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        form = StudentRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('student_id', form.errors)

    def test_password_mismatch(self):
        data = {
            'name': 'Charlie Brown',
            'student_id': '2026001002',
            'email': 'charlie@university.edu',
            'password': 'Password123!',
            'confirm_password': 'DifferentPassword456!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        form = StudentRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_password_shorter_than_system_setting(self):
        self.settings.password_min_length = 10
        self.settings.save()

        data = {
            'name': 'David Miller',
            'student_id': '2026001003',
            'email': 'david@university.edu',
            'password': 'Short8!',
            'confirm_password': 'Short8!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        form = StudentRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_allowed_email_domains_whitelist(self):
        self.settings.allowed_email_domains = "university.edu, college.ac.in"
        self.settings.save()

        # Rejected domain
        data_bad = {
            'name': 'Eva Green',
            'student_id': '2026001004',
            'email': 'eva@gmail.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        form_bad = StudentRegistrationForm(data=data_bad)
        self.assertFalse(form_bad.is_valid())
        self.assertIn('email', form_bad.errors)

        # Accepted domain
        data_good = {
            'name': 'Eva Green',
            'student_id': '2026001004',
            'email': 'eva@university.edu',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        form_good = StudentRegistrationForm(data=data_good)
        self.assertTrue(form_good.is_valid(), form_good.errors)

    def test_duplicate_email_or_student_id_rejected(self):
        User.objects.create_user(email='existing@university.edu', password='pwd')
        data = {
            'name': 'Frank White',
            'student_id': '2026001005',
            'email': 'existing@university.edu',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'contact_no': '9876543210',
            'school': self.school.id,
            'department': self.dept.id,
        }
        form = StudentRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
