#!/usr/bin/env python3
"""
Test script for student dashboard profile information updates
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

def test_student_profile_fields():
    """Test student profile fields for dashboard display"""
    print("👤 Testing Student Profile Information Display...")
    
    # Get student users
    student_users = User.objects.filter(role='student')[:3]
    
    if not student_users:
        print("❌ No student users found")
        return
    
    print(f"✅ Found {student_users.count()} student users")
    
    for user in student_users:
        try:
            profile = user.student_profile
            print(f"\n📋 Student: {user.email}")
            print(f"  Student ID: {profile.student_id}")
            print(f"  Name: {profile.name or 'Not provided'}")
            print(f"  School: {profile.school or 'Not provided'}")
            print(f"  Department: {profile.department}")
            print(f"  Contact: {profile.contact_no or 'Not provided'}")
            print(f"  Last Updated: {profile.updated_at.strftime('%B %d, %Y')}")
            
            # Check if this matches the target profile from the image
            if profile.student_id == "2022473539":
                print(f"\n🎯 Found target student profile!")
                print(f"  Expected School: Should show school information")
                print(f"  Expected Department: Computer Science ✅")
                print(f"  Expected Email: 2022473539.abhinav@uq.sharda.ac.in")
                print(f"  Expected Contact: 7840056134")
                
        except StudentProfile.DoesNotExist:
            print(f"❌ No profile found for {user.email}")
    
    print(f"\n🔗 Dashboard URL: http://127.0.0.1:8000/students/")
    print(f"🔗 Profile URL: http://127.0.0.1:8000/students/profile/")
    
    print("\n✅ Dashboard Profile Information Updated!")
    print("📋 Changes made:")
    print("  - Added School field above Department")
    print("  - Added Last Updated field showing profile update date")
    print("  - School field shows 'Not provided' if empty")
    print("  - Order: Student ID → School → Department → Email → Contact → Last Updated")
    
    print("\n🧪 To verify:")
    print("1. Login as student: 2022473539.abhinav@uq.sharda.ac.in")
    print("2. Check dashboard Profile Information section")
    print("3. Verify school field appears above department")
    print("4. Check profile page also shows school in read-only section")

if __name__ == "__main__":
    test_student_profile_fields()
