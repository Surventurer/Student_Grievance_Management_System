#!/usr/bin/env python
"""
Test script to create a temporary registration for testing the superadmin panel
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

from apps.authentication.models import TemporaryRegistration
from django.contrib.auth.hashers import make_password
from django.utils import timezone

def create_test_temp_registrations():
    """Create test temporary registrations"""
    
    # Clear existing test registrations
    TemporaryRegistration.objects.filter(email__contains='test').delete()
    
    # Create different types of temporary registrations
    registrations = [
        {
            'name': 'John Doe',
            'student_id': 'STU001',
            'email': 'john.test@student.edu',
            'password': make_password('password123'),
            'contact_no': '+1234567890',
            'school': 'Engineering School',
            'department': 'Computer Science',
            'otp': '123456',
            'is_verified': False,  # Awaiting email verification
            'expires_at': timezone.now() + timedelta(hours=24)
        },
        {
            'name': 'Jane Smith',
            'student_id': 'STU002',
            'email': 'jane.test@student.edu',
            'password': make_password('password123'),
            'contact_no': '+1234567891',
            'school': 'Business School',
            'department': 'Marketing',
            'otp': '654321',
            'is_verified': True,  # Awaiting admin approval
            'expires_at': timezone.now() + timedelta(hours=24)
        },
        {
            'name': 'Bob Wilson',
            'student_id': 'STU003',
            'email': 'bob.test@student.edu',
            'password': make_password('password123'),
            'contact_no': '+1234567892',
            'school': 'Science School',
            'department': 'Physics',
            'otp': '987654',
            'is_verified': False,  # Expired registration
            'expires_at': timezone.now() - timedelta(hours=2)
        }
    ]
    
    created_count = 0
    for reg_data in registrations:
        temp_reg = TemporaryRegistration.objects.create(**reg_data)
        created_count += 1
        print(f"Created temporary registration: {temp_reg.name} ({temp_reg.email})")
        print(f"  - Verified: {temp_reg.is_verified}")
        print(f"  - Expired: {temp_reg.is_expired}")
        print(f"  - Expires at: {temp_reg.expires_at}")
        print()
    
    print(f"Total temporary registrations created: {created_count}")
    print(f"Total in database: {TemporaryRegistration.objects.count()}")

if __name__ == '__main__':
    create_test_temp_registrations()
