from django.db import models
from django.conf import settings
import uuid


class StudentProfile(models.Model):
    """Student profile model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=15, blank=True, null=True)
    year_of_study = models.CharField(max_length=20, blank=True, null=True)
    course = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name()}"
    
    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"


class AdminProfile(models.Model):
    """Admin profile model"""
    
    ROLE_LEVEL_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('officer', 'Grievance Officer'),
        ('dept_admin', 'Department Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile')
    role_level = models.CharField(max_length=20, choices=ROLE_LEVEL_CHOICES)
    department = models.CharField(max_length=100, blank=True, null=True)
    employee_id = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    office_location = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role_level}"
    
    class Meta:
        verbose_name = "Admin Profile"
        verbose_name_plural = "Admin Profiles"


class Department(models.Model):
    """Department model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    head_of_department = models.ForeignKey(AdminProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments')
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"


class UserActivity(models.Model):
    """Track user login activity"""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    is_successful = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.login_time}"
    
    class Meta:
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ['-login_time']
