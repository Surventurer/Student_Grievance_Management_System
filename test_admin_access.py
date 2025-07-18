#!/usr/bin/env python3
"""
Test script to verify admin access and admin panel functionality
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
from apps.students.models import StudentProfile

def test_admin_access():
    """Test admin user access"""
    print("=== Testing Admin Access ===")
    
    # Test admin user exists
    try:
        admin_user = User.objects.get(email='admin@grievance.com')
        print(f"✓ Admin user found: {admin_user.email}")
        print(f"✓ Is admin: {admin_user.is_admin}")
        print(f"✓ Is staff: {admin_user.is_staff}")
        print(f"✓ Is superuser: {admin_user.is_superuser}")
    except User.DoesNotExist:
        print("✗ Admin user not found!")
        return False
    
    # Test authentication
    user = authenticate(email='admin@grievance.com', password='admin123')
    if user:
        print(f"✓ Authentication successful for {user.email}")
    else:
        print("✗ Authentication failed!")
        return False
    
    return True

def test_database_queries():
    """Test database queries used in admin dashboard"""
    print("\n=== Testing Database Queries ===")
    
    try:
        # Test basic model counts
        total_users = User.objects.count()
        total_grievances = Grievance.objects.count()
        total_categories = Category.objects.count()
        total_students = StudentProfile.objects.count()
        
        print(f"✓ Total users: {total_users}")
        print(f"✓ Total grievances: {total_grievances}")
        print(f"✓ Total categories: {total_categories}")
        print(f"✓ Total student profiles: {total_students}")
        
        # Test grievance status counts
        pending = Grievance.objects.filter(status='pending').count()
        resolved = Grievance.objects.filter(status='resolved').count()
        rejected = Grievance.objects.filter(status='rejected').count()
        
        print(f"✓ Pending grievances: {pending}")
        print(f"✓ Resolved grievances: {resolved}")
        print(f"✓ Rejected grievances: {rejected}")
        
        # Test related queries
        recent_grievances = Grievance.objects.select_related('student', 'category').order_by('-submitted_at')[:5]
        print(f"✓ Recent grievances query successful: {len(list(recent_grievances))} items")
        
        return True
        
    except Exception as e:
        print(f"✗ Database query error: {e}")
        return False

def main():
    """Main test function"""
    print("Student Grievance Management System - Admin Access Test")
    print("=" * 60)
    
    admin_ok = test_admin_access()
    db_ok = test_database_queries()
    
    print("\n=== Test Results ===")
    if admin_ok and db_ok:
        print("✓ All tests passed! Admin panel should work correctly.")
        print("\nAdmin Login Credentials:")
        print("Email: admin@grievance.com")
        print("Password: admin123")
        print("URL: http://127.0.0.1:8000/admin/dashboard/")
    else:
        print("✗ Some tests failed. Check the errors above.")

if __name__ == '__main__':
    main()
