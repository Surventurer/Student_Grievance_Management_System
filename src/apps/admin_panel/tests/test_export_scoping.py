from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import csv
import io

from apps.students.models import StudentProfile, AdminProfile, Department, School
from apps.grievances.models import Category, Grievance

User = get_user_model()


class ExportScopingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="School of Applied Sciences")
        self.dept_cs = Department.objects.create(name="Computer Science", school=self.school)
        self.dept_ee = Department.objects.create(name="Electrical", school=self.school)

        # Superadmin
        self.superadmin = User.objects.create_user(email="super_export@univ.edu", password="Pw!", role="superadmin")
        self.super_prof = AdminProfile.objects.create(
            user=self.superadmin, role_level="superadmin", department="Central", employee_id="SA_EXP"
        )

        # Admin CS
        self.admin_cs = User.objects.create_user(email="admin_cs_export@univ.edu", password="Pw!", role="admin")
        self.admin_prof_cs = AdminProfile.objects.create(
            user=self.admin_cs, role_level="admin", department="Computer Science", employee_id="ADM_EXP_CS"
        )
        self.dept_cs.head_of_department = self.admin_cs
        self.dept_cs.save()

        # Student CS (Anonymous Grievance)
        self.student_cs = User.objects.create_user(email="anon_stu@univ.edu", password="Pw!", role="student")
        self.prof_cs = StudentProfile.objects.create(
            user=self.student_cs, name="Secret Person", student_id="ANON007",
            school=self.school.name, department=self.dept_cs.name
        )

        # Student EE (Normal Grievance)
        self.student_ee = User.objects.create_user(email="normal_stu@univ.edu", password="Pw!", role="student")
        self.prof_ee = StudentProfile.objects.create(
            user=self.student_ee, name="Normal Person", student_id="NORM001",
            school=self.school.name, department=self.dept_ee.name
        )

        self.category = Category.objects.create(name="Lab Amenities", category_type="academic", sla_hours=48)

        # Grievance CS - Anonymous
        self.g_cs_anon = Grievance.objects.create(
            student=self.prof_cs, title="CS Confidential", description="Secret issue",
            category=self.category, department="Computer Science", is_anonymous=True
        )

        # Grievance EE - Regular
        self.g_ee = Grievance.objects.create(
            student=self.prof_ee, title="EE Power", description="EE issue",
            category=self.category, department="Electrical", is_anonymous=False
        )

    def test_department_admin_csv_scoped_to_department(self):
        self.client.force_login(self.admin_cs)
        url = reverse('admin_panel:download_grievances_csv')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Header + CS Grievance = 2 rows
        self.assertEqual(len(rows), 2)
        # Check titles
        titles = [row[7] for row in rows[1:]]
        self.assertIn("CS Confidential", titles)
        self.assertNotIn("EE Power", titles)

    def test_anonymous_grievance_masking_in_csv(self):
        self.client.force_login(self.admin_cs)
        url = reverse('admin_panel:download_grievances_csv')
        response = self.client.get(url)

        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        data_row = rows[1]
        student_id_col = data_row[1]
        student_name_col = data_row[2]
        student_email_col = data_row[3]

        self.assertEqual(student_id_col, "Anonymous")
        self.assertEqual(student_name_col, "Anonymous Student")
        self.assertEqual(student_email_col, "Hidden")
        self.assertNotIn("Secret Person", content)
        self.assertNotIn("ANON007", content)

    def test_superadmin_csv_includes_all_departments(self):
        self.client.force_login(self.superadmin)
        url = reverse('admin_panel:download_grievances_csv')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Header + 2 Grievances = 3 rows
        self.assertEqual(len(rows), 3)
        titles = [row[7] for row in rows[1:]]
        self.assertIn("CS Confidential", titles)
        self.assertIn("EE Power", titles)

    def test_student_cannot_download_admin_csv(self):
        self.client.force_login(self.student_cs)
        url = reverse('admin_panel:download_grievances_csv')
        response = self.client.get(url)

        # Blocked: 302 redirect to auth
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/', response.url)
