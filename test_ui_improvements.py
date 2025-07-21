"""
Test the improved user interface for create user form
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

def test_ui_improvements():
    """Test that the UI improvements work correctly"""
    print("🧪 Testing UI Improvements for Create User Form")
    print("=" * 60)
    
    # Get superadmin user
    superadmin = User.objects.filter(role='superadmin').first()
    if not superadmin:
        print("❌ No superadmin found")
        return
    
    client = Client()
    client.force_login(superadmin)
    
    # Test 1: Load the create user page
    print("\n📄 Test 1: Loading create user page...")
    try:
        response = client.get('/admin-panel/superadmin/users/create/')
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Page loads successfully")
            content = response.content.decode('utf-8')
            
            # Check for help text
            if 'Creating Users:' in content:
                print("✅ Help text is present")
            else:
                print("❌ Help text is missing")
            
            # Check for required field indicators
            if 'text-danger' in content and '*' in content:
                print("✅ Required field indicators are present")
            else:
                print("❌ Required field indicators are missing")
            
            # Check for form validation JavaScript
            if 'form validation' in content.lower() or 'addEventListener' in content:
                print("✅ JavaScript validation is present")
            else:
                print("❌ JavaScript validation is missing")
        else:
            print("❌ Page failed to load")
    except Exception as e:
        print(f"❌ Error loading page: {e}")
    
    # Test 2: Test form with missing fields (should show better error)
    print("\n❌ Test 2: Submitting incomplete form...")
    try:
        response = client.post('/admin-panel/superadmin/users/create/', {
            'email': 'test.incomplete@example.com',
            'role': 'student',
            'password': 'test123',
            'name': 'Incomplete Student',
            # Missing: student_id, school, department
        })
        
        if response.status_code == 200:  # Form returned with errors
            content = response.content.decode('utf-8')
            if 'fill in all required fields' in content.lower():
                print("✅ Improved error message is shown")
            else:
                print("❌ Standard error message (check message content)")
        elif response.status_code == 302:  # Unexpected success
            print("❌ Form submitted successfully (should have failed)")
            # Clean up if somehow created
            User.objects.filter(email='test.incomplete@example.com').delete()
        else:
            print(f"❌ Unexpected response status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing incomplete form: {e}")
    
    # Test 3: Test form with complete data (should succeed)
    print("\n✅ Test 3: Submitting complete form...")
    try:
        response = client.post('/admin-panel/superadmin/users/create/', {
            'email': 'test.ui.student@example.com',
            'role': 'student',
            'password': 'test123',
            'name': 'UI Test Student',
            'student_id': 'UITEST001',
            'school': 'Engineering College',
            'department': 'Computer Science',
            'contact_no': '1234567890'
        })
        
        if response.status_code == 302:  # Redirect indicates success
            user = User.objects.filter(email='test.ui.student@example.com').first()
            if user and hasattr(user, 'student_profile'):
                print("✅ Complete form submitted successfully")
                print(f"   Created user: {user.email}")
                print(f"   Student profile: {user.student_profile.name}")
                
                # Clean up
                user.delete()
                print("✅ Test user cleaned up")
            else:
                print("❌ User created but profile is missing")
        else:
            print(f"❌ Form submission failed with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing complete form: {e}")
    
    print("\n🎉 UI testing completed!")
    print("=" * 60)

if __name__ == '__main__':
    test_ui_improvements()
