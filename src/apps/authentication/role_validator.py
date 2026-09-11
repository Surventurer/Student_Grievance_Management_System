"""
Role validation utilities for the Student Grievance Management System
"""
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.students.models import AdminProfile, StudentProfile

User = get_user_model()


class RoleValidator:
    """Utility class to validate and fix role-related issues"""
    
    @staticmethod
    def validate_user_role_consistency(user):
        """Validate that user role matches their profile"""
        issues = []
        
        if user.role == 'student':
            if not hasattr(user, 'student_profile') or not user.student_profile:
                issues.append(f"Student user {user.email} missing StudentProfile")
        
        elif user.role in ['admin', 'officer', 'superadmin']:
            if not hasattr(user, 'admin_profile') or not user.admin_profile:
                issues.append(f"Admin user {user.email} missing AdminProfile")
            elif user.admin_profile.role_level != user.role:
                issues.append(f"User {user.email} role mismatch: User.role={user.role}, AdminProfile.role_level={user.admin_profile.role_level}")
        
        return issues
    
    @staticmethod
    def fix_role_inconsistencies():
        """Fix role inconsistencies in the system"""
        fixed_issues = []
        
        # Fix admin users without profiles
        admin_users = User.objects.filter(role__in=['admin', 'officer', 'superadmin'])
        for user in admin_users:
            if not hasattr(user, 'admin_profile') or not user.admin_profile:
                # Create missing admin profile
                AdminProfile.objects.create(
                    user=user,
                    role_level=user.role,
                    employee_id=f"EMP{user.id:04d}",
                    department="General" if user.role == 'superadmin' else "Unassigned"
                )
                fixed_issues.append(f"Created AdminProfile for {user.email}")
        
        # Fix student users without profiles
        student_users = User.objects.filter(role='student')
        for user in student_users:
            if not hasattr(user, 'student_profile') or not user.student_profile:
                # Create missing student profile
                StudentProfile.objects.create(
                    user=user,
                    name=f"Student {user.id}",
                    student_id=f"STU{user.id:04d}",
                    department="General",
                    school="General"
                )
                fixed_issues.append(f"Created StudentProfile for {user.email}")
        
        # Fix role level mismatches
        admin_profiles = AdminProfile.objects.all()
        for profile in admin_profiles:
            if profile.user.role != profile.role_level:
                old_role = profile.role_level
                profile.role_level = profile.user.role
                profile.save()
                fixed_issues.append(f"Fixed role mismatch for {profile.user.email}: {old_role} -> {profile.user.role}")
        
        return fixed_issues
    
    @staticmethod
    def get_role_permissions(role):
        """Get permissions for a specific role"""
        permissions = {
            'superadmin': [
                'view_all_data', 'manage_users', 'manage_system', 'manage_categories',
                'view_audit_logs', 'manage_auto_assignment', 'delete_users', 
                'modify_roles', 'system_backup', 'database_access'
            ],
            'admin': [
                'view_department_data', 'manage_department_students', 'manage_department_grievances',
                'assign_grievances', 'view_department_reports', 'manage_department_categories'
            ],
            'officer': [
                'view_assigned_grievances', 'update_grievance_status', 'add_comments',
                'view_assigned_students', 'update_own_profile'
            ],
            'student': [
                'submit_grievances', 'view_own_grievances', 'update_own_profile',
                'upload_documents'
            ]
        }
        return permissions.get(role, [])
    
    @staticmethod
    def can_user_perform_action(user, action):
        """Check if user can perform a specific action"""
        if not user or not user.is_authenticated:
            return False
            
        user_permissions = RoleValidator.get_role_permissions(user.role)
        return action in user_permissions
    
    @staticmethod
    def get_accessible_departments(user):
        """Get departments accessible to a user"""
        if user.role == 'superadmin':
            from apps.students.models import Department
            return Department.objects.all()
        
        elif user.role == 'admin':
            from apps.students.models import Department
            if hasattr(user, 'admin_profile') and user.admin_profile.department:
                return Department.objects.filter(name=user.admin_profile.department)
        
        elif user.role == 'student':
            from apps.students.models import Department
            if hasattr(user, 'student_profile') and user.student_profile.department:
                return Department.objects.filter(name=user.student_profile.department)
        
        return []
    
    @staticmethod
    def validate_system_integrity():
        """Validate overall system role integrity"""
        issues = []
        
        # Check all users
        for user in User.objects.all():
            user_issues = RoleValidator.validate_user_role_consistency(user)
            issues.extend(user_issues)
        
        # Check for orphaned profiles
        admin_profiles = AdminProfile.objects.select_related('user')
        for profile in admin_profiles:
            if not profile.user or profile.user.role not in ['admin', 'officer', 'superadmin']:
                issues.append(f"Orphaned AdminProfile for user {profile.user.email if profile.user else 'None'}")
        
        student_profiles = StudentProfile.objects.select_related('user')
        for profile in student_profiles:
            if not profile.user or profile.user.role != 'student':
                issues.append(f"Orphaned StudentProfile for user {profile.user.email if profile.user else 'None'}")
        
        return issues
