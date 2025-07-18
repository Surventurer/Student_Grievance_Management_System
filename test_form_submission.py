#!/usr/bin/env python
"""
Test script to simulate form submission and check if the grievance submission works
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.students.models import StudentProfile
from apps.grievances.models import Category, GrievanceOTPVerification

def test_form_submission():
    client = Client()
    
    # Create or get a test user
    User = get_user_model()
    try:
        user = User.objects.filter(role='student').first()
        if not user:
            print("No student users found. Please create a student user first.")
            return
        print(f"Using test user: {user.email}")
    except Exception as e:
        print(f"Error getting user: {e}")
        return
    
    # Login the user
    client.force_login(user)
    
    # Create an OTP record
    otp_verification = GrievanceOTPVerification.objects.create(
        email=user.email,
        otp='123456'
    )
    
    # Get a category
    category = Category.objects.filter(is_active=True).first()
    if not category:
        print("No categories found. Please populate categories first.")
        return
    
    # Prepare form data
    form_data = {
        'title': 'Test Grievance',
        'description': 'This is a test grievance submission',
        'nature_of_grievance': str(category.id),
        'category_type': category.category_type,
        'otp_code': '123456',
        'is_anonymous': False,
    }
    
    if category.category_type == 'non_academic':
        # Add department for non-academic
        from apps.students.models import Department
        dept = Department.objects.first()
        if dept:
            form_data['department'] = str(dept.id)
    
    print("Submitting form with data:", form_data)
    
    # Submit the form
    response = client.post('/grievances/submit/', form_data)
    
    print(f"Response status: {response.status_code}")
    print(f"Response redirect: {getattr(response, 'url', 'No redirect')}")
    
    if response.status_code == 200:
        print("Form submission failed - stayed on same page")
        if hasattr(response, 'context') and response.context and response.context.get('messages'):
            for message in response.context['messages']:
                print(f"Message: {message}")
    elif response.status_code == 400:
        print("Bad request - form validation failed")
        print(f"Response content length: {len(response.content)}")
        # Print first 500 chars of response to see what happened
        print(f"Response preview: {response.content[:500].decode('utf-8', errors='ignore')}")
    elif response.status_code == 302:
        print("Success - redirected to:", response.url)

if __name__ == '__main__':
    test_form_submission()
