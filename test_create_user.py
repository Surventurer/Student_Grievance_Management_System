"""
Test script to verify the create user functionality
"""
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from apps.authentication.models import User
from apps.students.models import AdminProfile, StudentProfile

def test_create_user_functionality():
    """Test the create user functionality"""
    print("🧪 Testing Create User Functionality")
    print("=" * 60)
    
    # Get the superadmin user
    try:
        superadmin = User.objects.filter(role='superadmin').first()
        if not superadmin:
            print("❌ No superadmin found. Please run the setup script first.")
            return
        
        client = Client()
        login_success = client.login(username=superadmin.email, password='admin123')
        
        if not login_success:
            print("❌ Could not login as superadmin")
            return
        
        print(f"✅ Logged in as superadmin: {superadmin.email}")
        
        # Test the create user page loads
        response = client.get(reverse('admin_panel:create_user'))
        print(f"📄 Create user page status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Create user page loads successfully")
        else:
            print("❌ Create user page failed to load")
            return
        
        # Test creating a student user
        print("\n👨‍🎓 Testing Student User Creation...")
        initial_user_count = User.objects.count()
        
        student_data = {
            'email': 'test.student@example.com',
            'role': 'student',
            'password': 'student123',
            'name': 'Test Student',
            'student_id': 'TEST001',
            'department': 'Computer Science',
            'school': 'School of Computer Science',
            'contact_no': '1234567890'
        }
        
        response = client.post(reverse('admin_panel:create_user'), student_data)
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 302:  # Redirect after successful creation
            print("✅ Student user creation successful (redirected)")
            
            # Verify user was created
            if User.objects.count() == initial_user_count + 1:
                print("✅ User count increased by 1")
                
                # Check if student profile was created
                test_user = User.objects.get(email='test.student@example.com')
                if hasattr(test_user, 'student_profile'):
                    profile = test_user.student_profile
                    print(f"✅ Student profile created: {profile.name} ({profile.student_id})")
                else:
                    print("❌ Student profile not created")
            else:
                print("❌ User count did not increase")
        else:
            print("❌ Student user creation failed")
        
        # Test creating an admin user
        print("\n👨‍💼 Testing Admin User Creation...")
        initial_user_count = User.objects.count()
        
        admin_data = {
            'email': 'test.admin@example.com',
            'role': 'admin',
            'password': 'admin123',
            'department': 'Computer Science',
            'employee_id': 'TESTADM001',
            'phone': '9876543210',
            'office_location': 'Admin Building'
        }
        
        response = client.post(reverse('admin_panel:create_user'), admin_data)
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 302:  # Redirect after successful creation
            print("✅ Admin user creation successful (redirected)")
            
            # Verify user was created
            if User.objects.count() == initial_user_count + 1:
                print("✅ User count increased by 1")
                
                # Check if admin profile was created
                test_user = User.objects.get(email='test.admin@example.com')
                if hasattr(test_user, 'admin_profile'):
                    profile = test_user.admin_profile
                    print(f"✅ Admin profile created: {profile.employee_id} ({profile.role_level})")
                else:
                    print("❌ Admin profile not created")
            else:
                print("❌ User count did not increase")
        else:
            print("❌ Admin user creation failed")
        
        # Test superadmin cannot create another superadmin
        print("\n🚫 Testing Superadmin Creation Prevention...")
        superadmin_data = {
            'email': 'test.superadmin@example.com',
            'role': 'superadmin',
            'password': 'super123',
            'employee_id': 'TESTSUPER001'
        }
        
        response = client.post(reverse('admin_panel:create_user'), superadmin_data)
        if response.status_code == 302 and not User.objects.filter(email='test.superadmin@example.com').exists():
            print("✅ Superadmin creation correctly prevented")
        else:
            print("❌ Superadmin creation was not prevented")
        
        print("\n🎉 Create user functionality test completed!")
        print("=" * 60)
        
        # Clean up test users
        print("\n🧹 Cleaning up test users...")
        User.objects.filter(email__in=['test.student@example.com', 'test.admin@example.com']).delete()
        print("✅ Test users cleaned up")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_create_user_functionality()
