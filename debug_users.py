#!/usr/bin/env python
"""
Debug script to check what's happening with the user_management view
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User, TemporaryRegistration
from django.db.models import Q

def debug_user_management():
    """Debug the user_management view logic"""
    
    print("=== DEBUG: User Management View ===")
    
    # Test the exact logic from the view
    users = User.objects.all().order_by('-created_at')
    print(f"Total verified users: {users.count()}")
    
    # Test show_unverified = True
    show_unverified = True
    if show_unverified:
        temp_registrations = TemporaryRegistration.objects.all().order_by('-created_at')
    else:
        temp_registrations = TemporaryRegistration.objects.none()
    
    print(f"Temporary registrations (show_unverified=True): {temp_registrations.count()}")
    
    # Test show_unverified = False
    show_unverified = False
    if show_unverified:
        temp_registrations_false = TemporaryRegistration.objects.all().order_by('-created_at')
    else:
        temp_registrations_false = TemporaryRegistration.objects.none()
    
    print(f"Temporary registrations (show_unverified=False): {temp_registrations_false.count()}")
    
    # Show details of temporary registrations
    print("\n=== Temporary Registration Details ===")
    for temp_reg in TemporaryRegistration.objects.all():
        print(f"ID: {temp_reg.id}, Email: {temp_reg.email}, Name: {temp_reg.name}")
        print(f"  - Verified: {temp_reg.is_verified}")
        print(f"  - Expired: {temp_reg.is_expired}")
        print(f"  - Created: {temp_reg.created_at}")
        print()
    
    # Test the combined logic
    print("=== Combined User List Test ===")
    all_users = []
    
    # Add verified users
    for user in users:
        user.is_temporary = False
        user.user_type = 'verified'
        all_users.append(user)
        print(f"Added verified user: {user.email}")
    
    # Add temporary registrations (with show_unverified=True)
    temp_registrations = TemporaryRegistration.objects.all().order_by('-created_at')
    for temp_reg in temp_registrations:
        temp_reg.is_temporary = True
        temp_reg.user_type = 'temporary'
        temp_reg.role = 'student'
        temp_reg.is_active = not temp_reg.is_expired
        temp_reg.is_email_verified = temp_reg.is_verified
        temp_reg.get_role_display = 'Student (Unverified)'
        temp_reg.get_display_name = temp_reg.name
        temp_reg.id = f"temp_{temp_reg.id}"
        all_users.append(temp_reg)
        print(f"Added temporary user: {temp_reg.email} (ID: {temp_reg.id})")
    
    print(f"\nTotal combined users: {len(all_users)}")
    print(f"Verified users: {len([u for u in all_users if not getattr(u, 'is_temporary', False)])}")
    print(f"Temporary users: {len([u for u in all_users if getattr(u, 'is_temporary', False)])}")

if __name__ == '__main__':
    debug_user_management()
