from django.core.management.base import BaseCommand
from apps.grievances.models import Category


class Command(BaseCommand):
    help = 'Populate grievance categories with comprehensive academic and non-academic types'

    def handle(self, *args, **options):
        # Academic Categories from the first image
        academic_categories = [
            {
                'name': 'Withhold or refuse to return any document (certificates of degree diploma or any other award/document for the purpose of seeking admission)',
                'description': 'Issues related to withholding of academic documents and certificates',
                'keywords': 'document, certificate, degree, diploma, withhold, refuse'
            },
            {
                'name': 'About academic probations/suspensions',
                'description': 'Issues related to academic probations and suspensions',
                'keywords': 'probation, suspension, academic discipline'
            },
            {
                'name': 'About Faculty Performance /Faculty Behaviour/Assigned Mentor',
                'description': 'Issues related to faculty performance, behavior, and mentorship',
                'keywords': 'faculty, teacher, mentor, behavior, performance'
            },
            {
                'name': 'Attendance of students',
                'description': 'Issues related to student attendance policies and records',
                'keywords': 'attendance, present, absent, attendance policy'
            },
            {
                'name': 'Unfair evaluation practices',
                'description': 'Issues related to unfair evaluation and grading practices',
                'keywords': 'evaluation, grading, unfair, bias, marks'
            },
            {
                'name': 'School amenities/cleanliness/maintenance issues',
                'description': 'Issues related to school facilities, cleanliness, and maintenance',
                'keywords': 'amenities, cleanliness, maintenance, facilities'
            },
            {
                'name': 'Change of Course/Program',
                'description': 'Issues related to course or program changes',
                'keywords': 'course change, program change, transfer'
            },
            {
                'name': 'Labs related issues',
                'description': 'Issues related to laboratory facilities and equipment',
                'keywords': 'lab, laboratory, equipment, practical'
            },
            {
                'name': 'About teaching methodology',
                'description': 'Issues related to teaching methods and pedagogy',
                'keywords': 'teaching, methodology, pedagogy, instruction'
            },
            {
                'name': 'Delay in conduct of examination or declaration of results',
                'description': 'Issues related to examination delays and result declaration',
                'keywords': 'examination, exam, delay, results, declaration'
            },
            {
                'name': 'Request for Bonafide Certificate for Opening Bank Account',
                'description': 'Issues related to bonafide certificate requests',
                'keywords': 'bonafide, certificate, bank account'
            },
            {
                'name': 'Permission for Registration with Pending Dues',
                'description': 'Issues related to registration with pending dues',
                'keywords': 'registration, pending dues, permission'
            },
            {
                'name': 'Request to provide Degree Certificate within 30 days (After Completion of the Course)',
                'description': 'Issues related to degree certificate provision after course completion',
                'keywords': 'degree certificate, completion, 30 days'
            },
            {
                'name': 'Request for Transcripts, Grade Card and Degree',
                'description': 'Issues related to transcript and grade card requests',
                'keywords': 'transcript, grade card, degree, records'
            },
            {
                'name': 'Discrepancy in Certificates/Correction in Certificates',
                'description': 'Issues related to certificate discrepancies and corrections',
                'keywords': 'certificate, discrepancy, correction, error'
            },
            {
                'name': 'Degree Verification',
                'description': 'Issues related to degree verification processes',
                'keywords': 'degree verification, authentication'
            },
            {
                'name': 'Withdrawal of admission',
                'description': 'Issues related to admission withdrawal processes',
                'keywords': 'withdrawal, admission, cancel'
            },
            {
                'name': 'Library related issues',
                'description': 'Issues related to library services and facilities',
                'keywords': 'library, books, resources, access'
            },
            {
                'name': 'Delay in PhD thesis evaluation',
                'description': 'Issues related to PhD thesis evaluation delays',
                'keywords': 'PhD, thesis, evaluation, delay, research'
            },
            {
                'name': 'PhD Scholarship/Fellowship Issues',
                'description': 'Issues related to PhD scholarships and fellowships',
                'keywords': 'PhD, scholarship, fellowship, research funding'
            },
            {
                'name': 'Other Academic Issues',
                'description': 'Any other academic-related grievances not covered above',
                'keywords': 'other, academic, miscellaneous'
            }
        ]

        # Non-Academic Categories from the second image
        non_academic_categories = [
            {
                'name': 'Issue with information in University Brochure',
                'description': 'Issues related to incorrect information in university brochures',
                'keywords': 'brochure, information, incorrect, university'
            },
            {
                'name': 'Issue with information in University Website',
                'description': 'Issues related to incorrect information on university website',
                'keywords': 'website, information, incorrect, online'
            },
            {
                'name': 'Demand of money in excess of that specified in the declared admission policy',
                'description': 'Issues related to excessive fee demands beyond admission policy',
                'keywords': 'money, fee, excess, admission policy, demand'
            },
            {
                'name': 'Refund of Security Fee of Academic/Hostel',
                'description': 'Issues related to security fee refunds',
                'keywords': 'refund, security fee, academic, hostel'
            },
            {
                'name': 'Updation of Scholarship',
                'description': 'Issues related to scholarship updates and modifications',
                'keywords': 'scholarship, update, modification'
            },
            {
                'name': 'Fee/Late payment issues/Fine',
                'description': 'Issues related to fee payments, late payments, and fines',
                'keywords': 'fee, late payment, fine, payment issues'
            },
            {
                'name': 'Reservation Policy in Admission',
                'description': 'Issues related to reservation policies in admissions',
                'keywords': 'reservation, policy, admission, quota'
            },
            {
                'name': 'Social Discrimination',
                'description': 'Issues related to social discrimination',
                'keywords': 'discrimination, social, bias, unfair treatment'
            },
            {
                'name': 'Non-payment or delay in payment of scholarship to any student',
                'description': 'Issues related to scholarship payment delays',
                'keywords': 'scholarship, payment, delay, non-payment'
            },
            {
                'name': 'Harassment and victimization of students including sexual harassment',
                'description': 'Issues related to harassment and victimization',
                'keywords': 'harassment, victimization, sexual harassment, abuse'
            },
            {
                'name': 'Issues related to admission',
                'description': 'General admission-related issues',
                'keywords': 'admission, enrollment, application'
            },
            {
                'name': 'Accounts related Issues',
                'description': 'Issues related to financial accounts and billing',
                'keywords': 'accounts, financial, billing, payment'
            },
            {
                'name': 'Issues related to Inter-Hostel Administration(Hostel & Mess/Food)',
                'description': 'Issues related to hostel administration and mess facilities',
                'keywords': 'hostel, mess, food, accommodation, administration'
            },
            {
                'name': 'Change of Food category/Mess issue',
                'description': 'Issues related to food category changes and mess problems',
                'keywords': 'food category, mess, dining, meal'
            },
            {
                'name': 'Change of Room category',
                'description': 'Issues related to room category changes',
                'keywords': 'room category, accommodation, change'
            },
            {
                'name': 'Issues related to Hygiene/Maintainance/ cleanliness',
                'description': 'Issues related to hygiene, maintenance, and cleanliness',
                'keywords': 'hygiene, maintenance, cleanliness, sanitation'
            },
            {
                'name': 'University Common Area',
                'description': 'Issues related to university common areas',
                'keywords': 'common area, university, shared space'
            },
            {
                'name': 'HouseKeeping & hygiene Issues- University Common Area',
                'description': 'Issues related to housekeeping and hygiene in common areas',
                'keywords': 'housekeeping, hygiene, common area, cleaning'
            },
            {
                'name': 'Student welfare and sports & cultural events related',
                'description': 'Issues related to student welfare, sports, and cultural activities',
                'keywords': 'welfare, sports, cultural events, activities'
            },
            {
                'name': 'Transport Issues',
                'description': 'Issues related to transportation services',
                'keywords': 'transport, bus, vehicle, transportation'
            },
            {
                'name': 'Security (Safety) – lost/theft of any valuable item',
                'description': 'Issues related to security and lost/stolen items',
                'keywords': 'security, safety, lost, theft, valuable'
            },
            {
                'name': 'Healthcare Services',
                'description': 'Issues related to healthcare and medical services',
                'keywords': 'healthcare, medical, health services, clinic'
            },
            {
                'name': 'ID cards (New Cards/Re-issue/error/damage/loss)',
                'description': 'Issues related to ID card services',
                'keywords': 'ID card, new card, reissue, error, damage, loss'
            },
            {
                'name': 'Request/Issues for Sharda student/Parent login ID/password',
                'description': 'Issues related to login credentials for students and parents',
                'keywords': 'login, password, student portal, parent portal'
            },
            {
                'name': 'Login related issues (LMS/I-cloud/Sharda Email)',
                'description': 'Issues related to various login systems',
                'keywords': 'login, LMS, cloud, email, access'
            },
            {
                'name': 'Wi-Fi issue/New registration',
                'description': 'Issues related to Wi-Fi connectivity and registration',
                'keywords': 'wifi, internet, connectivity, registration'
            },
            {
                'name': 'Discrimination on the basis of Minority',
                'description': 'Issues related to minority discrimination',
                'keywords': 'discrimination, minority, bias, unfair'
            },
            {
                'name': 'Ragging related issues',
                'description': 'Issues related to ragging and bullying',
                'keywords': 'ragging, bullying, harassment, intimidation'
            },
            {
                'name': 'Other Non-Academic Issues',
                'description': 'Any other non-academic grievances not covered above',
                'keywords': 'other, non-academic, miscellaneous'
            }
        ]

        # Clear existing categories
        self.stdout.write('Clearing existing categories...')
        Category.objects.all().delete()

        # Add academic categories
        self.stdout.write('Adding academic categories...')
        for cat_data in academic_categories:
            category = Category.objects.create(
                name=cat_data['name'],
                description=cat_data['description'],
                category_type='academic',
                keywords=cat_data['keywords'],
                is_active=True
            )
            self.stdout.write(f'  ✓ Added: {category.name[:50]}...')

        # Add non-academic categories
        self.stdout.write('Adding non-academic categories...')
        for cat_data in non_academic_categories:
            category = Category.objects.create(
                name=cat_data['name'],
                description=cat_data['description'],
                category_type='non_academic',
                keywords=cat_data['keywords'],
                is_active=True
            )
            self.stdout.write(f'  ✓ Added: {category.name[:50]}...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated {len(academic_categories)} academic and {len(non_academic_categories)} non-academic categories!'
            )
        )
