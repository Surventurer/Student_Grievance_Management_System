from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

from apps.students.models import StudentProfile, AdminProfile, Department, School
from apps.grievances.models import Category, Grievance, Appeal
from apps.admin_panel.models import SystemSettings

User = get_user_model()


class DashboardAndActionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="School of Science")
        self.dept_cs = Department.objects.create(name="Computer Science", school=self.school)
        self.dept_ee = Department.objects.create(name="Electrical", school=self.school)

        # Superadmin
        self.superadmin = User.objects.create_user(email="sa@univ.edu", password="Pw!", role="superadmin")
        self.super_prof = AdminProfile.objects.create(
            user=self.superadmin, role_level="superadmin", department="Central", employee_id="SA001"
        )

        # Admin CS
        self.admin_cs = User.objects.create_user(email="admin_cs@univ.edu", password="Pw!", role="admin")
        self.admin_prof_cs = AdminProfile.objects.create(
            user=self.admin_cs, role_level="admin", department="Computer Science", employee_id="ADM_CS_01"
        )
        self.dept_cs.head_of_department = self.admin_cs
        self.dept_cs.save()

        # Admin EE
        self.admin_ee = User.objects.create_user(email="admin_ee@univ.edu", password="Pw!", role="admin")
        self.admin_prof_ee = AdminProfile.objects.create(
            user=self.admin_ee, role_level="admin", department="Electrical", employee_id="ADM_EE_01"
        )
        self.dept_ee.head_of_department = self.admin_ee
        self.dept_ee.save()

        # Student CS
        self.student_cs = User.objects.create_user(email="stu_cs@univ.edu", password="Pw!", role="student")
        self.prof_cs = StudentProfile.objects.create(
            user=self.student_cs, name="CS Student", student_id="STU_CS_01",
            school=self.school.name, department=self.dept_cs.name
        )

        # Student EE
        self.student_ee = User.objects.create_user(email="stu_ee@univ.edu", password="Pw!", role="student")
        self.prof_ee = StudentProfile.objects.create(
            user=self.student_ee, name="EE Student", student_id="STU_EE_01",
            school=self.school.name, department=self.dept_ee.name
        )

        self.category = Category.objects.create(name="Department Lab Issue", category_type="academic", sla_hours=48)

        # Grievance CS
        self.g_cs = Grievance.objects.create(
            student=self.prof_cs, title="CS Lab AC", description="AC issue",
            category=self.category, department="Computer Science", status="pending"
        )

        # Grievance EE
        self.g_ee = Grievance.objects.create(
            student=self.prof_ee, title="EE Circuit Board", description="Board issue",
            category=self.category, department="Electrical", status="pending"
        )

    def test_dashboard_metrics_department_scoped(self):
        # Admin CS should see 1 grievance (only CS)
        self.client.force_login(self.admin_cs)
        response = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_grievances'], 1)

        # Superadmin should see 2 grievances (both CS and EE)
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_grievances'], 2)

    def test_update_status_to_in_progress(self):
        self.client.force_login(self.admin_cs)
        url = reverse('admin_panel:update_grievance_status', kwargs={'grievance_id': self.g_cs.id})
        response = self.client.post(url, json.dumps({'status': 'in_progress'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        self.g_cs.refresh_from_db()
        self.assertEqual(self.g_cs.status, 'in_progress')

    def test_update_status_pending_student_sets_sla_pause(self):
        self.client.force_login(self.admin_cs)
        url = reverse('admin_panel:update_grievance_status', kwargs={'grievance_id': self.g_cs.id})
        response = self.client.post(url, json.dumps({
            'status': 'pending_student',
            'resolution_notes': 'Awaiting your lab session receipt.'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.g_cs.refresh_from_db()
        self.assertEqual(self.g_cs.status, 'pending_student')
        self.assertIsNotNone(self.g_cs.sla_pause_time)

    def test_update_status_resolved_requires_closure_remark(self):
        settings = SystemSettings.load()
        settings.require_closure_remark = True
        settings.save()

        self.client.force_login(self.admin_cs)
        url = reverse('admin_panel:update_grievance_status', kwargs={'grievance_id': self.g_cs.id})

        # Attempt resolve without remarks -> 400
        response = self.client.post(url, json.dumps({
            'status': 'resolved',
            'resolution_notes': ''
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("remark is required", response.json()['error'])

        # Now with remarks -> 200
        response2 = self.client.post(url, json.dumps({
            'status': 'resolved',
            'resolution_notes': 'Lab AC repaired by technician.'
        }), content_type='application/json')
        self.assertEqual(response2.status_code, 200)

        self.g_cs.refresh_from_db()
        self.assertEqual(self.g_cs.status, 'resolved')
        self.assertIsNotNone(self.g_cs.actual_resolution_date)

    def test_process_grievance_appeal_approval_clears_resolution_date(self):
        self.g_cs.status = 'resolved'
        self.g_cs.actual_resolution_date = timezone.now()
        self.g_cs.is_appealed = True
        self.g_cs.save()

        appeal = Appeal.objects.create(
            grievance=self.g_cs,
            student=self.prof_cs,
            reason="Problem recurring"
        )

        self.client.force_login(self.admin_cs)
        url = reverse('admin_panel:process_grievance_appeal', kwargs={'grievance_id': self.g_cs.id})
        response = self.client.post(url, {
            'action': 'accept',
            'decision_notes': 'Reopening for further inspection.'
        })
        self.assertEqual(response.status_code, 302)

        self.g_cs.refresh_from_db()
        self.assertEqual(self.g_cs.status, 'in_progress')
        self.assertIsNone(self.g_cs.actual_resolution_date)
        self.assertFalse(self.g_cs.is_appealed)
