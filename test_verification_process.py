"""
Complete Email Verification Test - Simulates the student verification process
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

def simulate_email_verification_process():
    """Simulate the complete email verification process"""
    
    print("🔄 Simulating Email Verification Process")
    print("=" * 50)
    
    # Find unverified student
    try:
        student_user = User.objects.filter(
            role='student',
            is_email_verified=False
        ).select_related('student_profile').first()
        
        if not student_user:
            print("❌ No unverified students found.")
            return
            
        student_profile = student_user.student_profile
        student_id = student_profile.student_id
        
        print(f"👤 Student: {student_profile.name}")
        print(f"🆔 Student ID: {student_id}")
        print(f"📧 Email: {student_user.email}")
        
        # Find valid OTP
        verification = EmailVerification.objects.filter(
            user=student_user,
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification or verification.is_expired:
            print("❌ No valid OTP found.")
            return
            
        otp = verification.otp
        print(f"🔑 OTP: {otp}")
        
        # Simulate verification process
        print("\n🔄 Simulating verification process...")
        
        # Step 1: Check if student exists
        try:
            found_profile = StudentProfile.objects.select_related('user').get(student_id=student_id)
            print("✅ Step 1: Student ID found")
        except StudentProfile.DoesNotExist:
            print("❌ Step 1: Student ID not found")
            return
            
        # Step 2: Check if already verified
        if found_profile.user.is_email_verified:
            print("ℹ️ Step 2: Email already verified")
            return
        else:
            print("✅ Step 2: Email needs verification")
            
        # Step 3: Find valid OTP
        valid_verification = EmailVerification.objects.filter(
            user=found_profile.user,
            otp=otp,
            is_used=False
        ).order_by('-created_at').first()
        
        if not valid_verification:
            print("❌ Step 3: Invalid OTP")
            return
        else:
            print("✅ Step 3: Valid OTP found")
            
        # Step 4: Check expiration
        if valid_verification.is_expired:
            print("❌ Step 4: OTP expired")
            return
        else:
            print("✅ Step 4: OTP not expired")
            
        # Step 5: Mark as verified (simulation - not actually updating)
        print("✅ Step 5: Ready to mark email as verified")
        
        print(f"\n🎉 Verification process would succeed for:")
        print(f"   Student: {student_profile.name}")
        print(f"   Student ID: {student_id}")
        print(f"   OTP: {otp}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def show_verification_instructions():
    """Show instructions for testing"""
    print("\n📝 Testing Instructions")
    print("=" * 30)
    print("1. Go to: http://127.0.0.1:8000/auth/verify-student-email/")
    print("2. Enter the Student ID and OTP shown above")
    print("3. Click 'Verify Email'")
    print("4. Should redirect to login with success message")
    print("5. Try logging in with the verified student credentials")

if __name__ == "__main__":
    if simulate_email_verification_process():
        show_verification_instructions()
