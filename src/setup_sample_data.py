#!/usr/bin/env python
"""
Sample data setup script for Student Grievance Management System
This script creates sample data that matches the database schema structure.
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


def create_sample_data():
    """Create sample data matching the database schema"""
    
    print("Creating sample data for Student Grievance Management System...")
    
    # 1. Create Schools (as per School Table schema)
    schools_data = [
        {"name": "School of Engineering and Technology"},
        {"name": "School of Business and Management"},
        {"name": "School of Computer Science"},
        {"name": "School of Medicine and Health Sciences"},
        {"name": "School of Arts and Humanities"},
    ]
    
    schools = []
    for school_data in schools_data:
        school, created = School.objects.get_or_create(
            name=school_data["name"]
        )
        if created:
            print(f"✓ Created school: {school.name}")
        schools.append(school)
    
    # 2. Create Departments (as per Department Table schema)
    departments_data = [
        {"name": "Computer Science", "school": schools[2]},
        {"name": "Information Technology", "school": schools[2]},
        {"name": "Software Engineering", "school": schools[2]},
        {"name": "Mechanical Engineering", "school": schools[0]},
        {"name": "Electrical Engineering", "school": schools[0]},
        {"name": "Civil Engineering", "school": schools[0]},
        {"name": "Business Administration", "school": schools[1]},
        {"name": "Marketing", "school": schools[1]},
        {"name": "Finance", "school": schools[1]},
        {"name": "General Medicine", "school": schools[3]},
        {"name": "Nursing", "school": schools[3]},
        {"name": "English Literature", "school": schools[4]},
        {"name": "History", "school": schools[4]},
    ]
    
    departments = []
    for dept_data in departments_data:
        dept, created = Department.objects.get_or_create(
            name=dept_data["name"],
            defaults={"school": dept_data["school"]}
        )
        if created:
            print(f"✓ Created department: {dept.name} under {dept.school.name}")
        departments.append(dept)
    
    # 3. Create Users (as per User Table schema: email, password, role, created_at)
    users_data = [
        # Students
        {"email": "john.doe@university.edu", "role": "student"},
        {"email": "jane.smith@university.edu", "role": "student"},
        {"email": "mike.johnson@university.edu", "role": "student"},
        {"email": "sarah.williams@university.edu", "role": "student"},
        {"email": "david.brown@university.edu", "role": "student"},
        {"email": "lisa.davis@university.edu", "role": "student"},
        {"email": "tom.wilson@university.edu", "role": "student"},
        {"email": "anna.garcia@university.edu", "role": "student"},
        
        # Admin/Officers
        {"email": "admin@university.edu", "role": "admin"},
        {"email": "officer1@university.edu", "role": "officer"},
        {"email": "officer2@university.edu", "role": "officer"},
        {"email": "superadmin@university.edu", "role": "superadmin"},
    ]
    
    users = []
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            email=user_data["email"],
            defaults={
                "role": user_data["role"],
                "is_email_verified": True,
            }
        )
        if created:
            user.set_password("password123")  # Default password for demo
            if user.role in ['admin', 'superadmin', 'officer']:
                user.is_staff = True
            if user.role == 'superadmin':
                user.is_superuser = True
            user.save()
            print(f"✓ Created user: {user.email} ({user.role})")
        users.append(user)
    
    # 4. Create Student Profiles (as per Student Profile Table schema)
    # Fields: name, email (FK), student_id, school, department, contact_no
    student_profiles_data = [
        {"user": users[0], "name": "John Doe", "student_id": "CS2024001", "department": "Computer Science", "contact_no": "+1-555-0101"},
        {"user": users[1], "name": "Jane Smith", "student_id": "IT2024002", "department": "Information Technology", "contact_no": "+1-555-0102"},
        {"user": users[2], "name": "Mike Johnson", "student_id": "SE2024003", "department": "Software Engineering", "contact_no": "+1-555-0103"},
        {"user": users[3], "name": "Sarah Williams", "student_id": "ME2024004", "department": "Mechanical Engineering", "contact_no": "+1-555-0104"},
        {"user": users[4], "name": "David Brown", "student_id": "EE2024005", "department": "Electrical Engineering", "contact_no": "+1-555-0105"},
        {"user": users[5], "name": "Lisa Davis", "student_id": "BA2024006", "department": "Business Administration", "contact_no": "+1-555-0106"},
        {"user": users[6], "name": "Tom Wilson", "student_id": "MED2024007", "department": "General Medicine", "contact_no": "+1-555-0107"},
        {"user": users[7], "name": "Anna Garcia", "student_id": "ENG2024008", "department": "English Literature", "contact_no": "+1-555-0108"},
    ]
    
    for profile_data in student_profiles_data:
        profile, created = StudentProfile.objects.get_or_create(
            user=profile_data["user"],
            defaults={
                "name": profile_data["name"],
                "student_id": profile_data["student_id"],
                "department": profile_data["department"],
                "school": "Main Campus",  # Default school name
                "contact_no": profile_data["contact_no"],
            }
        )
        if created:
            print(f"✓ Created student profile: {profile.name} ({profile.student_id})")
    
    # 5. Create Admin Profiles
    admin_profiles_data = [
        {"user": users[8], "role_level": "admin", "employee_id": "ADMIN001", "department": "Administration"},
        {"user": users[9], "role_level": "officer", "employee_id": "OFF001", "department": "Student Affairs"},
        {"user": users[10], "role_level": "officer", "employee_id": "OFF002", "department": "Academic Affairs"},
        {"user": users[11], "role_level": "superadmin", "employee_id": "SUPER001", "department": "IT Services"},
    ]
    
    for profile_data in admin_profiles_data:
        profile, created = AdminProfile.objects.get_or_create(
            user=profile_data["user"],
            defaults={
                "role_level": profile_data["role_level"],
                "employee_id": profile_data["employee_id"],
                "department": profile_data["department"],
                "phone": "+1-555-9999",
                "office_location": "Admin Building",
            }
        )
        if created:
            print(f"✓ Created admin profile: {profile.user.email} ({profile.role_level})")
    
    print("\n🎉 Sample data creation completed successfully!")
    print("\nSample login credentials:")
    print("Students: john.doe@university.edu, jane.smith@university.edu, etc.")
    print("Admin: admin@university.edu")
    print("Officer: officer1@university.edu, officer2@university.edu")
    print("Super Admin: superadmin@university.edu")
    print("Password for all accounts: password123")
    
    print(f"\nDatabase Summary:")
    print(f"- Schools: {School.objects.count()}")
    print(f"- Departments: {Department.objects.count()}")
    print(f"- Users: {User.objects.count()}")
    print(f"- Student Profiles: {StudentProfile.objects.count()}")
    print(f"- Admin Profiles: {AdminProfile.objects.count()}")


if __name__ == "__main__":
    create_sample_data()
