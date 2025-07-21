"""
Update existing records to have proper school and department values
"""
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.students.models import AdminProfile, StudentProfile

def update_existing_records():
    """Update existing records to have proper values"""
    print("🔧 Updating existing records...")
    
    # Update student profiles with empty or null school
    students_updated = 0
    for student in StudentProfile.objects.all():
        if not student.school or student.school.strip() == '':
            # Assign school based on department
            if 'Computer Science' in student.department:
                student.school = 'School of Computer Science'
            elif 'Business' in student.department:
                student.school = 'School of Business Administration'
            elif 'Engineering' in student.department:
                student.school = 'School of Engineering'
            else:
                student.school = 'General School'
            student.save()
            students_updated += 1
            print(f"  Updated student {student.student_id}: {student.school}")
    
    # Update admin profiles with empty or null department
    admins_updated = 0
    for admin in AdminProfile.objects.all():
        if not admin.department or admin.department.strip() == '':
            if admin.role_level == 'superadmin':
                admin.department = 'Administration'
            else:
                admin.department = 'General Department'
            admin.save()
            admins_updated += 1
            print(f"  Updated admin {admin.employee_id}: {admin.department}")
    
    print(f"✅ Updated {students_updated} students and {admins_updated} admins")

if __name__ == '__main__':
    update_existing_records()
