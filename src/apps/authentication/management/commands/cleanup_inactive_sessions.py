from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone
from apps.admin_panel.models import SystemSettings


class Command(BaseCommand):
    help = 'Clean up inactive, expired, and corrupted user sessions based on SystemSettings.session_timeout'

    def handle(self, *args, **options):
        settings = SystemSettings.load()
        timeout_seconds = settings.session_timeout * 60
        now_ts = timezone.now().timestamp()

        # 1. Delete standard expired sessions
        expired_qs = Session.objects.filter(expire_date__lt=timezone.now())
        expired_count = expired_qs.count()
        expired_qs.delete()

        # 2. Check remaining sessions for inactivity beyond session_timeout or corrupted data
        inactive_deleted = 0
        corrupted_deleted = 0

        for s in Session.objects.all():
            try:
                data = s.get_decoded()
                if not data:
                    # Empty or invalid HMAC signature from old secret key
                    s.delete()
                    corrupted_deleted += 1
                    continue

                last_act = data.get('last_activity')
                user_id = data.get('_auth_user_id')

                # If session has an authenticated user and last_activity exceeded timeout
                if user_id and last_act and (now_ts - last_act) > timeout_seconds:
                    s.delete()
                    inactive_deleted += 1
                elif user_id and not last_act:
                    # Stale authenticated session without activity timestamp
                    s.delete()
                    inactive_deleted += 1
            except Exception:
                s.delete()
                corrupted_deleted += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully cleaned up sessions: '
                f'{inactive_deleted} inactive (idle > {settings.session_timeout}m), '
                f'{expired_count} expired, '
                f'{corrupted_deleted} corrupted.'
            )
        )
