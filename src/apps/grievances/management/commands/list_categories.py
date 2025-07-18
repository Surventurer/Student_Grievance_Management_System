"""
Management command to preview all categories in a nicely formatted way
"""
from django.core.management.base import BaseCommand
from apps.grievances.models import Category


class Command(BaseCommand):
    help = 'Display all categories in a formatted way'

    def handle(self, *args, **options):
        academic_categories = Category.objects.filter(
            category_type='academic', 
            is_active=True
        ).order_by('name')
        
        non_academic_categories = Category.objects.filter(
            category_type='non_academic', 
            is_active=True
        ).order_by('name')

        self.stdout.write(
            self.style.SUCCESS('=== ACADEMIC GRIEVANCE CATEGORIES ===')
        )
        for i, cat in enumerate(academic_categories, 1):
            self.stdout.write(f'{i:2}. {cat.name}')

        self.stdout.write(
            self.style.SUCCESS('\n=== NON-ACADEMIC GRIEVANCE CATEGORIES ===')
        )
        for i, cat in enumerate(non_academic_categories, 1):
            self.stdout.write(f'{i:2}. {cat.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal: {academic_categories.count()} Academic + '
                f'{non_academic_categories.count()} Non-Academic = '
                f'{academic_categories.count() + non_academic_categories.count()} Categories'
            )
        )
