from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.authentication.models import PasswordReset


class Command(BaseCommand):
    help = 'Clean up expired password reset tokens'

    def handle(self, *args, **options):
        # Delete expired or used password reset tokens
        expired_tokens = PasswordReset.objects.filter(
            expires_at__lt=timezone.now()
        )
        used_tokens = PasswordReset.objects.filter(is_used=True)
        
        expired_count = expired_tokens.count()
        used_count = used_tokens.count()
        
        expired_tokens.delete()
        used_tokens.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully cleaned up {expired_count} expired and {used_count} used password reset tokens.'
            )
        )
