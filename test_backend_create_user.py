"""
Test the create user functionality with direct form submissions
"""
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from apps.students.models import AdminProfile, StudentProfile
from django.db import transaction

def test_create_user_backend():
    """Test the create user functionality directly"""
    print("🧪 Testing Create User Backend Logic")
    print("=" * 60)
    
    initial_user_count = User.objects.count()
    print(f"📊 Initial user count: {initial_user_count}")
    
    # Test 1: Create a student user
    print("\n👨‍🎓 Test 1: Creating Student User...")
    try:
        with transaction.atomic():
            user = User.objects.create(
                email='test.student@example.com',
                role='student',
                is_staff=False,
                is_email_verified=True,
                is_active=True
            )
            user.set_password('student123')
            user.save()
            
            StudentProfile.objects.create(
                user=user,
                name='Test Student',
                student_id='TEST001',
                school='Test School',
                department='Computer Science',
                contact_no='1234567890'
            )
            
            print("✅ Student user created successfully")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role}")
            print(f"   Profile: {user.student_profile.name} ({user.student_profile.student_id})")
            
    except Exception as e:
        print(f"❌ Error creating student: {e}")
    
    # Test 2: Create an admin user
    print("\n👨‍💼 Test 2: Creating Admin User...")
    try:
        with transaction.atomic():
            user = User.objects.create(
                email='test.admin@example.com',
                role='admin',
                is_staff=True,
                is_email_verified=True,
                is_active=True
            )
            user.set_password('admin123')
            user.save()
            
            AdminProfile.objects.create(
                user=user,
                role_level='admin',
                department='Computer Science',
                employee_id='TESTADM001',
                phone='9876543210',
                office_location='Admin Building'
            )
            
            print("✅ Admin user created successfully")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role}")
            print(f"   Profile: {user.admin_profile.employee_id} ({user.admin_profile.role_level})")
            
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
    
    # Test 3: Create an officer user
    print("\n👮‍♂️ Test 3: Creating Officer User...")
    try:
        with transaction.atomic():
            user = User.objects.create(
                email='test.officer@example.com',
                role='officer',
                is_staff=True,
                is_email_verified=True,
                is_active=True
            )
            user.set_password('officer123')
            user.save()
            
            AdminProfile.objects.create(
                user=user,
                role_level='officer',
                department='Business Administration',
                employee_id='TESTOFF001',
                phone='5555555555',
                office_location='Officer Building'
            )
            
            print("✅ Officer user created successfully")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role}")
            print(f"   Profile: {user.admin_profile.employee_id} ({user.admin_profile.role_level})")
            
    except Exception as e:
        print(f"❌ Error creating officer: {e}")
    
    final_user_count = User.objects.count()
    print(f"\n📊 Final user count: {final_user_count}")
    print(f"📈 Users created: {final_user_count - initial_user_count}")
    
    # Verify the users exist and can be retrieved
    print("\n🔍 Verification:")
    test_users = ['test.student@example.com', 'test.admin@example.com', 'test.officer@example.com']
    for email in test_users:
        try:
            user = User.objects.get(email=email)
            print(f"✅ {email}: {user.role}")
            
            # Check profile
            if user.role == 'student' and hasattr(user, 'student_profile'):
                print(f"   Student Profile: {user.student_profile.name}")
            elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
                print(f"   Admin Profile: {user.admin_profile.employee_id}")
        except User.DoesNotExist:
            print(f"❌ {email}: Not found")
    
    print("\n🧹 Cleaning up test users...")
    User.objects.filter(email__in=test_users).delete()
    print("✅ Test users cleaned up")
    
    print("\n🎉 Backend test completed!")
    print("=" * 60)

if __name__ == '__main__':
    test_create_user_backend()
