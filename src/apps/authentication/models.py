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
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin', 'officer']
    
    @property
    def is_superadmin(self):
        return self.role == 'superadmin'


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
