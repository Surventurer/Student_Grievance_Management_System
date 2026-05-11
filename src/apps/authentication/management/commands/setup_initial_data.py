from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.students.models import School, Department, StudentProfile, AdminProfile
from apps.grievances.models import Category
from apps.authentication.models import User

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup initial data for the Student Grievance Management System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up initial data...'))
        
        # Create superuser if not exists
        if not User.objects.filter(email='admin@example.com').exists():
            admin_user = User.objects.create_superuser(
                email='admin@example.com',
                password='admin123',
                role='superadmin'
            )
            admin_user.is_email_verified = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created superuser: admin@example.com / admin123'))
        
        # Create sample schools
        school1, created = School.objects.get_or_create(
            name="School of Engineering",
            defaults={
                'code': 'SOE',
                'description': 'School of Engineering and Technology',
                'address': '123 University Ave',
                'phone': '+1-555-0101',
                'email': 'engineering@university.edu'
            }
        )
        
        school2, created = School.objects.get_or_create(
            name="School of Business",
            defaults={
                'code': 'SOB',
                'description': 'School of Business Administration',
                'address': '456 Campus Rd',
                'phone': '+1-555-0102',
                'email': 'business@university.edu'
            }
        )
        
        # Create sample departments
        dept1, created = Department.objects.get_or_create(
            name="Computer Science",
            school=school1,
            defaults={
                'code': 'CS',
                'description': 'Department of Computer Science and Engineering',
                'office_location': 'Engineering Building, Floor 3',
                'contact_email': 'cs@university.edu',
                'phone': '+1-555-0301'
            }
        )
        
        dept2, created = Department.objects.get_or_create(
            name="Business Administration",
            school=school2,
            defaults={
                'code': 'BA',
                'description': 'Department of Business Administration',
                'office_location': 'Business Building, Floor 2',
                'contact_email': 'ba@university.edu',
                'phone': '+1-555-0302'
            }
        )
        
        # Create sample admin users
        if not User.objects.filter(email='cs.admin@university.edu').exists():
            cs_admin_user = User.objects.create_user(
                email='cs.admin@university.edu',
                password='admin123',
                role='admin'
            )
            cs_admin_user.is_email_verified = True
            cs_admin_user.is_staff = True
            cs_admin_user.save()
            
            AdminProfile.objects.create(
                user=cs_admin_user,
                employee_id='EMP001',
                department='Computer Science',
                role_level='dept_admin',
                phone='+1-555-1001',
                office_location='CS Building 301'
            )
            self.stdout.write(self.style.SUCCESS('Created CS Admin: cs.admin@university.edu / admin123'))
        
        if not User.objects.filter(email='ba.admin@university.edu').exists():
            ba_admin_user = User.objects.create_user(
                email='ba.admin@university.edu',
                password='admin123',
                role='admin'
            )
            ba_admin_user.is_email_verified = True
            ba_admin_user.is_staff = True
            ba_admin_user.save()
            
            AdminProfile.objects.create(
                user=ba_admin_user,
                employee_id='EMP002',
                department='Business Administration',
                role_level='dept_admin',
                phone='+1-555-1002',
                office_location='BA Building 201'
            )
            self.stdout.write(self.style.SUCCESS('Created BA Admin: ba.admin@university.edu / admin123'))
        
        # Create sample student users
        if not User.objects.filter(email='student1@university.edu').exists():
            student1_user = User.objects.create_user(
                email='student1@university.edu',
                password='student123',
                role='student'
            )
            student1_user.is_email_verified = True
            student1_user.save()
            
            StudentProfile.objects.create(
                user=student1_user,
                student_id='CS2024001',
                name='Alice Johnson',
                department='Computer Science',
                school='School of Engineering',
                contact_no='+1-555-2001'
            )
            self.stdout.write(self.style.SUCCESS('Created Student: student1@university.edu / student123'))
        
        if not User.objects.filter(email='student2@university.edu').exists():
            student2_user = User.objects.create_user(
                email='student2@university.edu',
                password='student123',
                role='student'
            )
            student2_user.is_email_verified = True
            student2_user.save()
            
            StudentProfile.objects.create(
                user=student2_user,
                student_id='BA2024002',
                name='Bob Wilson',
                department='Business Administration',
                school='School of Business',
                contact_no='+1-555-2002'
            )
            self.stdout.write(self.style.SUCCESS('Created Student: student2@university.edu / student123'))
        
        # Create sample categories
        categories_data = [
            {
                'name': 'Academic - Grade Issues',
                'description': 'Issues related to grades, grading disputes, and academic records',
                'category_type': 'academic',
                'keywords': 'grade, grading, marks, score, exam, assignment'
            },
            {
                'name': 'Academic - Course Content',
                'description': 'Issues with course material, curriculum, or teaching quality',
                'category_type': 'academic',
                'keywords': 'course, curriculum, teaching, professor, lecture, material'
            },
            {
                'name': 'Non-Academic - Facilities',
                'description': 'Issues with campus facilities, infrastructure, and maintenance',
                'category_type': 'non_academic',
                'keywords': 'facility, building, maintenance, repair, infrastructure, campus'
            },
            {
                'name': 'Non-Academic - Administrative',
                'description': 'Issues with administrative processes, documentation, and services',
                'category_type': 'non_academic',
                'keywords': 'admin, administration, document, process, service, office'
            },
            {
                'name': 'Other',
                'description': 'Other issues not covered by specific categories',
                'category_type': 'non_academic',
                'keywords': 'other, miscellaneous'
            }
        ]
        
        for category_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'description': category_data['description'],
                    'category_type': category_data['category_type'],
                    'keywords': category_data['keywords'],
                    'is_active': True,
                    'auto_assign_enabled': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Initial setup completed successfully!'))
        self.stdout.write(self.style.SUCCESS('\nLogin credentials:'))
        self.stdout.write(self.style.SUCCESS('Superuser: admin@example.com / admin123'))
        self.stdout.write(self.style.SUCCESS('CS Admin: cs.admin@university.edu / admin123'))
        self.stdout.write(self.style.SUCCESS('BA Admin: ba.admin@university.edu / admin123'))
        self.stdout.write(self.style.SUCCESS('Student 1: student1@university.edu / student123'))
        self.stdout.write(self.style.SUCCESS('Student 2: student2@university.edu / student123'))
        self.stdout.write(self.style.SUCCESS('\nYou can now run: uv run python src/manage.py runserver'))
