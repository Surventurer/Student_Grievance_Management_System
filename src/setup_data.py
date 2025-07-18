#!/usr/bin/env python
"""
Script to set up initial data for the Student Grievance Management System
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
from apps.students.models import StudentProfile, AdminProfile, Department
from apps.grievances.models import Category


def create_departments():
    """Create sample departments"""
    departments = [
        'Computer Science',
        'Electronics',
        'Mechanical',
        'Civil',
        'Chemical',
        'Electrical',
        'Information Technology',
        'Biotechnology',
    ]
    
    for dept_name in departments:
        dept, created = Department.objects.get_or_create(
            name=dept_name,
            defaults={
                'description': f'{dept_name} Department',
                'contact_email': f'{dept_name.lower().replace(" ", "")}@university.edu',
                'contact_phone': '+1234567890',
            }
        )
        if created:
            print(f'Created department: {dept_name}')


def create_categories():
    """Create sample grievance categories"""
    categories = [
        ('Academic', 'Issues related to courses, exams, and academic matters', 'academic'),
        ('Administrative', 'Issues related to administrative processes and procedures', 'non_academic'),
        ('Infrastructure', 'Issues related to campus facilities and infrastructure', 'non_academic'),
        ('Library', 'Issues related to library services and resources', 'non_academic'),
        ('Hostel', 'Issues related to hostel facilities and accommodation', 'non_academic'),
        ('Transportation', 'Issues related to campus transportation', 'non_academic'),
        ('Fee', 'Issues related to fee payment and refunds', 'non_academic'),
        ('Other', 'Other general issues', 'non_academic'),
    ]
    
    for cat_name, cat_desc, cat_type in categories:
        cat, created = Category.objects.get_or_create(
            name=cat_name,
            defaults={
                'description': cat_desc,
                'category_type': cat_type,
                'is_active': True
            }
        )
        if created:
            print(f'Created category: {cat_name}')


def create_sample_users():
    """Create sample users for testing"""
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        email='admin@university.edu',
        defaults={
            'username': 'admin',
            'first_name': 'Admin',
            'last_name': 'User',
            'role': 'admin',
            'is_active': True,
            'is_staff': True,
            'is_email_verified': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f'Created admin user: {admin_user.email}')
        
        # Create admin profile
        AdminProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role_level': 'superadmin',
                'employee_id': 'ADMIN001',
                'phone': '+1234567890',
                'office_location': 'Admin Block'
            }
        )
    
    # Create a student user
    student_user, created = User.objects.get_or_create(
        email='student@university.edu',
        defaults={
            'username': 'student',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'student',
            'is_active': True,
            'is_email_verified': True
        }
    )
    if created:
        student_user.set_password('student123')
        student_user.save()
        print(f'Created student user: {student_user.email}')
        
        # Create student profile
        cs_dept = Department.objects.get(name='Computer Science')
        StudentProfile.objects.get_or_create(
            user=student_user,
            defaults={
                'student_id': 'CS2025001',
                'department': cs_dept.name,
                'contact_no': '+1234567891',
                'year_of_study': '2nd Year',
                'course': 'Computer Science',
                'emergency_contact': '+1234567892',
                'address': '123 Student St, Campus Area',
            }
        )


def create_sample_grievances():
    """Create sample grievances for testing"""
    from apps.grievances.models import Grievance
    
    # Get student and categories
    try:
        student = StudentProfile.objects.get(student_id='CS2025001')
        academic_category = Category.objects.get(name='Academic')
        infrastructure_category = Category.objects.get(name='Infrastructure')
        
        # Create sample grievances
        grievances = [
            {
                'title': 'Library Access Issues',
                'description': 'Unable to access digital library resources from hostel WiFi',
                'category': academic_category,
                'priority': 'medium',
                'status': 'pending'
            },
            {
                'title': 'Hostel WiFi Connectivity',
                'description': 'Poor WiFi connectivity in Block A, affecting online classes',
                'category': infrastructure_category,
                'priority': 'high',
                'status': 'under_review'
            },
            {
                'title': 'Exam Schedule Conflict',
                'description': 'Two exams scheduled at the same time for different subjects',
                'category': academic_category,
                'priority': 'urgent',
                'status': 'resolved'
            },
        ]
        
        for grievance_data in grievances:
            grievance, created = Grievance.objects.get_or_create(
                title=grievance_data['title'],
                student=student,
                defaults={
                    'description': grievance_data['description'],
                    'category': grievance_data['category'],
                    'priority': grievance_data['priority'],
                    'status': grievance_data['status'],
                }
            )
            if created:
                print(f'Created grievance: {grievance.title}')
                
    except (StudentProfile.DoesNotExist, Category.DoesNotExist) as e:
        print(f'Error creating sample grievances: {e}')


def main():
    """Run the setup"""
    print("Setting up initial data for Student Grievance Management System...")
    
    create_departments()
    create_categories()
    create_sample_users()
    create_sample_grievances()
    
    print("\nSetup completed successfully!")
    print("\nSample login credentials:")
    print("Admin: admin@university.edu / admin123")
    print("Student: student@university.edu / student123")


if __name__ == '__main__':
    main()
