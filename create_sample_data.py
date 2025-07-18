#!/usr/bin/env python
"""
Create sample schools and departments for testing
"""
import os
import sys
import django

# Setup Django
sys.path.append('src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.students.models import School, Department

def create_sample_data():
    """Create sample schools and departments"""
    
    # Clear existing data
    Department.objects.all().delete()
    School.objects.all().delete()
    
    # Create schools
    schools_data = [
        {
            'name': 'School of Engineering',
            'departments': [
                'Computer Science',
                'Electrical Engineering',
                'Mechanical Engineering',
                'Civil Engineering',
                'Chemical Engineering'
            ]
        },
        {
            'name': 'School of Business',
            'departments': [
                'Business Administration',
                'Marketing',
                'Finance',
                'Human Resources',
                'Operations Management'
            ]
        },
        {
            'name': 'School of Arts and Sciences',
            'departments': [
                'English Literature',
                'Mathematics',
                'Physics',
                'Chemistry',
                'Biology',
                'History',
                'Psychology'
            ]
        },
        {
            'name': 'School of Medicine',
            'departments': [
                'General Medicine',
                'Surgery',
                'Pediatrics',
                'Cardiology',
                'Neurology'
            ]
        }
    ]
    
    for school_data in schools_data:
        # Create school
        school = School.objects.create(name=school_data['name'])
        print(f"Created school: {school.name}")
        
        # Create departments for this school
        for dept_name in school_data['departments']:
            department = Department.objects.create(
                name=dept_name,
                school=school
            )
            print(f"  Created department: {department.name}")
    
    print(f"\nCreated {School.objects.count()} schools and {Department.objects.count()} departments")
    
    # Verify the relationships
    print("\nVerifying relationships:")
    for school in School.objects.all():
        dept_count = school.departments.count()
        print(f"{school.name}: {dept_count} departments")

if __name__ == '__main__':
    create_sample_data()
