from django.db import models
from django.conf import settings
from apps.grievances.models import GrievanceComment
import uuid


class ReadNotification(models.Model):
    """Track which notifications have been read by students"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='read_notifications')
    comment = models.ForeignKey(GrievanceComment, on_delete=models.CASCADE, related_name='read_by')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'comment']  # Prevent duplicate entries
        indexes = [
            models.Index(fields=['student', 'read_at']),
            models.Index(fields=['comment']),
        ]
    
    def __str__(self):
        return f"{self.student.email} read comment {self.comment.id}"


class Notification(models.Model):
    """General in-app notification system"""
    
    NOTIFICATION_TYPES = [
        ('status_update', 'Status Update'),
        ('new_assignment', 'New Assignment'),
        ('escalation', 'Escalation'),
        ('appeal', 'Appeal'),
        ('system', 'System Alert'),
        ('comment', 'New Comment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    related_link = models.CharField(max_length=255, blank=True, null=True, help_text="URL or path to navigate to")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} for {self.recipient.email}: {self.title}"
