from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.students.models import StudentProfile, AdminProfile, Department
from apps.grievances.models import Category, CategoryAssignment, Grievance
from apps.admin_panel.models import SystemSettings

User = get_user_model()


class AutoAssignmentEngineTest(TestCase):
    def setUp(self):
        # Enable auto assignment in system settings
        settings = SystemSettings.load()
        settings.auto_assignment = True
        settings.save()

        self.dept_cs = Department.objects.create(name="Computer Science")
        self.dept_ee = Department.objects.create(name="Electrical")

        self.student_user = User.objects.create_user(
            email="auto_student@univ.edu", password="Password123!", role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            name="Grace Hopper",
            student_id="STU_AUTO_01",
            school="School of Computing",
            department=self.dept_cs.name
        )

        self.category = Category.objects.create(
            name="Network / Infrastructure",
            category_type="non_academic",
            auto_assign_enabled=True,
            sla_hours=24
        )

    def test_tier1_department_category_assignment(self):
        admin_user = User.objects.create_user(email="cs_net@univ.edu", password="Pw!", role="admin")
        admin_prof = AdminProfile.objects.create(
            user=admin_user, role_level="admin", department=self.dept_cs.name, employee_id="EMP_CS_NET"
        )
        CategoryAssignment.objects.create(
            category=self.category,
            department=self.dept_cs.name,
            assigned_admin=admin_prof,
            is_active=True
        )

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Lab switch malfunction",
            description="Ethernet ports disconnected in CS Lab 2",
            category=self.category,
            department=self.dept_cs.name
        )
        assigned, reason = grievance.auto_assign()

        self.assertEqual(assigned, admin_prof)
        self.assertIn("Department-specific category assignment", reason)

    def test_tier2_keyword_matching(self):
        admin_user = User.objects.create_user(email="wifi_specialist@univ.edu", password="Pw!", role="admin")
        admin_prof = AdminProfile.objects.create(
            user=admin_user, role_level="admin", department="IT Services", employee_id="EMP_WIFI"
        )
        CategoryAssignment.objects.create(
            category=self.category,
            department="IT Services",
            assigned_admin=admin_prof,
            auto_assign_keywords="wifi, wireless, eduroam",
            is_active=True
        )

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Slow WiFi",
            description="The wireless connection in hostel is dropping continuously",
            category=self.category,
            department=None  # department unspecified
        )
        assigned, reason = grievance.auto_assign()

        self.assertEqual(assigned, admin_prof)
        self.assertIn("Keyword match", reason)

    def test_tier3_department_officer_assignment(self):
        officer_user = User.objects.create_user(email="ee_officer@univ.edu", password="Pw!", role="officer")
        officer_prof = AdminProfile.objects.create(
            user=officer_user, role_level="officer", department=self.dept_ee.name, employee_id="EMP_EE_OFF"
        )

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Electrical board sparking",
            description="Dangerous spark near circuit breaker",
            category=self.category,
            department=self.dept_ee.name
        )
        assigned, reason = grievance.auto_assign()

        self.assertEqual(assigned, officer_prof)
        self.assertIn("Department Grievance Officer", reason)

    def test_tier3b_department_admin_hod_fallback(self):
        # When no officer exists, assign to Department Admin
        admin_user = User.objects.create_user(email="ee_hod@univ.edu", password="Pw!", role="admin")
        admin_prof = AdminProfile.objects.create(
            user=admin_user, role_level="admin", department=self.dept_ee.name, employee_id="EMP_EE_HOD"
        )

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Power failure in EE wing",
            description="Transformer trip",
            category=self.category,
            department=self.dept_ee.name
        )
        assigned, reason = grievance.auto_assign()

        self.assertEqual(assigned, admin_prof)
        self.assertIn("Direct HOD Intake", reason)

    def test_tier4_category_default_admin(self):
        default_user = User.objects.create_user(email="default_cat_admin@univ.edu", password="Pw!", role="admin")
        default_prof = AdminProfile.objects.create(
            user=default_user, role_level="admin", department="Central Facilities", employee_id="EMP_DEF"
        )
        self.category.default_admin = default_prof
        self.category.save()

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Campus-wide query",
            description="General inquiry",
            category=self.category,
            department=None
        )
        assigned, reason = grievance.auto_assign()

        self.assertEqual(assigned, default_prof)
        self.assertIn("Category default admin", reason)

    def test_tier5_superadmin_fallback(self):
        super_user = User.objects.create_user(email="superadmin@univ.edu", password="Pw!", role="superadmin")
        super_prof = AdminProfile.objects.create(
            user=super_user, role_level="superadmin", department="Dean Office", employee_id="EMP_SUPER"
        )

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Unassigned grievance",
            description="Mystery issue with no dept or category admin",
            category=self.category,
            department=None
        )
        assigned, reason = grievance.auto_assign()

        self.assertEqual(assigned, super_prof)
        self.assertTrue(grievance.is_escalated)
        self.assertEqual(grievance.escalation_level, 2)
        self.assertIn("Central Cell Fallback", reason)

    def test_disabled_auto_assignment_global(self):
        settings = SystemSettings.load()
        settings.auto_assignment = False
        settings.save()

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Disabled test",
            description="Desc",
            category=self.category
        )
        assigned, reason = grievance.auto_assign()
        self.assertIsNone(assigned)
        self.assertIn("System-wide auto-assignment is disabled", reason)

    def test_disabled_auto_assignment_category(self):
        self.category.auto_assign_enabled = False
        self.category.save()

        grievance = Grievance.objects.create(
            student=self.student_profile,
            title="Cat disabled test",
            description="Desc",
            category=self.category
        )
        assigned, reason = grievance.auto_assign()
        self.assertIsNone(assigned)
        self.assertIn("Auto-assignment disabled for this category", reason)
