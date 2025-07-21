"""
Test the updated create user functionality with required fields
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
from apps.students.models import Department, School

def test_create_user_form():
    """Test the create user form with required fields"""
    print("🧪 Testing Create User Form with Required Fields")
    print("=" * 60)
    
    # Get superadmin user
    superadmin = User.objects.filter(role='superadmin').first()
    if not superadmin:
        print("❌ No superadmin found")
        return
    
    client = Client()
    client.force_login(superadmin)
    
    # Test 1: Create student without school (should fail)
    print("\n❌ Test 1: Student without school...")
    response = client.post('/admin-panel/superadmin/users/create/', {
        'email': 'test.nostudent@example.com',
        'role': 'student',
        'password': 'test123',
        'name': 'Test Student',
        'student_id': 'NOSCHOOL001',
        # 'school': '',  # Missing school
        'department': 'Computer Science',
        'contact_no': '1234567890'
    })
    
    if response.status_code == 302:  # Redirect indicates success (unexpected)
        print("❌ Student created without school (unexpected)")
        # Clean up
        User.objects.filter(email='test.nostudent@example.com').delete()
    else:
        print("✅ Correctly rejected student without school")
    
    # Test 2: Create admin without department (should fail)
    print("\n❌ Test 2: Admin without department...")
    response = client.post('/admin-panel/superadmin/users/create/', {
        'email': 'test.noadmin@example.com',
        'role': 'admin',
        'password': 'test123',
        'employee_id': 'NODEPT001',
        # 'department': '',  # Missing department
        'phone': '9876543210'
    })
    
    if response.status_code == 302:  # Redirect indicates success (unexpected)
        print("❌ Admin created without department (unexpected)")
        # Clean up
        User.objects.filter(email='test.noadmin@example.com').delete()
    else:
        print("✅ Correctly rejected admin without department")
    
    # Test 3: Create student with all required fields (should succeed)
    print("\n✅ Test 3: Complete student...")
    response = client.post('/admin-panel/superadmin/users/create/', {
        'email': 'test.complete.student@example.com',
        'role': 'student',
        'password': 'test123',
        'name': 'Complete Student',
        'student_id': 'COMPLETE001',
        'school': 'Engineering College',
        'department': 'Computer Science',
        'contact_no': '1234567890'
    })
    
    if response.status_code == 302:  # Redirect indicates success
        user = User.objects.filter(email='test.complete.student@example.com').first()
        if user and hasattr(user, 'student_profile'):
            print("✅ Student created successfully")
            print(f"   Email: {user.email}")
            print(f"   School: {user.student_profile.school}")
            print(f"   Department: {user.student_profile.department}")
        else:
            print("❌ Student user created but no profile found")
    else:
        print("❌ Failed to create complete student")
    
    # Test 4: Create admin with all required fields (should succeed)
    print("\n✅ Test 4: Complete admin...")
    response = client.post('/admin-panel/superadmin/users/create/', {
        'email': 'test.complete.admin@example.com',
        'role': 'admin',
        'password': 'test123',
        'employee_id': 'COMPLETE001',
        'department': 'Computer Science',
        'phone': '9876543210',
        'office_location': 'Admin Building'
    })
    
    if response.status_code == 302:  # Redirect indicates success
        user = User.objects.filter(email='test.complete.admin@example.com').first()
        if user and hasattr(user, 'admin_profile'):
            print("✅ Admin created successfully")
            print(f"   Email: {user.email}")
            print(f"   Department: {user.admin_profile.department}")
            print(f"   Employee ID: {user.admin_profile.employee_id}")
        else:
            print("❌ Admin user created but no profile found")
    else:
        print("❌ Failed to create complete admin")
    
    # Clean up test users
    print("\n🧹 Cleaning up...")
    test_emails = [
        'test.complete.student@example.com',
        'test.complete.admin@example.com'
    ]
    deleted_count = User.objects.filter(email__in=test_emails).count()
    User.objects.filter(email__in=test_emails).delete()
    print(f"✅ Cleaned up {deleted_count} test users")
    
    print("\n🎉 Form test completed!")
    print("=" * 60)

if __name__ == '__main__':
    test_create_user_form()
