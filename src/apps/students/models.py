from django.db import models
from django.conf import settings
import uuid


class School(models.Model):
    """School model as per database schema"""
    
    id = models.AutoField(primary_key=True)  # UUID/Auto Primary key
    name = models.CharField(max_length=200, unique=True)  # Name of the school (unique)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "School"
        verbose_name_plural = "Schools"


class Department(models.Model):
    """Department model as per database schema"""
    
    id = models.AutoField(primary_key=True)  # UUID/Auto Primary key  
    name = models.CharField(max_length=100)  # Name of the department
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='departments', null=True, blank=True)  # Links department to a school (nullable for migration)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}" + (f" - {self.school.name}" if self.school else "")
    
    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"


class StudentProfile(models.Model):
    """Student profile model as per database schema"""
    
    # Using user relationship to get email (FK to User.email - One-to-One)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=100, blank=True, null=True)  # Full name of the student (nullable for migration)
    student_id = models.CharField(max_length=50, unique=True)  # Student enrollment Id
    school = models.CharField(max_length=200, blank=True, null=True)  # Name of the School (optional, not in doc)
    department = models.CharField(max_length=100)  # Department name
    contact_no = models.CharField(max_length=15, blank=True, null=True)  # Contact number (nullable for migration)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student_id} - {self.name or 'No Name'}"
    
    @property
    def email(self):
        """Get email from related user"""
        return self.user.email
    
    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"


class AdminProfile(models.Model):
    """Admin profile model - keeping existing structure"""
    
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
