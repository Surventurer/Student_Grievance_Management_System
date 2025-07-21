"""
Simple debug test for create user functionality
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

def debug_create_user():
    print("🐛 Debugging Create User View")
    print("=" * 40)
    
    # Check URL resolution
    try:
        url = reverse('admin_panel:create_user')
        print(f"✅ URL resolves to: {url}")
    except Exception as e:
        print(f"❌ URL resolution failed: {e}")
        return
    
    # Check if superadmin exists
    superadmin = User.objects.filter(role='superadmin').first()
    if not superadmin:
        print("❌ No superadmin found")
        return
    
    print(f"✅ Superadmin found: {superadmin.email}")
    
    # Test direct function call
    try:
        from apps.admin_panel.superadmin_views import create_user
        print("✅ Function imported successfully")
        
        # Test with mock request
        from django.http import HttpRequest
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import AnonymousUser
        
        # Create a mock request
        request = HttpRequest()
        request.method = 'GET'
        request.user = superadmin
        
        # Call the view
        response = create_user(request)
        print(f"✅ Direct function call status: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Direct function call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_create_user()
