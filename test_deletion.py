#!/usr/bin/env python3
"""
Test direct deletion with foreign key handling
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, r'c:\Users\Abhinav\Desktop\Student_Grievance_Management_System\src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from django.db import connection, transaction

def test_deletion_with_pragma():
    """Test deletion with foreign key pragma"""
    print("🧪 Testing User Deletion with PRAGMA foreign_keys = OFF")
    print("=" * 60)
    
    # Find a test user
    test_user = User.objects.filter(role='student', email__contains='student2').first()
    
    if not test_user:
        print("❌ No suitable test user found")
        return
    
    print(f"🎯 Testing deletion of: {test_user.email} (ID: {test_user.id})")
    
    try:
        with transaction.atomic():
            # Disable foreign key checks
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF")
            
            try:
                # Store info before deletion
                user_info = {
                    'id': test_user.id,
                    'email': test_user.email,
                    'role': test_user.role
                }
                
                print(f"   📊 Before deletion:")
                if hasattr(test_user, 'student_profile') and test_user.student_profile:
                    grievance_count = test_user.student_profile.grievances.count()
                    print(f"     - Grievances: {grievance_count}")
                
                # Try to delete
                test_user.delete()
                
                print(f"✅ Successfully deleted user: {user_info['email']}")
                print(f"   📊 User ID {user_info['id']} has been removed from database")
                
            finally:
                # Re-enable foreign key checks
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = ON")
                    
    except Exception as e:
        print(f"❌ Still failed to delete user: {e}")
        print(f"   Error type: {type(e).__name__}")

def show_remaining_users():
    """Show remaining users after test"""
    print(f"\n📊 Remaining users: {User.objects.count()}")
    for user in User.objects.all()[:5]:
        print(f"   - {user.email} (ID: {user.id}, Role: {user.role})")

if __name__ == "__main__":
    try:
        test_deletion_with_pragma()
        show_remaining_users()
    except Exception as e:
        print(f"❌ Script error: {e}")
        import traceback
        traceback.print_exc()
