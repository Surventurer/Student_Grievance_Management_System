from django.db import models
from django.conf import settings
import uuid


class School(models.Model):
    """School model as per database schema - Enhanced for CRUD management"""
    
    id = models.AutoField(primary_key=True)  # UUID/Auto Primary key
    name = models.CharField(max_length=200, unique=True)  # Name of the school (unique)
    code = models.CharField(max_length=20, blank=True, null=True, unique=True)  # School code (optional)
    description = models.TextField(blank=True, null=True)  # School description
    address = models.TextField(blank=True, null=True)  # School address
    phone = models.CharField(max_length=15, blank=True, null=True)  # Contact phone
    email = models.EmailField(blank=True, null=True)  # Contact email
    website = models.URLField(blank=True, null=True)  # School website
    established_year = models.IntegerField(blank=True, null=True)  # Year established
    accreditation = models.CharField(max_length=100, blank=True, null=True)  # Accreditation info
    campus_size = models.CharField(max_length=100, blank=True, null=True)  # Campus size
    student_capacity = models.IntegerField(blank=True, null=True)  # Student capacity
    is_active = models.BooleanField(default=True)  # Active status
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "School"
        verbose_name_plural = "Schools"


class Department(models.Model):
    """Department model as per database schema - Core fields only"""
    
    id = models.AutoField(primary_key=True)  # UUID/Auto Primary key  
    name = models.CharField(max_length=100)  # Name of the department
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='departments', null=True, blank=True)  # Links department to a school (nullable for migration)
    head_of_department = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments')  # HOD
    is_active = models.BooleanField(default=True)  # Active status
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}" + (f" - {self.school.name}" if self.school else "")
    
    @property
    def students(self):
        """Get students in this department"""
        return StudentProfile.objects.filter(department=self.name)
    
    @property 
    def grievances(self):
        """Get grievances from students in this department"""
        from apps.grievances.models import Grievance
        return Grievance.objects.filter(student__department=self.name)
        
    @property
    def category_assignments(self):
        """Get category assignments for this department"""
        from apps.grievances.models import CategoryAssignment
        return CategoryAssignment.objects.filter(department__icontains=self.name)
    
    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"


class StudentProfile(models.Model):
    """Student profile model as per database schema"""
    
    # Using user relationship to get email (FK to User.email - One-to-One)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=100, blank=True, null=True)  # Full name of the student (nullable for migration)
    student_id = models.CharField(max_length=50, unique=True)  # Student enrollment Id
    school = models.CharField(max_length=200)  # Name of the School (required)
    department = models.CharField(max_length=100)  # Department name (required)
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
        ('admin', 'Department Admin'),  # Updated to match User model
        ('officer', 'Grievance Officer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile')
    name = models.CharField(max_length=100, blank=True, null=True)  # Added name field
    role_level = models.CharField(max_length=20, choices=ROLE_LEVEL_CHOICES)
    department = models.CharField(max_length=100)  # Department is required for admin/officers
    employee_id = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    office_location = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name or self.user.email} - {self.get_role_level_display()}"
    
    def save(self, *args, **kwargs):
        """Ensure user role matches admin role_level"""
        if self.user_id:
            # Sync user role with admin role_level
            self.user.role = self.role_level
            self.user.save()
        super().save(*args, **kwargs)
    
    @property
    def can_manage_department(self):
        """Check if admin can manage department-level operations"""
        return self.role_level in ['superadmin', 'admin']
    
    @property 
    def can_assign_grievances(self):
        """Check if admin can assign grievances"""
        return self.role_level in ['superadmin', 'admin']
    
    @property
    def accessible_departments(self):
        """Get list of departments this admin can access"""
        if self.role_level == 'superadmin':
            return Department.objects.all()
        elif self.role_level == 'admin' and self.department:
            return Department.objects.filter(name=self.department)
        return Department.objects.none()
    
    class Meta:
        verbose_name = "Admin Profile"
        verbose_name_plural = "Admin Profiles"
