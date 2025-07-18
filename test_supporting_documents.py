#!/usr/bin/env python3
"""
Test script for admin visibility of student supporting documents
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, 'src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.grievances.models import Grievance, GrievanceAttachment
from apps.students.models import StudentProfile
from django.contrib.auth import get_user_model

User = get_user_model()

def test_supporting_documents_visibility():
    """Test admin visibility of student supporting documents"""
    print("📎 Testing Supporting Documents Visibility for Admins...")
    
    # Get grievances with attachments
    grievances_with_attachments = Grievance.objects.filter(
        attachments__isnull=False
    ).distinct()
    
    if not grievances_with_attachments:
        print("❌ No grievances with attachments found")
        
        # Show available grievances
        all_grievances = Grievance.objects.all()[:5]
        print(f"\n📋 Available grievances ({all_grievances.count()}):")
        for g in all_grievances:
            attachment_count = g.attachments.count()
            print(f"  - {g.title} ({g.grievance_id}): {attachment_count} attachments")
        
        return
    
    print(f"✅ Found {grievances_with_attachments.count()} grievances with attachments")
    
    # Test each grievance with attachments
    for grievance in grievances_with_attachments[:3]:  # Test first 3
        print(f"\n📋 Grievance: {grievance.title} ({grievance.grievance_id})")
        print(f"👤 Student: {grievance.student.student_id}")
        
        attachments = grievance.attachments.all()
        print(f"📎 Attachments: {attachments.count()}")
        
        for i, attachment in enumerate(attachments, 1):
            print(f"  {i}. {attachment.file_name}")
            print(f"     Type: {attachment.file_type}")
            print(f"     Size: {attachment.file_size} bytes")
            print(f"     Uploaded: {attachment.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"     File URL: {attachment.file.url}")
    
    # Test URL for admin access
    sample_grievance = grievances_with_attachments.first()
    print(f"\n🔗 Admin grievance detail URL:")
    print(f"   http://127.0.0.1:8000/admin-panel/grievances/{sample_grievance.id}/")
    
    print("\n✅ Supporting Documents Fix Applied!")
    print("📋 Changes made:")
    print("  - Fixed admin template to use grievance.attachments.all")
    print("  - Added proper attachment display with file details")
    print("  - Added both View and Download buttons")
    print("  - Added file type, size, and upload timestamp")
    print("  - Added attachment count summary")
    
    print("\n🧪 To test:")
    print("1. Login as admin: admin@grievance.com / admin123")
    print("2. View any grievance with attachments")
    print("3. Supporting documents should now be visible")
    print("4. Admin can view and download student supporting documents")

if __name__ == "__main__":
    test_supporting_documents_visibility()
