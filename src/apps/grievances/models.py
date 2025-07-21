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
    auto_assign_enabled = models.BooleanField(default=True, help_text="Enable automatic assignment for this category")
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
    
    def get_assigned_hod(self, department=None):
        """Get the assigned HOD for this category based on department"""
        if department:
            assignment = CategoryAssignment.objects.filter(
                category=self,
                department__icontains=department,
                is_active=True
            ).first()
            if assignment:
                return assignment.assigned_admin
        
        # Fallback to default admin
        return self.default_admin


class CategoryAssignment(models.Model):
    """Model to assign HODs/Admins to categories based on departments"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='assignments')
    assigned_admin = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, related_name='category_assignments')
    department = models.CharField(max_length=100, help_text="Department this assignment applies to")
    school = models.CharField(max_length=200, blank=True, null=True, help_text="School this assignment applies to")
    priority_level = models.IntegerField(default=1, help_text="Higher number = higher priority for matching")
    is_active = models.BooleanField(default=True)
    auto_assign_keywords = models.TextField(blank=True, null=True, help_text="Additional keywords for auto-assignment (comma-separated)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-priority_level', 'category__name', 'department']
        unique_together = ['category', 'department', 'assigned_admin']
    
    def __str__(self):
        return f"{self.category.name} → {self.assigned_admin} ({self.department})"


class Grievance(models.Model):
    """Grievance model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
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
        """Enhanced auto-assign grievance based on category assignments and department"""
        from apps.admin_panel.audit_utils import log_custom_action
        
        # Skip if already assigned
        if self.assigned_to:
            return
        
        # Skip if auto-assignment is disabled for this category
        if not self.category.auto_assign_enabled:
            return
        
        assigned_admin = None
        assignment_reason = "No assignment found"
        
        # Try to get department from student profile
        try:
            student_department = self.student.department if hasattr(self.student, 'department') else None
        except Exception:
            student_department = None
        
        # Step 1: Try to find specific department assignment
        if student_department:
            assignment = CategoryAssignment.objects.filter(
                category=self.category,
                department__iexact=student_department,
                is_active=True
            ).order_by('-priority_level').first()
            
            if assignment:
                assigned_admin = assignment.assigned_admin
                assignment_reason = f"Department-specific assignment: {student_department}"
        
        # Step 2: Try keyword matching in CategoryAssignment
        if not assigned_admin:
            assignments_with_keywords = CategoryAssignment.objects.filter(
                category=self.category,
                is_active=True,
                auto_assign_keywords__isnull=False
            ).exclude(auto_assign_keywords='')
            
            description_lower = self.description.lower()
            title_lower = self.title.lower()
            
            for assignment in assignments_with_keywords:
                try:
                    keywords = [k.strip().lower() for k in assignment.auto_assign_keywords.split(',')]
                    for keyword in keywords:
                        if keyword and (keyword in description_lower or keyword in title_lower):
                            assigned_admin = assignment.assigned_admin
                            assignment_reason = f"Keyword match: '{keyword}' → {assignment.department}"
                            break
                    if assigned_admin:
                        break
                except Exception as e:
                    print(f"Error processing keywords for assignment {assignment.id}: {e}")
                    continue
        
        # Step 3: Fallback to category default admin
        if not assigned_admin and self.category.default_admin:
            assigned_admin = self.category.default_admin
            assignment_reason = "Category default admin"
        
        # Step 4: Fallback to any available admin for the department
        if not assigned_admin and student_department:
            try:
                fallback_admin = AdminProfile.objects.filter(
                    department__iexact=student_department,
                    role_level__in=['admin', 'officer']
                ).first()
                
                if fallback_admin:
                    assigned_admin = fallback_admin
                    assignment_reason = f"Department fallback: {student_department}"
            except Exception as e:
                print(f"Error finding fallback admin: {e}")
        
        # Assign and save
        if assigned_admin:
            self.assigned_to = assigned_admin
            self.save()
            
            # Create audit log for auto-assignment
            try:
                # Import here to avoid circular imports
                from apps.grievances.models import AuditLog
                AuditLog.objects.create(
                    user=assigned_admin.user,
                    action='assign',
                    target_model='Grievance',
                    target_id=str(self.id),
                    description=f"Auto-assigned grievance {self.grievance_id} to {assigned_admin}. Reason: {assignment_reason}",
                    ip_address='127.0.0.1',  # System assignment
                    user_agent='System Auto-Assignment'
                )
            except Exception as e:
                print(f"Failed to create audit log for auto-assignment: {e}")
            
            return assigned_admin, assignment_reason
        
        return None, "No suitable admin found for assignment"


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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
