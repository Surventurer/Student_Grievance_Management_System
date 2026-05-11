from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.authentication.models import AdminLoginOTP


class Command(BaseCommand):
    help = 'Clean up expired admin login OTPs'
    
    def handle(self, *args, **options):
        # Delete expired admin login OTPs
        expired_count = AdminLoginOTP.objects.filter(
            expires_at__lt=timezone.now()
        ).count()
        
        AdminLoginOTP.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleaned up {expired_count} expired admin OTPs')
        )
