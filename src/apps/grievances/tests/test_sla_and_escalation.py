from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command
from io import StringIO

from apps.students.models import StudentProfile, AdminProfile, Department
from apps.grievances.models import Category, Grievance, EscalationLog
from apps.grievances.tasks import check_sla_and_escalate, escalate_grievance
from apps.admin_panel.models import SystemSettings

User = get_user_model()


class SLAAndEscalationTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Computer Science")

        self.student_user = User.objects.create_user(
            email="sla_student@univ.edu", password="Pw!", role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            name="Ada Lovelace",
            student_id="STU_SLA_01",
            school="School of Computing",
            department=self.dept.name
        )

        self.officer_user = User.objects.create_user(email="officer_cs@univ.edu", password="Pw!", role="officer")
        self.officer_prof = AdminProfile.objects.create(
            user=self.officer_user, role_level="officer", department=self.dept.name, employee_id="OFF_CS_01"
        )

        self.admin_user = User.objects.create_user(email="admin_cs@univ.edu", password="Pw!", role="admin")
        self.admin_prof = AdminProfile.objects.create(
            user=self.admin_user, role_level="admin", department=self.dept.name, employee_id="ADM_CS_01"
        )

        self.super_user = User.objects.create_user(email="super_dean@univ.edu", password="Pw!", role="superadmin")
        self.super_prof = AdminProfile.objects.create(
            user=self.super_user, role_level="superadmin", department="Dean Office", employee_id="SUP_01"
        )

        self.category = Category.objects.create(
            name="Academic Evaluation",
            category_type="academic",
            sla_hours=24
        )

        self.grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Grade discrepancy in CS101",
            description="Midterm scores miscalculated",
            category=self.category,
            department=self.dept.name,
            status="pending",
            priority="medium",
            assigned_to=self.officer_prof,
            escalation_level=0
        )

    def test_escalate_level_0_to_level_1(self):
        result = escalate_grievance(self.grievance)
        self.assertTrue(result)
        self.grievance.refresh_from_db()

        self.assertTrue(self.grievance.is_escalated)
        self.assertEqual(self.grievance.escalation_level, 1)
        self.assertEqual(self.grievance.assigned_to, self.admin_prof)

        log = EscalationLog.objects.filter(grievance=self.grievance).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.escalated_from, self.officer_prof)
        self.assertEqual(log.escalated_to, self.admin_prof)

    def test_escalate_level_1_to_level_2(self):
        # First escalate to Level 1
        escalate_grievance(self.grievance)
        self.grievance.refresh_from_db()
        self.assertEqual(self.grievance.escalation_level, 1)

        # Now escalate from Level 1 to Level 2 (Superadmin)
        result = escalate_grievance(self.grievance)
        self.assertTrue(result)
        self.grievance.refresh_from_db()

        self.assertEqual(self.grievance.escalation_level, 2)
        self.assertEqual(self.grievance.assigned_to, self.super_prof)

    def test_check_sla_and_escalate_task_breached(self):
        # Backdate submitted_at by 50 hours (breaching 24h SLA)
        past_time = timezone.now() - timedelta(hours=50)
        Grievance.objects.filter(id=self.grievance.id).update(submitted_at=past_time)

        msg = check_sla_and_escalate()
        self.assertIn("Escalated 1 grievances", msg)

        self.grievance.refresh_from_db()
        self.assertEqual(self.grievance.escalation_level, 1)
        self.assertEqual(self.grievance.assigned_to, self.admin_prof)

    def test_check_sla_and_escalate_level_1_reference_timestamp_fix(self):
        # Grievance is at level 1 with a previous escalation log
        self.grievance.escalation_level = 1
        self.grievance.assigned_to = self.admin_prof
        self.grievance.is_escalated = True
        self.grievance.save()

        # Previous escalation log created 30 hours ago (breaching 24h)
        esc_log = EscalationLog.objects.create(
            grievance=self.grievance,
            escalated_from=self.officer_prof,
            escalated_to=self.admin_prof,
            reason="Level 1 escalation"
        )
        EscalationLog.objects.filter(id=esc_log.id).update(
            timestamp=timezone.now() - timedelta(hours=30)
        )

        msg = check_sla_and_escalate()
        self.assertIn("Escalated 1 grievances", msg)

        self.grievance.refresh_from_db()
        self.assertEqual(self.grievance.escalation_level, 2)
        self.assertEqual(self.grievance.assigned_to, self.super_prof)

    def test_check_sla_and_escalate_pauses_for_pending_student(self):
        self.grievance.status = 'pending_student'
        self.grievance.save()

        past_time = timezone.now() - timedelta(hours=50)
        Grievance.objects.filter(id=self.grievance.id).update(submitted_at=past_time)

        msg = check_sla_and_escalate()
        self.assertEqual(msg, "Escalated 0 grievances.")
        self.grievance.refresh_from_db()
        self.assertEqual(self.grievance.escalation_level, 0)

    def test_process_slas_management_command(self):
        settings = SystemSettings.load()
        settings.auto_resolve_days = 15
        settings.escalation_threshold = 5
        settings.sla_breach_action = 'both'
        settings.save()

        # 1 Stale grievance older than 20 days
        stale_time = timezone.now() - timedelta(days=20)
        Grievance.objects.filter(id=self.grievance.id).update(
            updated_at=stale_time,
            submitted_at=stale_time
        )

        out = StringIO()
        call_command('process_slas', stdout=out)
        output = out.getvalue()

        self.assertIn("Auto-resolved 1 grievances", output)
        self.grievance.refresh_from_db()
        self.assertEqual(self.grievance.status, 'resolved')
