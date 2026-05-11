from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task
def send_email_notification(subject, recipient_email, template_name, context):
    """
    Send email notification using Celery for async processing
    """
    try:
        # Render the email template
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"Email sent successfully to {recipient_email}"
    except Exception as e:
        return f"Failed to send email to {recipient_email}: {str(e)}"


@shared_task
def send_grievance_notification(grievance_id, notification_type):
    """
    Send notifications for grievance updates
    """
    from apps.grievances.models import Grievance
    
    try:
        grievance = Grievance.objects.get(id=grievance_id)
        
        if notification_type == 'new_submission':
            # Notify admin of new grievance
            if grievance.assigned_to:
                subject = f"New Grievance Assigned: {grievance.title}"
                recipient = grievance.assigned_to.user.email
                template = 'emails/new_grievance_admin.html'
                context = {
                    'grievance': grievance,
                    'admin': grievance.assigned_to,
                }
                return send_email_notification(subject, recipient, template, context)
        
        elif notification_type == 'status_update':
            # Notify student of status change
            subject = f"Grievance Update: {grievance.title}"
            recipient = grievance.student.user.email
            template = 'emails/grievance_status_update.html'
            context = {
                'grievance': grievance,
                'student': grievance.student,
            }
            return send_email_notification(subject, recipient, template, context)
            
    except Grievance.DoesNotExist:
        return f"Grievance with ID {grievance_id} not found"
    except Exception as e:
        return f"Error processing notification: {str(e)}"


@shared_task
def cleanup_old_sessions():
    """
    Cleanup expired sessions and temporary data
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    from apps.authentication.models import EmailVerification, PasswordReset
    from datetime import timedelta
    
    try:
        # Clean expired sessions
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        
        # Clean expired email verifications (older than 24 hours)
        EmailVerification.objects.filter(
            created_at__lt=timezone.now() - timedelta(hours=24)
        ).delete()
        
        # Clean expired password resets (older than 24 hours)
        PasswordReset.objects.filter(
            created_at__lt=timezone.now() - timedelta(hours=24)
        ).delete()
        
        return "Cleanup completed successfully"
    except Exception as e:
        return f"Cleanup failed: {str(e)}"
