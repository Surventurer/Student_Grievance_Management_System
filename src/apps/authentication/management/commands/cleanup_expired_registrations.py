from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.authentication.models import TemporaryRegistration


class Command(BaseCommand):
    help = 'Clean up expired temporary registrations'
    
    def handle(self, *args, **options):
        # Delete expired temporary registrations
        expired_count = TemporaryRegistration.objects.filter(
            expires_at__lt=timezone.now()
        ).count()
        
        TemporaryRegistration.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleaned up {expired_count} expired registrations')
        )
