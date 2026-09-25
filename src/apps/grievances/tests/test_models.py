from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.students.models import StudentProfile, AdminProfile
from apps.grievances.models import (
    Category, CategoryAssignment, Grievance, GrievanceAttachment, GrievanceComment
)

User = get_user_model()


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Hostel Amenities",
            description="Hostel related issues",
            category_type="non_academic",
            sla_hours=48
        )

    def test_category_str(self):
        self.assertEqual(str(self.category), "Hostel Amenities (Non-Academic)")

    def test_is_other_category(self):
        self.assertFalse(self.category.is_other_category)
        other_cat = Category.objects.create(
            name="Other Issues",
            category_type="academic",
            sla_hours=24
        )
        self.assertTrue(other_cat.is_other_category)

    def test_get_assigned_hod_fallback(self):
        admin_user = User.objects.create_user(email="catadmin@univ.edu", password="Pw!", role="admin")
        admin_prof = AdminProfile.objects.create(
            user=admin_user, role_level="admin", department="Civil", employee_id="CAT_ADM_01"
        )
        self.category.default_admin = admin_prof
        self.category.save()

        # Without matching assignment, returns default_admin
        self.assertEqual(self.category.get_assigned_hod("UnknownDept"), admin_prof)

    def test_get_assigned_hod_specific_assignment(self):
        admin_user = User.objects.create_user(email="deptadmin@univ.edu", password="Pw!", role="admin")
        admin_prof = AdminProfile.objects.create(
            user=admin_user, role_level="admin", department="Mechanical", employee_id="CAT_ADM_02"
        )
        CategoryAssignment.objects.create(
            category=self.category,
            department="Mechanical",
            assigned_admin=admin_prof
        )
        self.assertEqual(self.category.get_assigned_hod("Mechanical"), admin_prof)


class GrievanceModelTest(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            email="grievancetest_student@univ.edu",
            password="Password123!",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            name="Diana Prince",
            student_id="STU_GRV_01",
            school="Engineering",
            department="Electrical"
        )
        self.category = Category.objects.create(
            name="Laboratory Equipment",
            category_type="academic",
            sla_hours=48
        )
        self.grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Broken multimeter in lab 3",
            description="Multimeter displays 000 always.",
            category=self.category,
            department="Electrical",
            priority="medium"
        )

    def test_grievance_id_property(self):
        expected_prefix = f"GRV-{str(self.grievance.id)[:8].upper()}"
        self.assertEqual(self.grievance.grievance_id, expected_prefix)

    def test_resolved_at_property(self):
        self.assertIsNone(self.grievance.resolved_at)
        now = timezone.now()
        self.grievance.actual_resolution_date = now
        self.grievance.save()
        self.assertEqual(self.grievance.resolved_at, now)

    def test_effective_sla_hours_multipliers(self):
        self.grievance.priority = 'urgent'
        self.assertEqual(self.grievance.effective_sla_hours, 12)  # 48 * 0.25 = 12

        self.grievance.priority = 'high'
        self.assertEqual(self.grievance.effective_sla_hours, 24)  # 48 * 0.5 = 24

        self.grievance.priority = 'medium'
        self.assertEqual(self.grievance.effective_sla_hours, 48)  # 48 * 1.0 = 48

        self.grievance.priority = 'low'
        self.assertEqual(self.grievance.effective_sla_hours, 72)  # 48 * 1.5 = 72

    def test_effective_sla_hours_minimum_clamp(self):
        low_sla_cat = Category.objects.create(name="Quick Query", sla_hours=10)
        self.grievance.category = low_sla_cat
        self.grievance.priority = 'urgent'  # 10 * 0.25 = 2.5, clamped to min 6
        self.assertEqual(self.grievance.effective_sla_hours, 6)

    def test_soft_delete(self):
        self.assertFalse(self.grievance.is_archived)
        self.grievance.soft_delete()
        self.grievance.refresh_from_db()
        self.assertTrue(self.grievance.is_archived)


class GrievanceCommentTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="commenter@univ.edu", password="Pw!", role="student")
        self.student_profile = StudentProfile.objects.create(
            user=self.user, name="Commenter", student_id="STU_COM_01", school="Sci", department="Physics"
        )
        self.category = Category.objects.create(name="Lab")
        self.grievance = Grievance.objects.create(
            student=self.student_profile, title="Lab issue", description="Desc", category=self.category
        )

    def test_comment_creation(self):
        comment = GrievanceComment.objects.create(
            grievance=self.grievance,
            user=self.user,
            message="Test comment message",
            is_internal=False
        )
        self.assertEqual(str(comment), f"Comment by {self.user.email} on {self.grievance.title}")
        self.assertFalse(comment.is_internal)
