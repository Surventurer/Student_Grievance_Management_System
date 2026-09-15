from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.grievances.models import Grievance, EscalationLog
from apps.notifications.models import Notification
from apps.students.models import AdminProfile

@shared_task
def check_sla_and_escalate():
    """Check pending grievances and escalate those that have breached SLA across tiers."""
    # Get grievances that might need escalation (Level 0 or Level 1)
    grievances = Grievance.objects.filter(
        status='pending', # 'pending_student' pauses SLA
        escalation_level__lt=2, # Can escalate up to Level 2 (Superadmin/Appellate)
        is_archived=False
    ).select_related('category', 'assigned_to', 'student')

    now = timezone.now()
    escalated_count = 0

    for grievance in grievances:
        effective_sla = grievance.effective_sla_hours
        pause_td = timedelta(minutes=grievance.accumulated_sla_pause_minutes)

        # Base time for breach calculation:
        # If at Level 1, measure breach from when it escalated to Level 1
        base_time = grievance.submitted_at
        if grievance.escalation_level == 1:
            last_esc = grievance.escalation_logs.order_by('-created_at').first()
            if last_esc:
                base_time = last_esc.created_at

        breach_time = base_time + timedelta(hours=effective_sla) + pause_td
        
        # Simple Business hours handling: If breach time falls on weekend, shift to Monday
        if breach_time.weekday() >= 5: # 5 = Sat, 6 = Sun
            days_to_add = 7 - breach_time.weekday()
            breach_time += timedelta(days=days_to_add)
            
        if now > breach_time:
            # SLA breached, time to escalate
            escalated = escalate_grievance(grievance)
            if escalated:
                escalated_count += 1
                
    return f"Escalated {escalated_count} grievances."

def escalate_grievance(grievance, is_appeal=False, appeal_reason=None):
    """
    Multi-tier escalation:
    Level 0 (Officer) -> Level 1 (Department Admin / HOD)
    Level 1 (Admin) -> Level 2 (Superadmin / Appellate Authority)
    """
    old_assignee = grievance.assigned_to
    current_level = grievance.escalation_level
    new_assignee = None
    target_dept = grievance.department or (old_assignee.department if old_assignee else None)

    if current_level == 0 and not is_appeal:
        # Escalate Level 0 -> Level 1 (Department Admin)
        if target_dept:
            new_assignee = AdminProfile.objects.filter(
                role_level='admin', 
                department__iexact=target_dept
            ).first()
        if not new_assignee and grievance.category and grievance.category.default_admin:
            if grievance.category.default_admin.role_level in ['admin', 'superadmin']:
                new_assignee = grievance.category.default_admin
        if not new_assignee:
            new_assignee = AdminProfile.objects.filter(role_level='superadmin').first()
        next_level = 1
    else:
        # Escalate Level 1 -> Level 2 (Superadmin / Appellate Authority) or direct appeal
        new_assignee = AdminProfile.objects.filter(role_level='superadmin').first()
        next_level = 2

    if not new_assignee or (new_assignee == old_assignee and current_level == next_level):
        # Cannot escalate further
        return False

    # Update grievance
    grievance.is_escalated = True
    grievance.escalation_level = next_level
    grievance.assigned_to = new_assignee
    grievance.save()

    # Determine reason
    if is_appeal:
        reason_text = f"Escalated to Level {next_level} following student appeal: {appeal_reason or 'No reason provided'}"
    else:
        reason_text = f"Auto-escalated to Level {next_level} due to SLA breach ({grievance.effective_sla_hours} hours, Priority: {grievance.get_priority_display()})."

    # Create Escalation Log
    EscalationLog.objects.create(
        grievance=grievance,
        escalated_from=old_assignee,
        escalated_to=new_assignee,
        reason=reason_text,
        is_auto_escalated=not is_appeal
    )

    # Create Notification for the new assignee
    if new_assignee and new_assignee.user:
        Notification.objects.create(
            recipient=new_assignee.user,
            notification_type='escalation',
            title=f"Grievance Escalated to Level {next_level}",
            message=f"Grievance {grievance.grievance_id} ({grievance.title}) has been escalated to you as Level {next_level} authority.",
            related_link=f"/admin-panel/grievances/{grievance.id}/"
        )
        
        # Send email alert to new assignee
        if new_assignee.user.email:
            from django.core.mail import send_mail
            from django.conf import settings
            try:
                subject = f"URGENT: Grievance {grievance.grievance_id} Escalated to Level {next_level}"
                body = (
                    f"Dear {new_assignee.user.get_full_name() or 'Administrator'},\n\n"
                    f"Grievance {grievance.grievance_id} ('{grievance.title}') has been escalated to your attention.\n"
                    f"Reason: {reason_text}\n"
                    f"Priority: {grievance.get_priority_display()}\n\n"
                    f"Please review and take prompt action in the admin portal.\n\n"
                    f"Student Grievance Management System"
                )
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [new_assignee.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending escalation email: {e}")
        
    return True
