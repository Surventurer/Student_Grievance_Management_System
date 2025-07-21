"""
Test the create user functionality with required school and department fields
"""
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from apps.students.models import AdminProfile, StudentProfile, School, Department
from django.db import transaction

def test_required_fields():
    """Test that school and department are now required"""
    print("🧪 Testing Required School and Department Fields")
    print("=" * 60)
    
    # Test 1: Try creating student without school (should fail)
    print("\n❌ Test 1: Student without school...")
    try:
        with transaction.atomic():
            user = User.objects.create(
                email='test.nostudent@example.com',
                role='student'
            )
            user.set_password('test123')
            user.save()
            
            # This should fail now
            StudentProfile.objects.create(
                user=user,
                name='Test Student',
                student_id='NOSCHOOL001',
                # school=  # Missing school
                department='Computer Science'
            )
            print("✅ Created student without school (unexpected)")
    except Exception as e:
        print(f"✅ Correctly failed: {e}")
    
    # Test 2: Try creating admin without department (should fail)
    print("\n❌ Test 2: Admin without department...")
    try:
        with transaction.atomic():
            user = User.objects.create(
                email='test.noadmin@example.com',
                role='admin'
            )
            user.set_password('test123')
            user.save()
            
            # This should fail now
            AdminProfile.objects.create(
                user=user,
                role_level='admin',
                employee_id='NODEPT001',
                # department=  # Missing department
            )
            print("✅ Created admin without department (unexpected)")
    except Exception as e:
        print(f"✅ Correctly failed: {e}")
    
    # Test 3: Create student with all required fields (should succeed)
    print("\n✅ Test 3: Student with all required fields...")
    try:
        with transaction.atomic():
            user = User.objects.create(
                email='test.complete.student@example.com',
                role='student'
            )
            user.set_password('test123')
            user.save()
            
            StudentProfile.objects.create(
                user=user,
                name='Complete Student',
                student_id='COMPLETE001',
                school='Engineering College',
                department='Computer Science'
            )
            print("✅ Created student with all required fields")
            print(f"   School: {user.student_profile.school}")
            print(f"   Department: {user.student_profile.department}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 4: Create admin with all required fields (should succeed)
    print("\n✅ Test 4: Admin with all required fields...")
    try:
        with transaction.atomic():
            user = User.objects.create(
                email='test.complete.admin@example.com',
                role='admin'
            )
            user.set_password('test123')
            user.save()
            
            AdminProfile.objects.create(
                user=user,
                role_level='admin',
                employee_id='COMPLETE001',
                department='Computer Science'
            )
            print("✅ Created admin with all required fields")
            print(f"   Department: {user.admin_profile.department}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Clean up test users
    print("\n🧹 Cleaning up...")
    test_emails = [
        'test.nostudent@example.com',
        'test.noadmin@example.com', 
        'test.complete.student@example.com',
        'test.complete.admin@example.com'
    ]
    User.objects.filter(email__in=test_emails).delete()
    print("✅ Cleanup completed")
    
    print("\n🎉 Required fields test completed!")
    print("=" * 60)

def check_existing_data():
    """Check existing data to ensure defaults were applied"""
    print("\n🔍 Checking existing data...")
    
    # Check students without school
    students_no_school = StudentProfile.objects.filter(school__isnull=True).count()
    students_empty_school = StudentProfile.objects.filter(school='').count()
    print(f"Students with NULL school: {students_no_school}")
    print(f"Students with empty school: {students_empty_school}")
    
    # Check admins without department
    admins_no_dept = AdminProfile.objects.filter(department__isnull=True).count()
    admins_empty_dept = AdminProfile.objects.filter(department='').count()
    print(f"Admins with NULL department: {admins_no_dept}")
    print(f"Admins with empty department: {admins_empty_dept}")
    
    # Show sample data
    print("\nSample student data:")
    for student in StudentProfile.objects.all()[:3]:
        print(f"  {student.student_id}: School='{student.school}', Dept='{student.department}'")
    
    print("\nSample admin data:")
    for admin in AdminProfile.objects.all()[:3]:
        print(f"  {admin.employee_id}: Dept='{admin.department}'")

if __name__ == '__main__':
    check_existing_data()
    test_required_fields()
