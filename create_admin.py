#!/usr/bin/env python
"""
Script to create an admin user for the Student Grievance Management System
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User

def create_admin_user():
    """Create an admin user"""
    email = "admin@grievance.com"
    password = "admin123"
    
    # Check if admin user already exists
    if User.objects.filter(email=email).exists():
        admin_user = User.objects.get(email=email)
        print(f"Admin user already exists: {email}")
    else:
        # Create new admin user
        admin_user = User.objects.create_user(
            email=email,
            password=password,
            role='admin',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            is_email_verified=True
        )
        print(f"Admin user created: {email}")
    
    # Ensure user has admin privileges
    admin_user.role = 'admin'
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.is_active = True
    admin_user.is_email_verified = True
    admin_user.set_password(password)
    admin_user.save()
    
    print("\n" + "="*50)
    print("ADMIN LOGIN CREDENTIALS")
    print("="*50)
    print(f"Email: {email}")
    print(f"Password: {password}")
    print(f"Role: {admin_user.role}")
    print(f"Is Admin: {admin_user.is_admin}")
    print("="*50)
    print("\nYou can now login at:")
    print("http://127.0.0.1:8000/auth/login/")
    print("\nThen access admin panel at:")
    print("http://127.0.0.1:8000/admin-panel/dashboard/")
    print("="*50)

if __name__ == "__main__":
    create_admin_user()
