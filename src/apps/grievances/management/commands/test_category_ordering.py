"""
Management command to test category ordering
"""
from django.core.management.base import BaseCommand
from apps.grievances.models import Category


class Command(BaseCommand):
    help = 'Test category ordering with Other categories at the end'

    def handle(self, *args, **options):
        for category_type in ['academic', 'non_academic']:
            self.stdout.write(
                self.style.SUCCESS(f'\n=== {category_type.upper()} CATEGORIES (Alphabetical + Other at End) ===')
            )
            
            categories = Category.objects.filter(category_type=category_type, is_active=True)
            
            # Separate "Other" categories from regular categories
            other_categories = []
            regular_categories = []
            
            for c in categories:
                if c.name.lower().startswith('other'):
                    other_categories.append(c)
                else:
                    regular_categories.append(c)
            
            # Sort regular categories alphabetically
            regular_categories.sort(key=lambda x: x.name.lower())
            
            # Sort other categories alphabetically (in case there are multiple)
            other_categories.sort(key=lambda x: x.name.lower())
            
            # Combine: regular categories first, then "Other" categories at the end
            sorted_categories = regular_categories + other_categories
            
            for i, cat in enumerate(sorted_categories, 1):
                marker = " ⭐" if cat.name.lower().startswith('other') else ""
                self.stdout.write(f'{i:2}. {cat.name}{marker}')
        
        self.stdout.write(
            self.style.SUCCESS('\n⭐ = Other categories (at the end)')
        )
