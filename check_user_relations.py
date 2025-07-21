#!/usr/bin/env python3
"""
Check user relationships and foreign key constraints
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, r'c:\Users\Abhinav\Desktop\Student_Grievance_Management_System\src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from apps.students.models import StudentProfile, AdminProfile
from apps.grievances.models import Grievance
from apps.notifications.models import ReadNotification

def check_user_relationships():
    """Check what relationships exist for users"""
    print("🔍 Checking User Relationships and Foreign Key Constraints")
    print("=" * 60)
    
    users = User.objects.all()
    print(f"📊 Total users in database: {users.count()}")
    
    for user in users[:5]:  # Check first 5 users
        print(f"\n👤 User: {user.email} (ID: {user.id}, Role: {user.role})")
        
        # Check student profile
        try:
            if hasattr(user, 'student_profile'):
                print(f"   📚 Student Profile: {user.student_profile}")
            else:
                print("   📚 No Student Profile")
        except:
            print("   📚 No Student Profile (exception)")
            
        # Check admin profile
        try:
            if hasattr(user, 'admin_profile'):
                print(f"   👨‍💼 Admin Profile: {user.admin_profile}")
            else:
                print("   👨‍💼 No Admin Profile")
        except:
            print("   👨‍💼 No Admin Profile (exception)")
            
        # Check grievances
        try:
            if hasattr(user, 'student_profile') and user.student_profile:
                grievances = Grievance.objects.filter(student=user.student_profile)
                print(f"   📋 Grievances created: {grievances.count()}")
            else:
                print("   📋 No grievances (not a student)")
        except Exception as e:
            print(f"   📋 Error checking grievances: {e}")
        
        # Check audit logs
        from apps.grievances.models import AuditLog
        audit_logs = AuditLog.objects.filter(user=user)
        print(f"   📝 Audit logs: {audit_logs.count()}")
        
        # Check notifications
        notifications = ReadNotification.objects.filter(student=user)
        print(f"   🔔 Read notifications: {notifications.count()}")

def test_single_user_deletion():
    """Test deleting a single user to see the exact error"""
    print("\n🧪 Testing Single User Deletion")
    print("=" * 40)
    
    # Find a user that's not a superadmin and not critical
    test_user = User.objects.filter(role='student').exclude(email='admin@example.com').first()
    
    if test_user:
        print(f"🎯 Testing deletion of: {test_user.email} (ID: {test_user.id})")
        
        try:
            # Store ID before deletion
            user_id = test_user.id
            user_email = test_user.email
            
            # Try to delete
            test_user.delete()
            print(f"✅ Successfully deleted user {user_email} (ID: {user_id})")
            
        except Exception as e:
            print(f"❌ Failed to delete user: {e}")
            print(f"   Error type: {type(e).__name__}")
            
            # Let's check what's preventing deletion
            print("\n🔍 Checking what's blocking deletion...")
            
            # Check related objects
            if hasattr(test_user, '_meta'):
                for field in test_user._meta.get_fields():
                    if field.related_model and hasattr(field, 'related_name'):
                        try:
                            related_objects = getattr(test_user, field.related_name).all()
                            if related_objects.exists():
                                print(f"   🔗 {field.related_name}: {related_objects.count()} objects")
                        except:
                            pass
    else:
        print("❌ No suitable test user found")

if __name__ == "__main__":
    try:
        check_user_relationships()
        test_single_user_deletion()
    except Exception as e:
        print(f"❌ Script error: {e}")
        import traceback
        traceback.print_exc()
