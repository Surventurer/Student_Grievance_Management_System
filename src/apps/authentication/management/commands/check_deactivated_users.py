"""
Debug command to check user deactivation status
"""
from django.core.management.base import BaseCommand
from apps.authentication.models import User

class Command(BaseCommand):
    help = 'Check user deactivation status and reasons'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Check specific user email')

    def handle(self, *args, **options):
        if options['email']:
            try:
                user = User.objects.get(email=options['email'])
                self.stdout.write(f"User: {user.email}")
                self.stdout.write(f"Is Active: {user.is_active}")
                self.stdout.write(f"Deactivation Reason: '{user.deactivation_reason}'")
                self.stdout.write(f"Role: {user.role}")
            except User.DoesNotExist:
                self.stdout.write(f"User with email {options['email']} not found")
        else:
            # Show all inactive users
            inactive_users = User.objects.filter(is_active=False)
            self.stdout.write(f"Found {inactive_users.count()} inactive users:")
            for user in inactive_users:
                self.stdout.write(f"- {user.email}: '{user.deactivation_reason}'")
