from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from unittest.mock import patch

from apps.notifications.models import Notification, ReadNotification
from apps.notifications.tasks import send_email_notification
from apps.students.models import StudentProfile
from apps.grievances.models import Category, Grievance, GrievanceComment
from apps.admin_panel.models import SystemSettings

User = get_user_model()


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="notif_user@univ.edu", password="Pw!", role="student")
        self.profile = StudentProfile.objects.create(
            user=self.user, name="Notif User", student_id="NOTIF01", school="ENG", department="CS"
        )
        self.category = Category.objects.create(name="Admin Issue", category_type="academic")
        self.grievance = Grievance.objects.create(
            student=self.profile, title="Issue", description="Desc", category=self.category
        )
        self.comment = GrievanceComment.objects.create(
            grievance=self.grievance, user=self.user, message="Hello comment"
        )

    def test_read_notification_creation_and_unique_constraint(self):
        read_notif = ReadNotification.objects.create(
            student=self.user,
            comment=self.comment
        )
        self.assertEqual(str(read_notif), f"{self.user.email} read comment {self.comment.id}")

        # Duplicate should fail with IntegrityError
        with self.assertRaises(IntegrityError):
            ReadNotification.objects.create(
                student=self.user,
                comment=self.comment
            )

    def test_notification_creation_and_ordering(self):
        n1 = Notification.objects.create(
            recipient=self.user,
            title="First Notification",
            message="Msg 1",
            notification_type="system"
        )
        n2 = Notification.objects.create(
            recipient=self.user,
            title="Second Notification",
            message="Msg 2",
            notification_type="status_update"
        )

        self.assertFalse(n1.is_read)
        self.assertFalse(n2.is_read)

        notifications = list(Notification.objects.filter(recipient=self.user))
        self.assertEqual(notifications[0], n2)  # Most recent first
        self.assertEqual(notifications[1], n1)


class NotificationViewsApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="api_notif@univ.edu", password="Pw!", role="student")
        self.notification = Notification.objects.create(
            recipient=self.user,
            title="Important Alert",
            message="Please review your grievance.",
            notification_type="status_update"
        )
        self.client.force_login(self.user)

    def test_notification_list_api(self):
        response = self.client.get('/notifications/list/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['notifications'][0]['title'], "Important Alert")

    def test_mark_notification_read_api(self):
        url = f'/notifications/mark-read/{self.notification.id}/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_mark_all_notifications_read_api(self):
        # Create second unread notification
        Notification.objects.create(
            recipient=self.user,
            title="Second Alert",
            message="Another update.",
            notification_type="comment"
        )
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 2)

        response = self.client.post('/notifications/mark-all-read/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cleared_count'], 2)

        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)


class NotificationEmailTasksTest(TestCase):
    def test_email_notification_suppressed_when_disabled(self):
        settings = SystemSettings.load()
        settings.email_notifications = False
        settings.save()

        result = send_email_notification(
            "Test Subject",
            "student@univ.edu",
            "emails/base_email.html",
            {"message": "Hello"}
        )
        self.assertIn("Email notification suppressed by system settings", result)

    @patch('apps.notifications.tasks.send_mail')
    @patch('apps.notifications.tasks.render_to_string')
    def test_email_notification_sent_when_enabled(self, mock_render, mock_send_mail):
        settings = SystemSettings.load()
        settings.email_notifications = True
        settings.save()

        mock_render.return_value = "<html><body>Test Email Content</body></html>"

        result = send_email_notification(
            "Test Subject",
            "student@univ.edu",
            "emails/base_email.html",
            {"message": "Hello"}
        )
        self.assertIn("Email sent successfully", result)
        mock_send_mail.assert_called_once()
