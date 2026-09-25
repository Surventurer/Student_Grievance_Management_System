from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from apps.students.models import StudentProfile, AdminProfile
from apps.grievances.models import (
    Category, Grievance, GrievanceComment, GrievanceStatusHistory, Appeal, AuditLog
)
from apps.admin_panel.models import SystemSettings
from apps.notifications.models import ReadNotification

User = get_user_model()


class StudentActionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.student_user = User.objects.create_user(
            email="action_student@university.edu",
            password="Password123!",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            name="Charlie Brown",
            student_id="STU_ACT_01",
            school="School of Technology",
            department="Computer Science"
        )

        self.admin_user = User.objects.create_user(
            email="action_admin@university.edu",
            password="Password123!",
            role="admin"
        )
        self.admin_profile = AdminProfile.objects.create(
            user=self.admin_user,
            role_level="admin",
            department="Computer Science",
            employee_id="EMP_ACT_01"
        )

        self.category = Category.objects.create(
            name="Hostel Issue",
            category_type="non_academic",
            sla_hours=48
        )

        self.grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Room Maintenance",
            description="AC not working in room 101",
            category=self.category,
            department="Computer Science",
            status="pending",
            priority="medium",
            assigned_to=self.admin_profile
        )

    @patch('apps.admin_panel.models.SystemSettings.is_support_active', True)
    def test_add_student_response_normal(self):
        self.client.force_login(self.student_user)
        url = reverse('students:add_student_response', kwargs={'grievance_id': self.grievance.id})
        response = self.client.post(url, {'student_response': 'Still waiting for an update.'})

        self.assertEqual(response.status_code, 302)
        comment = GrievanceComment.objects.filter(grievance=self.grievance, user=self.student_user).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.message, 'Still waiting for an update.')
        self.assertFalse(comment.is_internal)

    @patch('apps.admin_panel.models.SystemSettings.is_support_active', True)
    def test_add_student_response_unpauses_sla_when_pending_student(self):
        self.grievance.status = 'pending_student'
        pause_time = timezone.now() - timedelta(minutes=45)
        self.grievance.sla_pause_time = pause_time
        self.grievance.save()

        self.client.force_login(self.student_user)
        url = reverse('students:add_student_response', kwargs={'grievance_id': self.grievance.id})
        response = self.client.post(url, {'student_response': 'Here are the details you requested.'})

        self.assertEqual(response.status_code, 302)
        self.grievance.refresh_from_db()

        self.assertEqual(self.grievance.status, 'pending')
        self.assertIsNone(self.grievance.sla_pause_time)
        self.assertGreaterEqual(self.grievance.accumulated_sla_pause_minutes, 44)

        # Check status history recorded
        status_hist = GrievanceStatusHistory.objects.filter(
            grievance=self.grievance,
            previous_status='pending_student',
            new_status='pending'
        ).first()
        self.assertIsNotNone(status_hist)

        # Check audit log recorded
        audit = AuditLog.objects.filter(
            target_id=str(self.grievance.id),
            action='update'
        ).first()
        self.assertIsNotNone(audit)

    @patch('apps.admin_panel.models.SystemSettings.is_support_active', True)
    def test_add_student_response_blocked_when_resolved(self):
        self.grievance.status = 'resolved'
        self.grievance.save()

        self.client.force_login(self.student_user)
        url = reverse('students:add_student_response', kwargs={'grievance_id': self.grievance.id})
        response = self.client.post(url, {'student_response': 'Can I still message?'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(GrievanceComment.objects.filter(grievance=self.grievance, user=self.student_user).count(), 0)

    @patch('apps.admin_panel.models.SystemSettings.is_support_active', False)
    def test_add_student_response_blocked_outside_support_hours(self):
        self.client.force_login(self.student_user)
        url = reverse('students:add_student_response', kwargs={'grievance_id': self.grievance.id})
        response = self.client.post(url, {'student_response': 'Midnight message.'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(GrievanceComment.objects.filter(grievance=self.grievance, user=self.student_user).count(), 0)

    def test_appeal_grievance_view_success(self):
        self.grievance.status = 'resolved'
        self.grievance.actual_resolution_date = timezone.now()
        self.grievance.save()

        self.client.force_login(self.student_user)
        url = reverse('students:appeal_grievance', kwargs={'grievance_id': self.grievance.id})
        response = self.client.post(url, {'reason': 'The issue was not properly solved.'})

        self.assertEqual(response.status_code, 302)
        self.grievance.refresh_from_db()

        self.assertTrue(self.grievance.is_appealed)
        self.assertEqual(self.grievance.status, 'pending')
        self.assertEqual(self.grievance.appeals.count(), 1)
        self.assertEqual(self.grievance.appeals.first().reason, 'The issue was not properly solved.')

    def test_appeal_grievance_blocked_if_not_resolved_or_rejected(self):
        self.grievance.status = 'pending'
        self.grievance.save()

        self.client.force_login(self.student_user)
        url = reverse('students:appeal_grievance', kwargs={'grievance_id': self.grievance.id})
        response = self.client.post(url, {'reason': 'Premature appeal.'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.grievance.is_appealed)
        self.assertEqual(self.grievance.appeals.count(), 0)

    def test_appeal_grievance_max_limit_enforced(self):
        self.grievance.status = 'resolved'
        self.grievance.save()

        settings = SystemSettings.load()
        settings.max_reopen_count = 1
        settings.save()

        # Create 1 existing appeal
        Appeal.objects.create(
            grievance=self.grievance,
            student=self.student_profile,
            reason="First appeal"
        )

        self.client.force_login(self.student_user)
        url = reverse('students:appeal_grievance', kwargs={'grievance_id': self.grievance.id})
        response = self.client.post(url, {'reason': 'Second appeal attempt'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.grievance.appeals.count(), 1)

    def test_mark_notification_read(self):
        comment = GrievanceComment.objects.create(
            grievance=self.grievance,
            user=self.admin_user,
            message="Please provide more information.",
            comment_type='comment'
        )

        self.client.force_login(self.student_user)
        url = reverse('students:mark_notification_read', kwargs={'notification_id': comment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['was_new'])

        self.assertTrue(
            ReadNotification.objects.filter(student=self.student_user, comment=comment).exists()
        )
