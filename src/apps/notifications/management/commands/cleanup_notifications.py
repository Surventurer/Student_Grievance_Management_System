from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.notifications.models import ReadNotification


class Command(BaseCommand):
    help = 'Clean up old read notifications (older than 30 days)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep read notifications (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_notifications = ReadNotification.objects.filter(read_at__lt=cutoff_date)
        count = old_notifications.count()
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[DRY RUN] Would delete {count} read notifications older than {days} days'
                )
            )
        else:
            deleted_count, _ = old_notifications.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} read notifications older than {days} days'
                )
            )
