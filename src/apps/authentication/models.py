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
        extra_fields.setdefault('is_email_verified', True)
        
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
        """Get display name - from admin profile name, student profile name, or email"""
        if hasattr(self, 'admin_profile') and self.admin_profile.name:
            return self.admin_profile.name
        if hasattr(self, 'student_profile') and self.student_profile.name:
            return self.student_profile.name
        return self.email
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin']
    
    @property 
    def is_officer(self):
        return self.role == 'officer'
    
    @property
    def is_admin_or_officer(self):
        return self.role in ['admin', 'superadmin', 'officer']
    
    @property
    def is_superadmin(self):
        return self.role == 'superadmin'
    
    @property
    def assigned_department(self):
        """Get the department this user is assigned to"""
        if self.role == 'superadmin':
            return None  # Superadmin has access to all departments
        elif self.role == 'admin':
            # Admins are assigned as HOD of departments
            return self.headed_departments.first()
        elif self.role == 'officer':
            # Officers are assigned through AdminProfile
            try:
                if hasattr(self, 'admin_profile') and self.admin_profile:
                    dept_name = self.admin_profile.department
                    from apps.students.models import Department
                    return Department.objects.filter(name=dept_name).first()
            except Exception as e:
                print(f"Error getting officer department: {e}")
            return None
        return None
    
    @property
    def department_name(self):
        """Get the name of the department this user manages"""
        dept = self.assigned_department
        return dept.name if dept else None
    
    def get_accessible_students(self):
        """Get students this user can access based on their role"""
        if self.is_superadmin:
            # Superadmin can see all students
            from apps.students.models import StudentProfile
            return StudentProfile.objects.all()
        elif self.role in ['admin', 'officer'] and self.assigned_department:
            # Department admin/hod can only see their department students
            from apps.students.models import StudentProfile
            return StudentProfile.objects.filter(department=self.assigned_department.name)
        else:
            # Students and others see none
            from apps.students.models import StudentProfile
            return StudentProfile.objects.none()
    
    def get_accessible_grievances(self):
        """Get grievances this user can access based on their role"""
        if self.is_superadmin:
            # Superadmin can see all grievances
            from apps.grievances.models import Grievance
            return Grievance.objects.filter(is_archived=False)
        elif self.role in ['admin', 'officer'] and self.assigned_department:
            # Department admin/hod can only see grievances from their department students
            from apps.grievances.models import Grievance
            accessible_students = self.get_accessible_students()
            return Grievance.objects.filter(student__in=accessible_students, is_archived=False)
        else:
            # Students see their own grievances
            from apps.grievances.models import Grievance
            if hasattr(self, 'student_profile') and self.student_profile:
                return Grievance.objects.filter(student=self.student_profile, is_archived=False)
            return Grievance.objects.none()
    
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
