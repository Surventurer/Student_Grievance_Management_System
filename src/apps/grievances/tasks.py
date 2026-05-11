from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.grievances.models import Grievance, EscalationLog
from apps.notifications.models import Notification
from apps.students.models import AdminProfile

@shared_task
def check_sla_and_escalate():
    """Check pending grievances and escalate those that have breached SLA."""
    # Get grievances that might need escalation
    grievances = Grievance.objects.filter(
        status__in=['pending', 'under_review'],
        is_escalated=False,
        is_archived=False
    ).select_related('category', 'assigned_to', 'student')

    now = timezone.now()
    escalated_count = 0

    for grievance in grievances:
        if grievance.category and grievance.category.sla_hours:
            breach_time = grievance.submitted_at + timedelta(hours=grievance.category.sla_hours)
            if now > breach_time:
                # SLA breached, time to escalate
                escalated = escalate_grievance(grievance)
                if escalated:
                    escalated_count += 1
                
    return f"Escalated {escalated_count} grievances."

def escalate_grievance(grievance):
    old_assignee = grievance.assigned_to
    
    # Logic to find the next higher authority.
    # If currently assigned to 'officer', escalate to 'admin' (HOD) of that department.
    # If currently 'admin', escalate to 'superadmin'.
    new_assignee = None
    
    if old_assignee:
        if old_assignee.role_level == 'officer':
            new_assignee = AdminProfile.objects.filter(
                role_level='admin', 
                department=old_assignee.department
            ).first()
        elif old_assignee.role_level == 'admin':
            new_assignee = AdminProfile.objects.filter(role_level='superadmin').first()
            
    # Fallback to superadmin if no suitable HOD found
    if not new_assignee:
        new_assignee = AdminProfile.objects.filter(role_level='superadmin').first()
        
    if not new_assignee or new_assignee == old_assignee:
        # Cannot escalate
        return False

    # Update grievance
    grievance.is_escalated = True
    grievance.escalation_level += 1
    grievance.assigned_to = new_assignee
    grievance.save()

    # Create Escalation Log
    EscalationLog.objects.create(
        grievance=grievance,
        escalated_from=old_assignee,
        escalated_to=new_assignee,
        reason=f"Auto-escalated due to SLA breach ({grievance.category.sla_hours} hours).",
        is_auto_escalated=True
    )

    # Create Notification for the new assignee
    if new_assignee and new_assignee.user:
        Notification.objects.create(
            recipient=new_assignee.user,
            notification_type='escalation',
            title='Grievance Auto-Escalated',
            message=f"Grievance {grievance.grievance_id} has breached SLA and was escalated to you.",
            related_link=f"/admin-panel/grievances/{grievance.id}/"
        )
        
    return True
