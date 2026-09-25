from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.students.models import StudentProfile, AdminProfile, Department
from apps.grievances.models import Category, Grievance, GrievanceComment

User = get_user_model()


class GrievanceSecurityIDORTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept_cs = Department.objects.create(name="Computer Science")
        self.dept_ee = Department.objects.create(name="Electrical")

        # Student A
        self.student_a = User.objects.create_user(email="alice@univ.edu", password="Pw!", role="student")
        self.prof_a = StudentProfile.objects.create(
            user=self.student_a, name="Alice", student_id="STU_A", school="ENG", department="Computer Science"
        )

        # Student B
        self.student_b = User.objects.create_user(email="bob@univ.edu", password="Pw!", role="student")
        self.prof_b = StudentProfile.objects.create(
            user=self.student_b, name="Bob", student_id="STU_B", school="ENG", department="Electrical"
        )

        # Admin CS
        self.admin_cs = User.objects.create_user(email="admin_cs@univ.edu", password="Pw!", role="admin")
        self.admin_prof_cs = AdminProfile.objects.create(
            user=self.admin_cs, role_level="admin", department="Computer Science", employee_id="ADM_CS"
        )

        self.category = Category.objects.create(name="General", category_type="academic", sla_hours=48)

        # Bob's Grievance (Dept EE)
        self.grievance_b = Grievance.objects.create(
            student=self.prof_b,
            title="Bob's Confidential Grievance",
            description="Private issues with grading",
            category=self.category,
            department="Electrical"
        )

        # Public and internal comments on Bob's grievance
        self.public_comment = GrievanceComment.objects.create(
            grievance=self.grievance_b,
            user=self.student_b,
            message="Public update from Bob",
            is_internal=False
        )
        self.internal_note = GrievanceComment.objects.create(
            grievance=self.grievance_b,
            user=self.admin_cs,
            message="Internal confidential staff note",
            is_internal=True
        )

    def test_idor_student_cannot_access_other_student_grievance(self):
        self.client.force_login(self.student_a)
        response = self.client.get(f'/grievances/{self.grievance_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_idor_student_cannot_view_other_student_comments(self):
        self.client.force_login(self.student_a)
        response = self.client.get(f'/grievances/{self.grievance_b.id}/comments/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_idor_admin_cannot_access_other_department_grievance(self):
        # Admin CS cannot access Grievance in Electrical
        self.admin_cs.refresh_from_db()
        self.client.force_login(self.admin_cs)
        response = self.client.get(f'/api/grievances/{self.grievance_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_students_cannot_see_internal_comments(self):
        self.client.force_login(self.student_b)
        response = self.client.get(f'/api/grievances/{self.grievance_b.id}/comments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comments = response.json()
        messages = [c['message'] for c in comments]
        self.assertIn("Public update from Bob", messages)
        self.assertNotIn("Internal confidential staff note", messages)
