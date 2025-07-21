#!/usr/bin/env python
"""
Test script to validate the role-based Student Grievance Management System
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.authentication.role_validator import RoleValidator
from apps.students.models import AdminProfile, StudentProfile

User = get_user_model()

def test_role_system():
    """Test the role-based system"""
    print("🧪 Testing Role-Based Student Grievance Management System")
    print("=" * 60)
    
    # Test 1: User Creation and Role Assignment
    print("\n📝 Test 1: User Creation and Role Assignment")
    users = User.objects.all()
    print(f"Total Users: {users.count()}")
    
    for user in users:
        print(f"  {user.email} -> {user.get_role_display()} ({user.role})")
        
        # Test role properties
        print(f"    is_student: {user.is_student}")
        print(f"    is_admin: {user.is_admin}")  
        print(f"    is_superadmin: {user.is_superadmin}")
        
        # Test permissions
        if hasattr(user, 'has_permission'):
            print(f"    can manage_users: {user.has_permission('manage_users')}")
            print(f"    can view_all_data: {user.has_permission('view_all_data')}")
        
        print()
    
    # Test 2: Profile Consistency
    print("\n🔍 Test 2: Profile Consistency")
    issues = RoleValidator.validate_system_integrity()
    if issues:
        print(f"❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ No role integrity issues found!")
    
    # Test 3: Role Permissions
    print("\n🔒 Test 3: Role Permissions")
    for role_choice in User.ROLE_CHOICES:
        role = role_choice[0]
        role_name = role_choice[1]
        permissions = RoleValidator.get_role_permissions(role)
        print(f"{role_name} ({role}):")
        for perm in permissions:
            print(f"  ✓ {perm}")
        print()
    
    # Test 4: Admin Profile Check
    print("\n👥 Test 4: Admin Profile Check")
    admin_profiles = AdminProfile.objects.all()
    for profile in admin_profiles:
        print(f"  {profile.user.email} -> {profile.get_role_level_display()} in {profile.department}")
        print(f"    Employee ID: {profile.employee_id}")
        print(f"    Role Level: {profile.role_level}")
        print(f"    User Role: {profile.user.role}")
        print(f"    Match: {profile.role_level == profile.user.role}")
        print()
    
    # Test 5: Student Profile Check
    print("\n🎓 Test 5: Student Profile Check")
    student_profiles = StudentProfile.objects.all()
    for profile in student_profiles:
        print(f"  {profile.user.email} -> {profile.name} ({profile.student_id})")
        print(f"    Department: {profile.department}")
        print(f"    School: {profile.school}")
        print(f"    User Role: {profile.user.role}")
        print()
    
    # Test 6: Role-based Access
    print("\n🚪 Test 6: Role-based Access")
    test_actions = [
        'manage_users', 'view_all_data', 'manage_system',
        'view_department_data', 'assign_grievances',
        'view_assigned_grievances', 'submit_grievances'
    ]
    
    for user in users:
        print(f"\n{user.email} ({user.get_role_display()}) can:")
        for action in test_actions:
            can_perform = RoleValidator.can_user_perform_action(user, action)
            status = "✅" if can_perform else "❌"
            print(f"  {status} {action}")
    
    print("\n🎉 Role-based system test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_role_system()
