from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.students.models import StudentProfile, AdminProfile

User = get_user_model()


class StudentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.student_user = User.objects.create_user(
            email="student_view@university.edu",
            password="Password123!",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            name="Bob Johnson",
            student_id="STU2002",
            school="School of Engineering",
            department="Electrical Engineering",
            contact_no="9876543210"
        )

        self.admin_user = User.objects.create_user(
            email="admin_view@university.edu",
            password="Password123!",
            role="admin"
        )
        self.admin_profile = AdminProfile.objects.create(
            user=self.admin_user,
            role_level="admin",
            department="Electrical Engineering",
            employee_id="EMP_VIEW_01"
        )

    def test_dashboard_unauthenticated_redirect(self):
        response = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_dashboard_admin_redirect(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_panel:dashboard'), response.url)

    def test_dashboard_student_access(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'students/dashboard.html')
        self.assertIn('total_grievances', response.context)
        self.assertEqual(response.context['total_grievances'], 0)

    def test_profile_view_student(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('students:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'students/profile.html')
        self.assertEqual(response.context['student_profile'], self.student_profile)

    def test_update_contact_view_valid(self):
        self.client.force_login(self.student_user)
        response = self.client.post(reverse('students:update_contact'), {
            'contact_no': '9123456789'
        })
        self.assertEqual(response.status_code, 302)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.contact_no, '9123456789')

    def test_update_contact_view_invalid_letters(self):
        self.client.force_login(self.student_user)
        response = self.client.post(reverse('students:update_contact'), {
            'contact_no': 'notanumber1'
        })
        self.assertEqual(response.status_code, 302)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.contact_no, '9876543210')

    def test_update_contact_view_invalid_length(self):
        self.client.force_login(self.student_user)
        response = self.client.post(reverse('students:update_contact'), {
            'contact_no': '123'
        })
        self.assertEqual(response.status_code, 302)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.contact_no, '9876543210')

    def test_dashboard_api(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('students:dashboard_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('statistics', data)
        self.assertEqual(data['statistics']['total_grievances'], 0)

    def test_profile_api_get(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('students:profile_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['student_id'], 'STU2002')
