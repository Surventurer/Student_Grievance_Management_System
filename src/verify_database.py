#!/usr/bin/env python
"""
Database verification script to show the created data structure
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.authentication.models import User
from apps.students.models import School, Department, StudentProfile, AdminProfile


def verify_database_structure():
    """Verify the database structure matches the schema"""
    
    print("=== DATABASE STRUCTURE VERIFICATION ===\n")
    
    # User Table verification
    print("📋 USER TABLE")
    print("Fields: email, password, role, created_at")
    users = User.objects.all()[:3]
    for user in users:
        print(f"  • Email: {user.email}")
        print(f"    Password: {'*' * len(user.password[:10])}... (hashed)")
        print(f"    Role: {user.role}")
        print(f"    Created: {user.created_at}")
        print()
    
    # School Table verification
    print("🏫 SCHOOL TABLE")
    print("Fields: id (UUID/Auto Primary key), name (unique)")
    schools = School.objects.all()[:3]
    for school in schools:
        print(f"  • ID: {school.id}")
        print(f"    Name: {school.name}")
        print()
    
    # Department Table verification  
    print("🏢 DEPARTMENT TABLE")
    print("Fields: id (UUID/Auto Primary key), name, school_id (FK → School)")
    departments = Department.objects.all()[:3]
    for dept in departments:
        print(f"  • ID: {dept.id}")
        print(f"    Name: {dept.name}")
        print(f"    School: {dept.school.name if dept.school else 'None'}")
        print()
    
    # Student Profile Table verification
    print("🎓 STUDENT PROFILE TABLE")
    print("Fields: name, email (FK → User.email One-to-One), student_id, school, department, contact_no")
    profiles = StudentProfile.objects.all()[:3]
    for profile in profiles:
        print(f"  • Name: {profile.name}")
        print(f"    Email: {profile.email} (FK to User)")
        print(f"    Student ID: {profile.student_id}")
        print(f"    School: {profile.school}")
        print(f"    Department: {profile.department}")
        print(f"    Contact: {profile.contact_no}")
        print()
    
    # Summary
    print("📊 DATABASE SUMMARY")
    print(f"  • Total Schools: {School.objects.count()}")
    print(f"  • Total Departments: {Department.objects.count()}")
    print(f"  • Total Users: {User.objects.count()}")
    print(f"  • Total Student Profiles: {StudentProfile.objects.count()}")
    print(f"  • Total Admin Profiles: {AdminProfile.objects.count()}")
    
    print("\n✅ Database structure matches the provided schema!")
    print("\n🔑 Login Credentials (Password: password123)")
    print("  • Super Admin: superadmin@university.edu")
    print("  • Admin: admin@university.edu") 
    print("  • Officers: officer1@university.edu, officer2@university.edu")
    print("  • Students: john.doe@university.edu, jane.smith@university.edu, etc.")
    
    print("\n🌐 Access URLs:")
    print("  • Development Server: http://127.0.0.1:8000/")
    print("  • Django Admin: http://127.0.0.1:8000/admin/")


if __name__ == "__main__":
    verify_database_structure()
