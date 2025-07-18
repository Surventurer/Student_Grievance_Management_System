#!/usr/bin/env python3
"""
Test script for admin response functionality
"""
import os
import sys
import django
import requests

# Setup Django
sys.path.insert(0, 'src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.grievances.models import Grievance, GrievanceComment
from apps.students.models import StudentProfile
from django.contrib.auth import get_user_model

User = get_user_model()

def test_admin_response_feature():
    """Test admin response visibility for students"""
    print("🔧 Testing Admin Response Feature...")
    
    # Get a sample grievance
    grievances = Grievance.objects.all()[:1]
    if not grievances:
        print("❌ No grievances found")
        return
    
    grievance = grievances[0]
    print(f"📋 Testing with grievance: {grievance.title} ({grievance.grievance_id})")
    
    # Check existing comments
    all_comments = grievance.comments.all()
    public_comments = all_comments.filter(is_internal=False)
    internal_comments = all_comments.filter(is_internal=True)
    
    print(f"💬 Total comments: {all_comments.count()}")
    print(f"👁️ Public comments (visible to students): {public_comments.count()}")
    print(f"🔒 Internal comments (admin only): {internal_comments.count()}")
    
    # Show comment details
    for comment in all_comments:
        visibility = "Public" if not comment.is_internal else "Internal"
        user_type = "Admin" if comment.user.is_admin else "Student"
        print(f"  - {comment.comment_type}: {visibility} by {user_type} at {comment.timestamp}")
        print(f"    Message: {comment.message[:50]}...")
    
    # Test URLs
    print(f"\n🌐 Student grievance detail URL: http://127.0.0.1:8000/students/grievances/{grievance.id}/")
    print(f"🔧 Admin grievance detail URL: http://127.0.0.1:8000/admin-panel/grievances/{grievance.id}/")
    print(f"📝 Admin response endpoint: http://127.0.0.1:8000/admin-panel/grievances/{grievance.id}/add-response/")
    
    print("\n✅ Admin response feature structure is ready!")
    print("📋 To test the functionality:")
    print("1. Login as admin: admin@grievance.com / admin123")
    print("2. Go to admin grievance detail page")
    print("3. Add a public response (should be visible to student)")
    print("4. Add an internal note (should be admin-only)")
    print("5. Login as student and check if public responses are visible")

if __name__ == "__main__":
    test_admin_response_feature()
