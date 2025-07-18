from django.db import models
from django.conf import settings
from apps.students.models import StudentProfile, AdminProfile
import uuid


class Category(models.Model):
    """Grievance category model"""
    
    CATEGORY_TYPES = [
        ('academic', 'Academic'),
        ('non_academic', 'Non-Academic'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    default_admin = models.ForeignKey(AdminProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_categories')
    keywords = models.TextField(blank=True, null=True, help_text="Keywords for auto-assignment (comma-separated)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['category_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"
    
    @property
    def is_other_category(self):
        """Check if this is an 'Other' category"""
        return self.name.lower().startswith('other')


class Grievance(models.Model):
    """Grievance model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='grievances')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='grievances')
    department = models.CharField(max_length=100, blank=True, null=True, help_text="Department related to grievance")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    assigned_to = models.ForeignKey(AdminProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_grievances')
    is_anonymous = models.BooleanField(default=False)
    expected_resolution_date = models.DateTimeField(null=True, blank=True)
    actual_resolution_date = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', 'submitted_at']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.student.student_id}"
    
    @property
    def grievance_id(self):
        """Generate a human-readable grievance ID"""
        return f"GRV-{str(self.id)[:8].upper()}"
    
    def auto_assign(self):
        """Auto-assign grievance based on category and keywords"""
        if self.category.default_admin:
            self.assigned_to = self.category.default_admin
            self.save()
        elif self.category.keywords:
            # Simple keyword matching for auto-assignment
            keywords = [k.strip().lower() for k in self.category.keywords.split(',')]
            description_lower = self.description.lower()
            title_lower = self.title.lower()
            
            # Check if any keyword matches
            for keyword in keywords:
                if keyword in description_lower or keyword in title_lower:
                    # Find admin with matching department or expertise
                    potential_admin = AdminProfile.objects.filter(
                        department=self.category.name,
                        role_level__in=['officer', 'dept_admin']
                    ).first()
                    
                    if potential_admin:
                        self.assigned_to = potential_admin
                        self.save()
                        break


class GrievanceAttachment(models.Model):
    """Grievance attachment model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='grievance_attachments/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.file_name} - {self.grievance.title}"


class GrievanceComment(models.Model):
    """Grievance comment/communication model"""
    
    COMMENT_TYPES = [
        ('comment', 'Comment'),
        ('status_update', 'Status Update'),
        ('internal_note', 'Internal Note'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES, default='comment')
    message = models.TextField()
    is_internal = models.BooleanField(default=False)  # Only visible to admins
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Comment by {self.user.email} on {self.grievance.title}"


class GrievanceStatusHistory(models.Model):
    """Track grievance status changes"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Status Histories"
    
    def __str__(self):
        return f"{self.grievance.title}: {self.previous_status} → {self.new_status}"


class GrievanceAssignmentHistory(models.Model):
    """Track grievance assignment changes"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='assignment_history')
    previous_assignee = models.ForeignKey(AdminProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_assignments')
    new_assignee = models.ForeignKey(AdminProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Assignment Histories"
    
    def __str__(self):
        prev_name = self.previous_assignee.user.get_full_name() if self.previous_assignee else "Unassigned"
        new_name = self.new_assignee.user.get_full_name() if self.new_assignee else "Unassigned"
        return f"{self.grievance.title}: {prev_name} → {new_name}"


class Feedback(models.Model):
    """Grievance feedback model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.OneToOneField(Grievance, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comments = models.TextField(blank=True, null=True)
    is_satisfied = models.BooleanField(default=True)
    improvement_suggestions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback for {self.grievance.title} - {self.rating}/5"


class AuditLog(models.Model):
    """Audit log for tracking all admin actions"""
    
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('assign', 'Assign'),
        ('status_change', 'Status Change'),
        ('comment', 'Comment'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    target_model = models.CharField(max_length=50)  # Model name
    target_id = models.CharField(max_length=100)  # ID of affected object
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.target_model}"


class GrievanceOTPVerification(models.Model):
    """OTP verification for grievance submission"""
    
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=50, default='grievance_submission')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"OTP for {self.email} - {self.purpose}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > (self.created_at + timedelta(minutes=10))
    
    class Meta:
        ordering = ['-created_at']
