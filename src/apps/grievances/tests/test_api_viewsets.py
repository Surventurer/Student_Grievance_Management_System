from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.students.models import StudentProfile, AdminProfile, Department
from apps.grievances.models import Category, Grievance

User = get_user_model()


class GrievanceViewSetApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept_cs = Department.objects.create(name="Computer Science")
        self.dept_ee = Department.objects.create(name="Electrical")

        self.student1 = User.objects.create_user(email="s1@univ.edu", password="Pw!", role="student")
        self.prof1 = StudentProfile.objects.create(
            user=self.student1, name="S1", student_id="STU1", school="ENG", department="Computer Science"
        )

        self.student2 = User.objects.create_user(email="s2@univ.edu", password="Pw!", role="student")
        self.prof2 = StudentProfile.objects.create(
            user=self.student2, name="S2", student_id="STU2", school="ENG", department="Electrical"
        )

        self.category = Category.objects.create(name="Academic Evaluation", category_type="academic", sla_hours=24)

        self.officer_user = User.objects.create_user(email="officer@univ.edu", password="Pw!", role="officer")
        self.officer_prof = AdminProfile.objects.create(
            user=self.officer_user, role_level="officer", department="Computer Science", employee_id="OFF01"
        )

        self.admin_user = User.objects.create_user(email="admin_cs@univ.edu", password="Pw!", role="admin")
        self.admin_prof = AdminProfile.objects.create(
            user=self.admin_user, role_level="admin", department="Computer Science", employee_id="ADM01"
        )
        self.dept_cs.head_of_department = self.admin_user
        self.dept_cs.save()

        self.superadmin_user = User.objects.create_user(email="super@univ.edu", password="Pw!", role="superadmin")
        self.super_prof = AdminProfile.objects.create(
            user=self.superadmin_user, role_level="superadmin", department="Central", employee_id="SUP01"
        )

        # Grievance 1: Student 1, CS dept, assigned to officer
        self.g1 = Grievance.objects.create(
            student=self.prof1, title="Grievance 1", description="CS Issue",
            category=self.category, department="Computer Science", assigned_to=self.officer_prof
        )

        # Grievance 2: Student 2, EE dept, unassigned
        self.g2 = Grievance.objects.create(
            student=self.prof2, title="Grievance 2", description="EE Issue",
            category=self.category, department="Electrical"
        )

    def test_student_sees_only_own_grievances(self):
        self.client.force_login(self.student1)
        response = self.client.get('/api/grievances/api/v1/grievances/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [item['id'] for item in results]
        self.assertIn(str(self.g1.id), ids)
        self.assertNotIn(str(self.g2.id), ids)

    def test_officer_sees_only_assigned_grievances(self):
        self.client.force_login(self.officer_user)
        response = self.client.get('/api/grievances/api/v1/grievances/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [item['id'] for item in results]
        self.assertIn(str(self.g1.id), ids)
        self.assertNotIn(str(self.g2.id), ids)

    def test_admin_sees_department_grievances(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/api/grievances/api/v1/grievances/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [item['id'] for item in results]
        self.assertIn(str(self.g1.id), ids)
        self.assertNotIn(str(self.g2.id), ids)

    def test_superadmin_sees_all_grievances(self):
        self.client.force_login(self.superadmin_user)
        response = self.client.get('/api/grievances/api/v1/grievances/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [item['id'] for item in results]
        self.assertIn(str(self.g1.id), ids)
        self.assertIn(str(self.g2.id), ids)

    def test_only_students_can_create_via_viewset(self):
        self.client.force_login(self.admin_user)
        response = self.client.post('/api/grievances/api/v1/grievances/', {
            'title': 'Admin Grievance',
            'description': 'Trying to post as admin'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_categories_endpoint(self):
        self.client.force_login(self.student1)
        response = self.client.get('/api/grievances/api/v1/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        self.assertGreaterEqual(len(results), 1)
        names = [c['name'] for c in results]
        self.assertIn(self.category.name, names)
