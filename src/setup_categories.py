#!/usr/bin/env python
"""
Script to set up academic grievance categories
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

from apps.grievances.models import Category


def create_academic_categories():
    """Create academic grievance categories"""
    academic_categories = [
        {
            'name': 'Grading and Evaluation',
            'description': 'Issues related to grades, marks, evaluation criteria, unfair assessment, grade disputes',
            'keywords': 'grade, marks, evaluation, assessment, unfair grading, exam results'
        },
        {
            'name': 'Teaching Quality',
            'description': 'Concerns about teaching methods, course content delivery, faculty behavior in class',
            'keywords': 'teaching, faculty, professor, course content, teaching method, class quality'
        },
        {
            'name': 'Curriculum and Syllabus',
            'description': 'Issues with course structure, outdated syllabus, insufficient practical sessions',
            'keywords': 'curriculum, syllabus, course structure, practical, lab sessions, course content'
        },
        {
            'name': 'Assignment and Project',
            'description': 'Problems related to assignments, project work, submission issues, unclear requirements',
            'keywords': 'assignment, project, submission, deadline, requirements, group work'
        },
        {
            'name': 'Examination Issues',
            'description': 'Problems during exams, scheduling conflicts, question paper issues, invigilation problems',
            'keywords': 'exam, examination, question paper, invigilation, exam schedule, test'
        },
        {
            'name': 'Academic Counseling',
            'description': 'Issues with academic guidance, course selection, career counseling, faculty advisors',
            'keywords': 'counseling, guidance, advisor, course selection, academic planning'
        },
        {
            'name': 'Research and Thesis',
            'description': 'Problems related to research work, thesis supervision, research facilities, publication',
            'keywords': 'research, thesis, supervisor, publication, research facilities, dissertation'
        },
        {
            'name': 'Academic Misconduct',
            'description': 'Report academic dishonesty, plagiarism, cheating, unfair practices by students or faculty',
            'keywords': 'misconduct, plagiarism, cheating, dishonesty, unfair practice, academic integrity'
        },
        {
            'name': 'Attendance Issues',
            'description': 'Problems with attendance marking, attendance requirements, make-up classes',
            'keywords': 'attendance, absent, present, attendance requirement, make-up class'
        },
        {
            'name': 'Laboratory and Practical',
            'description': 'Issues with lab sessions, equipment, practical work, lab schedules, safety concerns',
            'keywords': 'laboratory, lab, practical, equipment, safety, lab schedule, experiment'
        }
    ]
    
    print("Creating Academic Grievance Categories...")
    
    for cat_data in academic_categories:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            category_type='academic',
            defaults={
                'description': cat_data['description'],
                'keywords': cat_data['keywords'],
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Created: {category.name}")
        else:
            print(f"⚠️  Already exists: {category.name}")
    
    print(f"\n📊 Total Academic Categories: {Category.objects.filter(category_type='academic').count()}")
    

def create_non_academic_categories():
    """Create non-academic grievance categories for future use"""
    non_academic_categories = [
        {
            'name': 'Hostel and Accommodation',
            'description': 'Issues related to hostel facilities, room allocation, maintenance, security',
            'keywords': 'hostel, accommodation, room, maintenance, security, facilities'
        },
        {
            'name': 'Food and Cafeteria',
            'description': 'Problems with food quality, cafeteria services, hygiene, pricing',
            'keywords': 'food, cafeteria, canteen, hygiene, quality, pricing, mess'
        },
        {
            'name': 'Transportation',
            'description': 'Issues with college transport, bus services, parking, vehicle registration',
            'keywords': 'transport, bus, parking, vehicle, registration, travel'
        },
        {
            'name': 'Medical and Health',
            'description': 'Problems with medical facilities, health center, emergency services, medical staff',
            'keywords': 'medical, health, doctor, emergency, first aid, health center'
        }
    ]
    
    print("\nCreating Sample Non-Academic Categories (for future use)...")
    
    for cat_data in non_academic_categories:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            category_type='non_academic',
            defaults={
                'description': cat_data['description'],
                'keywords': cat_data['keywords'],
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Created: {category.name}")
        else:
            print(f"⚠️  Already exists: {category.name}")


if __name__ == '__main__':
    create_academic_categories()
    create_non_academic_categories()
    
    print("\n✅ Grievance categories setup completed!")
    print("\n🌐 You can now access:")
    print("  • Submit Grievance: http://127.0.0.1:8000/grievances/submit/")
    print("  • Admin Panel: http://127.0.0.1:8000/admin/ (to manage categories)")
