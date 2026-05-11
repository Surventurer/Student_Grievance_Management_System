"""
Management command to set up the grievance system with proper role-based data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from apps.authentication.models import User
from apps.students.models import StudentProfile, AdminProfile, School, Department
from apps.grievances.models import Category
import uuid


class Command(BaseCommand):
    help = 'Setup role-based grievance management system with default data'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting role-based grievance system setup...')
        )

        with transaction.atomic():
            # Create Schools
            self.create_schools()
            
            # Create Departments
            self.create_departments()
            
            # Create Categories
            self.create_categories()
            
            # Create Users and Profiles
            self.create_users_and_profiles()
            
        self.stdout.write(
            self.style.SUCCESS('Role-based grievance system setup completed successfully!')
        )
        self.print_credentials()

    def create_schools(self):
        """Create default schools"""
        schools_data = [
            {
                'name': 'School of Computer Science',
                'code': 'SCS',
                'description': 'Computer Science and IT programs'
            },
            {
                'name': 'School of Business Administration', 
                'code': 'SBA',
                'description': 'Business and Management programs'
            },
            {
                'name': 'School of Engineering',
                'code': 'SOE', 
                'description': 'Engineering programs'
            }
        ]
        
        for school_data in schools_data:
            school, created = School.objects.get_or_create(
                name=school_data['name'],
                defaults=school_data
            )
            if created:
                self.stdout.write(f'Created school: {school.name}')

    def create_departments(self):
        """Create default departments"""
        cs_school = School.objects.get(code='SCS')
        ba_school = School.objects.get(code='SBA')
        eng_school = School.objects.get(code='SOE')
        
        departments_data = [
            {'name': 'Computer Science', 'school': cs_school, 'code': 'CS'},
            {'name': 'Information Technology', 'school': cs_school, 'code': 'IT'},
            {'name': 'Business Administration', 'school': ba_school, 'code': 'BA'},
            {'name': 'Marketing', 'school': ba_school, 'code': 'MKT'},
            {'name': 'Mechanical Engineering', 'school': eng_school, 'code': 'ME'},
            {'name': 'Electrical Engineering', 'school': eng_school, 'code': 'EE'},
        ]
        
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults=dept_data
            )
            if created:
                self.stdout.write(f'Created department: {dept.name}')

    def create_categories(self):
        """Create default grievance categories"""
        categories_data = [
            {
                'name': 'Academic Issues',
                'category_type': 'academic',
                'description': 'Issues related to courses, exams, grades'
            },
            {
                'name': 'Faculty Issues',
                'category_type': 'academic', 
                'description': 'Issues with teaching staff and faculty'
            },
            {
                'name': 'Infrastructure Issues',
                'category_type': 'non_academic',
                'description': 'Issues with campus facilities and infrastructure'
            },
            {
                'name': 'Administrative Issues',
                'category_type': 'non_academic',
                'description': 'Issues with administrative processes'
            },
            {
                'name': 'Other Academic',
                'category_type': 'academic',
                'description': 'Other academic related issues'
            },
            {
                'name': 'Other Non-Academic', 
                'category_type': 'non_academic',
                'description': 'Other non-academic related issues'
            }
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

    def create_users_and_profiles(self):
        """Create default users with proper role-based profiles"""
        
        # 1. Create Superadmin
        superadmin_user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'role': 'superadmin',
                'is_staff': True,
                'is_superuser': True,
                'is_email_verified': True,
                'password': make_password('admin123')
            }
        )
        
        if created:
            AdminProfile.objects.create(
                user=superadmin_user,
                role_level='superadmin',
                employee_id='SUPER001',
                department='Administration'
            )
            self.stdout.write(f'Created superadmin: {superadmin_user.email}')

        # 2. Create Department Admins
        admin_data = [
            {
                'email': 'cs.admin@university.edu',
                'employee_id': 'ADM001',
                'department': 'Computer Science'
            },
            {
                'email': 'ba.admin@university.edu', 
                'employee_id': 'ADM002',
                'department': 'Business Administration'
            },
            {
                'email': 'eng.admin@university.edu',
                'employee_id': 'ADM003', 
                'department': 'Mechanical Engineering'
            }
        ]
        
        for admin_info in admin_data:
            admin_user, created = User.objects.get_or_create(
                email=admin_info['email'],
                defaults={
                    'role': 'admin',
                    'is_staff': True,
                    'is_email_verified': True,
                    'password': make_password('admin123')
                }
            )
            
            if created:
                AdminProfile.objects.create(
                    user=admin_user,
                    role_level='admin',
                    employee_id=admin_info['employee_id'],
                    department=admin_info['department']
                )
                self.stdout.write(f'Created admin: {admin_user.email}')

        # 3. Create Officers  
        officer_data = [
            {
                'email': 'officer1@university.edu',
                'employee_id': 'OFF001',
                'department': 'Computer Science'
            },
            {
                'email': 'officer2@university.edu',
                'employee_id': 'OFF002', 
                'department': 'Business Administration'
            }
        ]
        
        for officer_info in officer_data:
            officer_user, created = User.objects.get_or_create(
                email=officer_info['email'],
                defaults={
                    'role': 'officer',
                    'is_email_verified': True,
                    'password': make_password('officer123')
                }
            )
            
            if created:
                AdminProfile.objects.create(
                    user=officer_user,
                    role_level='officer',
                    employee_id=officer_info['employee_id'], 
                    department=officer_info['department']
                )
                self.stdout.write(f'Created officer: {officer_user.email}')

        # 4. Create Students
        student_data = [
            {
                'email': 'student1@university.edu',
                'name': 'John Doe',
                'student_id': 'STU001', 
                'department': 'Computer Science',
                'school': 'School of Computer Science'
            },
            {
                'email': 'student2@university.edu',
                'name': 'Jane Smith',
                'student_id': 'STU002',
                'department': 'Business Administration', 
                'school': 'School of Business Administration'
            },
            {
                'email': 'student3@university.edu',
                'name': 'Mike Johnson', 
                'student_id': 'STU003',
                'department': 'Mechanical Engineering',
                'school': 'School of Engineering'
            }
        ]
        
        for student_info in student_data:
            student_user, created = User.objects.get_or_create(
                email=student_info['email'],
                defaults={
                    'role': 'student',
                    'is_email_verified': True,
                    'password': make_password('student123')
                }
            )
            
            if created:
                StudentProfile.objects.create(
                    user=student_user,
                    name=student_info['name'],
                    student_id=student_info['student_id'],
                    department=student_info['department'],
                    school=student_info['school']
                )
                self.stdout.write(f'Created student: {student_user.email}')

    def print_credentials(self):
        """Print login credentials for all roles"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('DEFAULT LOGIN CREDENTIALS'))
        self.stdout.write('='*60)
        
        self.stdout.write('\n🔴 SUPERADMIN:')
        self.stdout.write('  Email: admin@example.com')
        self.stdout.write('  Password: admin123')
        self.stdout.write('  Access: Full system control')
        
        self.stdout.write('\n🟠 DEPARTMENT ADMINS:')
        admins = [
            ('cs.admin@university.edu', 'Computer Science'),
            ('ba.admin@university.edu', 'Business Administration'), 
            ('eng.admin@university.edu', 'Mechanical Engineering')
        ]
        for email, dept in admins:
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Password: admin123')
            self.stdout.write(f'  Department: {dept}')
            self.stdout.write('')
        
        self.stdout.write('🔵 OFFICERS:')
        officers = [
            ('officer1@university.edu', 'Computer Science'),
            ('officer2@university.edu', 'Business Administration')
        ]
        for email, dept in officers:
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Password: officer123') 
            self.stdout.write(f'  Department: {dept}')
            self.stdout.write('')
            
        self.stdout.write('🟢 STUDENTS:')
        students = [
            ('student1@university.edu', 'John Doe', 'Computer Science'),
            ('student2@university.edu', 'Jane Smith', 'Business Administration'),
            ('student3@university.edu', 'Mike Johnson', 'Mechanical Engineering')
        ]
        for email, name, dept in students:
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Password: student123')
            self.stdout.write(f'  Name: {name} ({dept})')
            self.stdout.write('')
        
        self.stdout.write('='*60)
        self.stdout.write('🚀 System is ready! Login at: /auth/login/')
        self.stdout.write('='*60)
