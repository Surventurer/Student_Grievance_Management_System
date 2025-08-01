from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model matching the exact schema: email, password, role, created_at"""
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
        ('officer', 'Grievance Officer'),
    ]
    
    # Schema fields only - matching your database schema exactly
    email = models.EmailField(unique=True)  # STRING - Unique email address
    # password field inherited from AbstractBaseUser - STRING - Hashed password
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')  # STRING - User role (e.g., 'student')
    created_at = models.DateTimeField(auto_now_add=True)  # DATETIME - Timestamp of registration
    
    # Required fields for Django admin functionality
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    deactivation_reason = models.TextField(blank=True, null=True, help_text="Reason for account deactivation")
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email
    
    def get_display_name(self):
        """Get display name - either from student profile or email"""
        if hasattr(self, 'student_profile') and self.student_profile.name:
            return self.student_profile.name
        return self.email
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin', 'officer']
    
    @property
    def is_superadmin(self):
        return self.role == 'superadmin'
    
    def get_full_name(self):
        """Get full name from student profile if available, otherwise return email"""
        if hasattr(self, 'student_profile') and self.student_profile:
            return self.student_profile.name or self.email
        if hasattr(self, 'admin_profile') and self.admin_profile:
            return f"{self.admin_profile.user.email} ({self.admin_profile.role_level})"
        return self.email

    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        permission_map = {
            'superadmin': [
                'view_all_data', 'manage_users', 'manage_system', 'manage_categories',
                'view_audit_logs', 'manage_auto_assignment', 'delete_users', 
                'modify_roles', 'system_backup', 'database_access'
            ],
            'admin': [
                'view_department_data', 'manage_department_students', 'manage_department_grievances',
                'assign_grievances', 'view_department_reports', 'manage_department_categories'
            ],
            'officer': [
                'view_assigned_grievances', 'update_grievance_status', 'add_comments',
                'view_assigned_students', 'update_own_profile'
            ],
            'student': [
                'submit_grievances', 'view_own_grievances', 'update_own_profile',
                'provide_feedback', 'upload_documents'
            ]
        }
        
        user_permissions = permission_map.get(self.role, [])
        return permission in user_permissions
    
    @property
    def role_display(self):
        """Get human-readable role display"""
        return self.get_role_display()
    
    def can_access_grievance(self, grievance):
        """Check if user can access a specific grievance"""
        if self.role == 'superadmin':
            return True
        elif self.role == 'admin':
            try:
                admin_profile = self.admin_profile
                return (grievance.student.department == admin_profile.department or 
                       grievance.department == admin_profile.department)
            except:
                return False
        elif self.role == 'officer':
            try:
                admin_profile = self.admin_profile
                return grievance.assigned_to == admin_profile
            except:
                return False
        elif self.role == 'student':
            try:
                return grievance.student == self.student_profile
            except:
                return False
        return False


class EmailVerification(models.Model):
    """Model for email verification OTP"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"OTP for {self.user.email}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class PasswordReset(models.Model):
    """Model for password reset tokens"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=100, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class AdminLoginOTP(models.Model):
    """Model for admin login OTP verification"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_login_otps')
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    session_key = models.CharField(max_length=100, null=True, blank=True)  # To track login session
    
    def __str__(self):
        return f"Admin Login OTP for {self.user.email}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class TemporaryRegistration(models.Model):
    """Model to store registration data temporarily until email verification"""
    
    # Personal Information
    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=50)
    email = models.EmailField()
    password = models.CharField(max_length=255)  # Will store hashed password
    contact_no = models.CharField(max_length=15)
    school = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    
    # Verification
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"Temp registration for {self.email}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def create_actual_user(self):
        """Create the actual User and StudentProfile after verification"""
        from apps.students.models import StudentProfile
        from django.contrib.auth.hashers import make_password
        
        # Create User
        user = User.objects.create(
            email=self.email,
            password=self.password,  # Password is already hashed
            role='student',
            is_email_verified=True  # Since they verified via temp registration
        )
        
        # Create StudentProfile
        student_profile = StudentProfile.objects.create(
            user=user,
            name=self.name,
            student_id=self.student_id,
            school=self.school,
            department=self.department,
            contact_no=self.contact_no
        )
        
        return user, student_profile
