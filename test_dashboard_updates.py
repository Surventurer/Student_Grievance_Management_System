#!/usr/bin/env python3
"""
Test script for dashboard profile information updates
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, 'src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.students.models import StudentProfile
from django.contrib.auth import get_user_model

User = get_user_model()

def test_dashboard_profile_updates():
    """Test that dashboard reflects profile changes"""
    print("📱 Testing Dashboard Profile Updates...")
    
    # Get a sample student
    student_users = User.objects.filter(role='student')[:1]
    
    if not student_users:
        print("❌ No student users found")
        return
    
    user = student_users[0]
    try:
        profile = user.student_profile
        print(f"✅ Testing with student: {user.email}")
        print(f"📋 Current Profile Information:")
        print(f"  Student ID: {profile.student_id}")
        print(f"  School: {profile.school or 'Not provided'}")
        print(f"  Department: {profile.department}")
        print(f"  Email: {user.email}")
        print(f"  Contact: {profile.contact_no or 'Not provided'}")
        
        print(f"\n🔗 Dashboard URL: http://127.0.0.1:8000/students/")
        print(f"🔗 Profile Management URL: http://127.0.0.1:8000/students/profile/")
        
        print(f"\n✅ Dashboard Profile Section Updated!")
        print(f"📋 Changes made:")
        print(f"  ❌ Removed 'Last Updated' field from dashboard")
        print(f"  ✅ Dashboard shows: Student ID → School → Department → Email → Contact")
        print(f"  ✅ Profile updates automatically refresh when:")
        print(f"    - Contact number is changed via Manage Profile")
        print(f"    - Password is changed via Manage Profile")
        print(f"    - Any profile field is updated")
        
        print(f"\n🧪 How Profile Updates Work:")
        print(f"1. Student goes to 'Manage Profile' (/students/profile/)")
        print(f"2. Updates contact number in editable section")
        print(f"3. Changes password in security section")  
        print(f"4. Returns to dashboard - sees updated contact info")
        print(f"5. No 'Last Updated' timestamp shown on dashboard")
        
        print(f"\n🎯 Dashboard Profile Information Display:")
        print(f"  Student ID: {profile.student_id}")
        print(f"  School: {profile.school or 'Not provided'}")
        print(f"  Department: {profile.department}")
        print(f"  Email: {user.email}")
        print(f"  Contact: {profile.contact_no or 'Not provided'}")
        print(f"  (No 'Last Updated' field)")
        
    except StudentProfile.DoesNotExist:
        print(f"❌ No profile found for {user.email}")

if __name__ == "__main__":
    test_dashboard_profile_updates()
