"""
Test script to validate the web interface works correctly
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

def test_web_interface():
    """Test basic web interface functionality"""
    print("🌐 Testing Web Interface")
    print("=" * 60)
    
    client = Client()
    
    # Test homepage
    print("🏠 Testing Homepage...")
    try:
        response = client.get('/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Homepage loads successfully")
        else:
            print("   ❌ Homepage failed to load")
    except Exception as e:
        print(f"   ❌ Homepage error: {str(e)}")
    
    # Test login page
    print("\n🔑 Testing Login Page...")
    try:
        response = client.get('/auth/login/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Login page loads successfully")
        else:
            print("   ❌ Login page failed to load")
    except Exception as e:
        print(f"   ❌ Login error: {str(e)}")
    
    # Test admin login
    print("\n🔐 Testing Admin Login...")
    try:
        admin_user = User.objects.filter(role='superadmin').first()
        if admin_user:
            login_success = client.login(username=admin_user.email, password='admin123')
            if login_success:
                print("   ✅ Super admin login successful")
                
                # Test admin dashboard
                response = client.get('/admin-panel/dashboard/')
                print(f"   Dashboard Status: {response.status_code}")
                if response.status_code == 200:
                    print("   ✅ Admin dashboard loads successfully")
                else:
                    print("   ❌ Admin dashboard failed to load")
            else:
                print("   ❌ Super admin login failed")
        else:
            print("   ❌ No super admin found")
    except Exception as e:
        print(f"   ❌ Admin login error: {str(e)}")
    
    # Test student login
    print("\n👨‍🎓 Testing Student Login...")
    try:
        student_user = User.objects.filter(role='student').first()
        if student_user:
            # Create new client for student
            student_client = Client()
            login_success = student_client.login(username=student_user.email, password='student123')
            if login_success:
                print("   ✅ Student login successful")
                
                # Test student dashboard
                response = student_client.get('/students/dashboard/')
                print(f"   Dashboard Status: {response.status_code}")
                if response.status_code == 200:
                    print("   ✅ Student dashboard loads successfully")
                else:
                    print("   ❌ Student dashboard failed to load")
            else:
                print("   ❌ Student login failed")
        else:
            print("   ❌ No student found")
    except Exception as e:
        print(f"   ❌ Student login error: {str(e)}")
    
    print("\n🎉 Web interface test completed!")
    print("=" * 60)

if __name__ == '__main__':
    test_web_interface()
