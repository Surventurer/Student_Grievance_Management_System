from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.grievances.models import Grievance
from apps.admin_panel.models import SystemSettings
from apps.students.models import AdminProfile
from apps.notifications.models import Notification

class Command(BaseCommand):
    help = 'Process SLA breaches and auto-resolutions based on System Settings'

    def handle(self, *args, **options):
        settings = SystemSettings.load()
        now = timezone.now()
        
        # 1. Auto-Resolution
        resolve_threshold = now - timedelta(days=settings.auto_resolve_days)
        # Find grievances that are 'in_progress' or 'pending' but haven't been updated in `auto_resolve_days`
        stale_grievances = Grievance.objects.filter(
            status__in=['pending', 'in_progress'],
            updated_at__lt=resolve_threshold
        )
        
        resolved_count = 0
        for g in stale_grievances:
            g.status = 'resolved'
            g.admin_remarks = f"Auto-resolved after {settings.auto_resolve_days} days of inactivity."
            g.save(update_fields=['status', 'admin_remarks', 'updated_at'])
            resolved_count += 1
            
            # Notify student
            Notification.objects.create(
                recipient=g.student.user,
                title="Grievance Auto-Resolved",
                message=f"Your grievance '{g.title}' has been auto-resolved due to inactivity.",
                related_link=f"/students/grievance/{g.id}/"
            )
            
        self.stdout.write(self.style.SUCCESS(f"Auto-resolved {resolved_count} grievances."))

        # 2. SLA Escalation
        escalation_threshold = now - timedelta(days=settings.escalation_threshold)
        breached_grievances = Grievance.objects.filter(
            status__in=['pending', 'in_progress'],
            submitted_at__lt=escalation_threshold
        )
        
        escalated_count = 0
        for g in breached_grievances:
            # If not already escalated or notified recently (simple check)
            if settings.sla_breach_action in ['escalate', 'both']:
                # Find higher authority
                superadmins = AdminProfile.objects.filter(role_level='superadmin')
                if superadmins.exists():
                    g.assigned_to = superadmins.first()
                    g.priority = 'urgent'
                    g.save(update_fields=['assigned_to', 'priority', 'updated_at'])
                    escalated_count += 1
                    
                    if settings.sla_breach_action == 'both':
                        Notification.objects.create(
                            recipient=g.assigned_to.user,
                            title="SLA Breach Escalation",
                            message=f"Grievance '{g.title}' breached SLA and was auto-escalated.",
                            related_link=f"/admin-panel/grievances/{g.id}/"
                        )
            elif settings.sla_breach_action == 'notify':
                # Just notify assigned officer
                if g.assigned_to:
                    Notification.objects.create(
                        recipient=g.assigned_to.user,
                        title="SLA Breach Warning",
                        message=f"Grievance '{g.title}' has breached its SLA threshold of {settings.escalation_threshold} days.",
                        related_link=f"/admin-panel/grievances/{g.id}/"
                    )
                    
        self.stdout.write(self.style.SUCCESS(f"Processed {breached_grievances.count()} SLA breaches (Escalated {escalated_count})."))

