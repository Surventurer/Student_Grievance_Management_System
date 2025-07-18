#!/usr/bin/env python
"""
Quick test script to verify admin login functionality
"""

import os
import django
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User

def test_admin_login():
    """Test admin login"""
    try:
        admin_user = User.objects.get(email='admin@university.edu')
        print(f"Admin user found: {admin_user.email}")
        print(f"Is admin: {admin_user.is_admin}")
        print(f"Role: {admin_user.role}")
        print(f"Is active: {admin_user.is_active}")
        print(f"Is staff: {admin_user.is_staff}")
        
        # Test password
        if admin_user.check_password('admin123'):
            print("✓ Password is correct")
        else:
            print("✗ Password is incorrect")
            
    except User.DoesNotExist:
        print("Admin user not found")

if __name__ == '__main__':
    test_admin_login()
