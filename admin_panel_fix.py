#!/usr/bin/env python3
"""
Comprehensive Admin Panel Fix Script
This script will create all necessary data and fix any remaining issues
"""

import os
import sys
import django

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import authenticate
from apps.authentication.models import User
from apps.grievances.models import Grievance, Category
from apps.students.models import StudentProfile, Department, School

def ensure_admin_user():
    """Ensure admin user exists and is properly configured"""
    print("=== Ensuring Admin User ===")
    
    admin_email = 'admin@grievance.com'
    admin_password = 'admin123'
    
    try:
        admin_user = User.objects.get(email=admin_email)
        print(f"✓ Admin user already exists: {admin_user.email}")
        
        # Update admin user properties if needed
        if admin_user.role != 'admin':
            admin_user.role = 'admin'
        if not admin_user.is_staff:
            admin_user.is_staff = True
        if not admin_user.is_email_verified:
            admin_user.is_email_verified = True
        if not admin_user.is_active:
            admin_user.is_active = True
        
        admin_user.save()
        print(f"✓ Admin user updated - Role: {admin_user.role}, Staff: {admin_user.is_staff}")
        
    except User.DoesNotExist:
        print(f"✗ Admin user not found, creating new one...")
        admin_user = User.objects.create_user(
            email=admin_email,
            password=admin_password,
            role='admin',
            is_staff=True,
            is_email_verified=True,
            is_active=True
        )
        print(f"✓ Admin user created: {admin_user.email}")
    
    # Test authentication
    auth_user = authenticate(email=admin_email, password=admin_password)
    if auth_user:
        print(f"✓ Admin authentication working")
        return True
    else:
        print(f"✗ Admin authentication failed")
        return False

def ensure_sample_data():
    """Ensure there's sample data for testing"""
    print("\n=== Ensuring Sample Data ===")
    
    # Ensure categories exist
    sample_categories = [
        'Academic Issues',
        'Hostel Facilities', 
        'Library Services',
        'Examination Issues',
        'Fee Related',
        'Infrastructure',
        'Faculty Issues',
        'Administrative',
    ]
    
    for cat_name in sample_categories:
        category, created = Category.objects.get_or_create(
            name=cat_name,
            defaults={'description': f'Category for {cat_name} related grievances'}
        )
        if created:
            print(f"✓ Created category: {cat_name}")
    
    print(f"✓ Total categories: {Category.objects.count()}")
    
    # Ensure at least one school and department exist
    school, created = School.objects.get_or_create(
        name='School of Engineering & Technology'
    )
    if created:
        print(f"✓ Created school: {school.name}")
    
    department, created = Department.objects.get_or_create(
        name='Computer Science Engineering',
        defaults={'school': school}
    )
    if created:
        print(f"✓ Created department: {department.name}")
    
    print(f"✓ Total schools: {School.objects.count()}")
    print(f"✓ Total departments: {Department.objects.count()}")
    print(f"✓ Total student profiles: {StudentProfile.objects.count()}")
    print(f"✓ Total grievances: {Grievance.objects.count()}")

def check_template_files():
    """Check if all required template files exist"""
    print("\n=== Checking Template Files ===")
    
    template_base = os.path.join(os.path.dirname(__file__), 'src', 'templates')
    
    required_templates = [
        'base.html',
        'admin_panel/dashboard_working.html',
        'authentication/login.html',
    ]
    
    all_exist = True
    for template in required_templates:
        template_path = os.path.join(template_base, template)
        if os.path.exists(template_path):
            print(f"✓ Template exists: {template}")
        else:
            print(f"✗ Template missing: {template}")
            all_exist = False
    
    return all_exist

def check_static_files():
    """Check if static files are properly configured"""
    print("\n=== Checking Static Files ===")
    
    static_base = os.path.join(os.path.dirname(__file__), 'src', 'static')
    
    required_static = [
        'css/style.css',
        'js/main.js',
    ]
    
    all_exist = True
    for static_file in required_static:
        static_path = os.path.join(static_base, static_file)
        if os.path.exists(static_path):
            print(f"✓ Static file exists: {static_file}")
        else:
            print(f"✗ Static file missing: {static_file}")
            all_exist = False
    
    return all_exist

def test_url_patterns():
    """Test all URL patterns work"""
    print("\n=== Testing URL Patterns ===")
    
    from django.urls import reverse
    
    try:
        # Test admin URLs
        dashboard_url = reverse('admin_panel:dashboard')
        grievances_url = reverse('admin_panel:grievance_list')
        students_url = reverse('admin_panel:student_list')
        reports_url = reverse('admin_panel:reports')
        categories_url = reverse('admin_panel:manage_categories')
        
        print(f"✓ Dashboard URL: {dashboard_url}")
        print(f"✓ Grievances URL: {grievances_url}")
        print(f"✓ Students URL: {students_url}")
        print(f"✓ Reports URL: {reports_url}")
        print(f"✓ Categories URL: {categories_url}")
        
        # Test auth URLs
        login_url = reverse('authentication:login_view')
        logout_url = reverse('authentication:logout_view')
        
        print(f"✓ Login URL: {login_url}")
        print(f"✓ Logout URL: {logout_url}")
        
        return True
        
    except Exception as e:
        print(f"✗ URL pattern error: {e}")
        return False

def main():
    """Run all fixes and checks"""
    print("Student Grievance Management System - Comprehensive Admin Panel Fix")
    print("=" * 80)
    
    fixes = [
        ensure_admin_user,
        ensure_sample_data,
        check_template_files,
        check_static_files,
        test_url_patterns,
    ]
    
    results = []
    for fix in fixes:
        try:
            result = fix()
            results.append(result)
        except Exception as e:
            print(f"✗ {fix.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE FIX SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r is not False)
    total = len(results)
    
    print(f"Checks Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        print("\n✅ Admin Panel Setup Complete:")
        print("- Admin user configured and verified")
        print("- Sample data created")
        print("- Templates and static files verified")
        print("- URL patterns validated")
        
        print("\n🚀 Ready to Use:")
        print("1. Start server: uv run python src/manage.py runserver")
        print("2. Login URL: http://127.0.0.1:8000/auth/login/")
        print("3. Admin Dashboard: http://127.0.0.1:8000/admin-panel/dashboard/")
        print("4. Credentials: admin@grievance.com / admin123")
        
    else:
        print("⚠️  Some issues remain. Check the errors above.")
        
        print("\n🔧 Manual Steps if needed:")
        print("1. Run: uv run python src/manage.py migrate")
        print("2. Run: uv run python src/manage.py collectstatic --noinput")
        print("3. Restart Django server")
        print("4. Clear browser cache")

if __name__ == '__main__':
    main()
