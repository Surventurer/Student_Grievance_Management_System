#!/usr/bin/env python3
"""
Comprehensive admin panel diagnostic and fix script
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
from django.urls import reverse
from django.test import Client
from django.conf import settings
from apps.authentication.models import User
from apps.grievances.models import Grievance, Category
from apps.students.models import StudentProfile

def test_url_configuration():
    """Test URL configuration"""
    print("=== Testing URL Configuration ===")
    
    try:
        # Test admin panel URLs
        admin_dashboard_url = reverse('admin_panel:dashboard')
        print(f"✓ Admin dashboard URL: {admin_dashboard_url}")
        
        admin_grievances_url = reverse('admin_panel:grievance_list')
        print(f"✓ Admin grievances URL: {admin_grievances_url}")
        
        auth_login_url = reverse('authentication:login_view')
        print(f"✓ Auth login URL: {auth_login_url}")
        
        return True
    except Exception as e:
        print(f"✗ URL configuration error: {e}")
        return False

def test_admin_user():
    """Test admin user functionality"""
    print("\n=== Testing Admin User ===")
    
    try:
        # Check if admin user exists
        admin_user = User.objects.filter(email='admin@grievance.com').first()
        if admin_user:
            print(f"✓ Admin user exists: {admin_user.email}")
            print(f"✓ Role: {admin_user.role}")
            print(f"✓ Is admin: {admin_user.is_admin}")
            print(f"✓ Is staff: {admin_user.is_staff}")
            print(f"✓ Is active: {admin_user.is_active}")
            print(f"✓ Email verified: {admin_user.is_email_verified}")
            
            # Test authentication
            authenticated_user = authenticate(email='admin@grievance.com', password='admin123')
            if authenticated_user:
                print(f"✓ Authentication successful")
                return True
            else:
                print(f"✗ Authentication failed")
                return False
        else:
            print("✗ Admin user not found")
            return False
            
    except Exception as e:
        print(f"✗ Admin user test error: {e}")
        return False

def test_database_queries():
    """Test database queries used in admin panel"""
    print("\n=== Testing Database Queries ===")
    
    try:
        # Basic counts
        user_count = User.objects.count()
        grievance_count = Grievance.objects.count()
        category_count = Category.objects.count()
        student_count = StudentProfile.objects.count()
        
        print(f"✓ Users: {user_count}")
        print(f"✓ Grievances: {grievance_count}")
        print(f"✓ Categories: {category_count}")
        print(f"✓ Student Profiles: {student_count}")
        
        # Status-based counts
        pending = Grievance.objects.filter(status='pending').count()
        resolved = Grievance.objects.filter(status='resolved').count()
        rejected = Grievance.objects.filter(status='rejected').count()
        
        print(f"✓ Pending: {pending}")
        print(f"✓ Resolved: {resolved}")
        print(f"✓ Rejected: {rejected}")
        
        # Test recent grievances query
        recent_grievances = Grievance.objects.select_related('student', 'category').order_by('-submitted_at')[:5]
        print(f"✓ Recent grievances query successful: {len(list(recent_grievances))} items")
        
        # Test category stats
        from django.db.models import Count
        category_stats = Category.objects.annotate(count=Count('grievances')).order_by('-count')[:5]
        print(f"✓ Category stats query successful: {len(list(category_stats))} items")
        
        return True
        
    except Exception as e:
        print(f"✗ Database query error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_rendering():
    """Test template rendering"""
    print("\n=== Testing Template Rendering ===")
    
    try:
        from django.template.loader import get_template
        
        # Test base template
        base_template = get_template('base.html')
        print("✓ Base template loads successfully")
        
        # Test admin dashboard template
        dashboard_template = get_template('admin_panel/dashboard.html')
        print("✓ Admin dashboard template loads successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Template rendering error: {e}")
        return False

def test_admin_panel_access():
    """Test admin panel access via client"""
    print("\n=== Testing Admin Panel Access ===")
    
    try:
        client = Client()
        
        # Test login page
        login_response = client.get('/auth/login/')
        print(f"✓ Login page accessible: {login_response.status_code}")
        
        # Test admin dashboard without login (should redirect)
        dashboard_response = client.get('/admin-panel/dashboard/')
        print(f"✓ Dashboard redirect works: {dashboard_response.status_code}")
        
        # Test login with admin credentials
        login_data = {
            'email': 'admin@grievance.com',
            'password': 'admin123'
        }
        login_post = client.post('/auth/login/', login_data)
        print(f"✓ Admin login attempt: {login_post.status_code}")
        
        # Test dashboard access after login
        if login_post.status_code in [200, 302]:  # Success or redirect
            dashboard_logged_in = client.get('/admin-panel/dashboard/')
            print(f"✓ Dashboard after login: {dashboard_logged_in.status_code}")
        
        return True
        
    except Exception as e:
        print(f"✗ Admin panel access error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_settings_configuration():
    """Test Django settings"""
    print("\n=== Testing Settings Configuration ===")
    
    try:
        print(f"✓ DEBUG: {settings.DEBUG}")
        print(f"✓ LOGIN_URL: {getattr(settings, 'LOGIN_URL', 'NOT SET')}")
        print(f"✓ STATIC_URL: {settings.STATIC_URL}")
        print(f"✓ AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings error: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("Student Grievance Management System - Admin Panel Diagnostics")
    print("=" * 70)
    
    tests = [
        test_settings_configuration,
        test_url_configuration,
        test_admin_user,
        test_database_queries,
        test_template_rendering,
        test_admin_panel_access,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Admin panel should be working correctly.")
        print("\nAccess Information:")
        print("- Login URL: http://127.0.0.1:8000/auth/login/")
        print("- Admin Dashboard: http://127.0.0.1:8000/admin-panel/dashboard/")
        print("- Credentials: admin@grievance.com / admin123")
    else:
        print("⚠️  Some tests failed. Check the errors above for details.")
        
        print("\nTroubleshooting Steps:")
        print("1. Ensure the Django server is running")
        print("2. Check database migrations are applied")
        print("3. Verify admin user is created with correct role")
        print("4. Check template files exist and are valid")
        print("5. Verify URL patterns are correctly configured")

if __name__ == '__main__':
    main()
