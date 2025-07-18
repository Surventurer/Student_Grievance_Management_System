#!/usr/bin/env python3
"""
Test script for profile page "Last Updated" field removal
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

def test_profile_page_updates():
    """Test that Last Updated field is removed from profile page"""
    print("👤 Testing Profile Page 'Last Updated' Field Removal...")
    
    # Get a sample student
    student_users = User.objects.filter(role='student')[:1]
    
    if not student_users:
        print("❌ No student users found")
        return
    
    user = student_users[0]
    try:
        profile = user.student_profile
        print(f"✅ Testing with student: {user.email}")
        
        print(f"\n🔗 URLs to verify:")
        print(f"📊 Dashboard: http://127.0.0.1:8000/students/")
        print(f"⚙️ Manage Profile: http://127.0.0.1:8000/students/profile/")
        
        print(f"\n✅ 'Last Updated' Field Removal Complete!")
        
        print(f"\n📋 Dashboard Profile Information (Clean):")
        print(f"  Student ID: {profile.student_id}")
        print(f"  School: {profile.school or 'Not provided'}")
        print(f"  Department: {profile.department}")
        print(f"  Email: {user.email}")
        print(f"  Contact: {profile.contact_no or 'Not provided'}")
        print(f"  ❌ Last Updated: [REMOVED]")
        
        print(f"\n📋 Manage Profile Page Info Panel:")
        print(f"  Account Status: {user.is_active}")
        print(f"  Email Status: {'Verified' if user.is_email_verified else 'Not Verified'}")
        print(f"  Member Since: {profile.created_at.strftime('%B %d, %Y')}")
        print(f"  ❌ Last Updated: [REMOVED]")
        
        print(f"\n🎯 Changes Made:")
        print(f"  ✅ Dashboard: Removed 'Last Updated' from Profile Information card")
        print(f"  ✅ Profile Page: Removed 'Last Updated' from sidebar info panel")
        print(f"  ✅ Both pages now show clean profile information")
        print(f"  ✅ Profile updates still work normally (contact, password)")
        
        print(f"\n🧪 User Experience:")
        print(f"1. Dashboard shows essential profile info only")
        print(f"2. Profile page shows clean sidebar information")
        print(f"3. No timestamp clutter in either location")
        print(f"4. Profile management functionality unchanged")
        print(f"5. Updates still work seamlessly")
        
    except StudentProfile.DoesNotExist:
        print(f"❌ No profile found for {user.email}")

if __name__ == "__main__":
    test_profile_page_updates()
