from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.students.models import School, Department, StudentProfile, AdminProfile

User = get_user_model()


class SchoolModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="School of Engineering and Technology",
            code="SOET",
            description="Engineering school",
            is_active=True
        )

    def test_school_str(self):
        self.assertEqual(str(self.school), "School of Engineering and Technology")

    def test_school_unique_name(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            School.objects.create(name="School of Engineering and Technology", code="SOET2")


class DepartmentModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="School of Computing", code="SOC")
        self.department = Department.objects.create(
            name="Computer Science and Engineering",
            school=self.school
        )

    def test_department_str(self):
        self.assertEqual(
            str(self.department),
            "Computer Science and Engineering - School of Computing"
        )

        dept_no_school = Department.objects.create(name="General Studies")
        self.assertEqual(str(dept_no_school), "General Studies")

    def test_department_students_property(self):
        user = User.objects.create_user(
            email="csestudent@university.edu",
            password="TestPassword123!",
            role="student"
        )
        StudentProfile.objects.create(
            user=user,
            name="CSE Student",
            student_id="STU_CSE_001",
            school=self.school.name,
            department=self.department.name
        )
        self.assertEqual(self.department.students.count(), 1)
        self.assertEqual(self.department.students.first().user, user)

    def test_auto_assign_hod_if_needed(self):
        # When no admin exists, returns None
        self.assertIsNone(self.department.auto_assign_hod_if_needed())
        self.assertIsNone(self.department.head_of_department)

        # Create department admin
        admin_user = User.objects.create_user(
            email="admin_cse@university.edu",
            password="AdminPassword123!",
            role="admin"
        )
        admin_profile = AdminProfile.objects.create(
            user=admin_user,
            role_level="admin",
            department=self.department.name,
            employee_id="EMP_CSE_01"
        )

        # Department auto HOD should assign admin_user
        assigned = self.department.auto_assign_hod_if_needed()
        self.assertEqual(assigned, admin_user)
        self.department.refresh_from_db()
        self.assertEqual(self.department.head_of_department, admin_user)

        # Re-running keeps the same valid HOD
        assigned2 = self.department.auto_assign_hod_if_needed()
        self.assertEqual(assigned2, admin_user)

        # If admin becomes inactive, auto_assign_hod clears HOD
        admin_user.is_active = False
        admin_user.save()
        assigned_inactive = self.department.auto_assign_hod_if_needed()
        self.assertIsNone(assigned_inactive)
        self.department.refresh_from_db()
        self.assertIsNone(self.department.head_of_department)


class AdminProfileModelTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Mechanical Engineering")

    def test_admin_profile_role_sync(self):
        user = User.objects.create_user(
            email="officer_mech@university.edu",
            password="Password123!",
            role="student"  # Starts as student
        )
        profile = AdminProfile.objects.create(
            user=user,
            role_level="officer",
            department=self.dept.name,
            employee_id="EMP_OFFICER_01"
        )
        user.refresh_from_db()
        self.assertEqual(user.role, "officer")

    def test_admin_profile_auto_assigns_hod_on_save(self):
        admin_user = User.objects.create_user(
            email="hod_mech@university.edu",
            password="Password123!",
            role="admin"
        )
        profile = AdminProfile.objects.create(
            user=admin_user,
            role_level="admin",
            department=self.dept.name,
            employee_id="EMP_MECH_01"
        )
        self.dept.refresh_from_db()
        self.assertEqual(self.dept.head_of_department, admin_user)

    def test_admin_profile_reassigns_hod_on_dept_change(self):
        dept2 = Department.objects.create(name="Civil Engineering")
        admin_user = User.objects.create_user(
            email="transfer_admin@university.edu",
            password="Password123!",
            role="admin"
        )
        profile = AdminProfile.objects.create(
            user=admin_user,
            role_level="admin",
            department=self.dept.name,
            employee_id="EMP_TRANSFER_01"
        )
        self.dept.refresh_from_db()
        self.assertEqual(self.dept.head_of_department, admin_user)

        # Move to Civil Engineering
        profile.department = dept2.name
        profile.save()

        self.dept.refresh_from_db()
        dept2.refresh_from_db()
        self.assertIsNone(self.dept.head_of_department)
        self.assertEqual(dept2.head_of_department, admin_user)

    def test_admin_profile_permission_properties(self):
        superadmin_user = User.objects.create_user(email="super@univ.edu", password="Pw!", role="superadmin")
        superadmin_profile = AdminProfile.objects.create(
            user=superadmin_user, role_level="superadmin", department="Admin", employee_id="SA01"
        )
        self.assertTrue(superadmin_profile.can_manage_department)
        self.assertTrue(superadmin_profile.can_assign_grievances)
        self.assertEqual(superadmin_profile.accessible_departments.count(), Department.objects.count())

        officer_user = User.objects.create_user(email="officer@univ.edu", password="Pw!", role="officer")
        officer_profile = AdminProfile.objects.create(
            user=officer_user, role_level="officer", department="Civil", employee_id="OFF01"
        )
        self.assertFalse(officer_profile.can_manage_department)
        self.assertFalse(officer_profile.can_assign_grievances)
        self.assertEqual(officer_profile.accessible_departments.count(), 0)


class StudentProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student_profile@university.edu",
            password="StudentPass123!",
            role="student"
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            name="Alice Smith",
            student_id="STU1001",
            school="School of Computing",
            department="Computer Science",
            contact_no="9876543210"
        )

    def test_student_profile_str(self):
        self.assertEqual(str(self.profile), "STU1001 - Alice Smith")

    def test_student_profile_email_property(self):
        self.assertEqual(self.profile.email, self.user.email)
