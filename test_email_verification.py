"""
Test script to verify the email verification functionality for newly created students.
"""

import os
import sys
import django

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.students.models import StudentProfile
from apps.authentication.models import User, EmailVerification
from datetime import timedelta
from django.utils import timezone

def test_email_verification_workflow():
    """Test the complete email verification workflow"""
    
    print("🧪 Testing Email Verification Workflow")
    print("=" * 50)
    
    # Find a student user created by admin
    try:
        # Look for unverified student users
        unverified_students = User.objects.filter(
            role='student',
            is_email_verified=False
        ).select_related('student_profile')
        
        if not unverified_students.exists():
            print("❌ No unverified students found. Create a student through admin panel first.")
            return False
            
        student_user = unverified_students.first()
        student_profile = student_user.student_profile
        
        print(f"📧 Found unverified student: {student_profile.name}")
        print(f"📍 Student ID: {student_profile.student_id}")
        print(f"📧 Email: {student_user.email}")
        
        # Check if there's an OTP for this user
        verification = EmailVerification.objects.filter(
            user=student_user,
            is_used=False
        ).order_by('-created_at').first()
        
        if verification:
            print(f"🔑 Found OTP: {verification.otp}")
            print(f"⏰ Expires at: {verification.expires_at}")
            print(f"🔒 Is expired: {verification.is_expired}")
            print(f"✅ Email verification ready for testing!")
            
            # Show verification URL
            print("\n🌐 Test URLs:")
            print("- Verification page: http://127.0.0.1:8000/auth/verify-student-email/")
            print("- Login page: http://127.0.0.1:8000/auth/login/")
            
            print(f"\n📋 Test Data:")
            print(f"Student ID: {student_profile.student_id}")
            print(f"OTP: {verification.otp}")
            
            return True
        else:
            print("❌ No OTP found. Create a new student through admin panel to generate OTP.")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_verification_statistics():
    """Show verification statistics"""
    print("\n📊 Email Verification Statistics")
    print("-" * 40)
    
    total_students = User.objects.filter(role='student').count()
    verified_students = User.objects.filter(role='student', is_email_verified=True).count()
    unverified_students = total_students - verified_students
    
    print(f"👥 Total Students: {total_students}")
    print(f"✅ Verified: {verified_students}")
    print(f"❌ Unverified: {unverified_students}")
    
    # Show recent OTPs
    recent_otps = EmailVerification.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).select_related('user__student_profile').order_by('-created_at')[:5]
    
    if recent_otps.exists():
        print(f"\n🕒 Recent OTPs (Last 24 hours):")
        for otp in recent_otps:
            student_name = otp.user.student_profile.name if hasattr(otp.user, 'student_profile') else 'Unknown'
            status = "Used" if otp.is_used else "Active" if not otp.is_expired else "Expired"
            print(f"  - {student_name}: {otp.otp} ({status})")

if __name__ == "__main__":
    test_email_verification_workflow()
    show_verification_statistics()
