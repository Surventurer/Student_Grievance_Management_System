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
