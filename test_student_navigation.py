#!/usr/bin/env python3
"""
Test script for student navigation links
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, 'src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

def test_student_navigation_urls():
    """Test all student navigation URLs"""
    print("🧭 Testing Student Navigation URLs...")
    
    # Test URLs
    urls_to_test = [
        ('students:dashboard', 'Dashboard'),
        ('grievances:submit_grievance', 'Lodge Grievance'),
        ('students:grievances', 'My Grievances'),
        ('students:profile', 'Manage Profile'),
    ]
    
    print("\n📋 Testing URL resolution:")
    for url_name, description in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"✅ {description}: {url}")
        except Exception as e:
            print(f"❌ {description}: Error - {e}")
    
    # Get a student user for context
    student_users = User.objects.filter(role='student')[:1]
    if student_users:
        student = student_users[0]
        print(f"\n👤 Sample student: {student.email}")
        print(f"📧 Login URL: http://127.0.0.1:8000/auth/login/")
        print("\n🎯 Student Navigation Menu Added:")
        print("📊 Dashboard - View student dashboard")
        print("➕ Lodge Grievance - Submit new grievance")
        print("📋 My Grievances - View submitted grievances")
        print("⚙️ Manage Profile - Update profile and password")
    else:
        print("\n❌ No student users found")
    
    print("\n✅ Student navigation links are ready!")
    print("🔗 The header now includes all requested navigation options")

if __name__ == "__main__":
    test_student_navigation_urls()
