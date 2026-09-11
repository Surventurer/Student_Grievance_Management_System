from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from apps.students.models import StudentProfile, School, Department
from .models import TemporaryRegistration

User = get_user_model()


class StudentRegistrationForm(forms.Form):
    """Student Registration Form matching the database schema"""
    
    # Student Profile fields
    name = forms.CharField(
        max_length=100,
        validators=[RegexValidator(
            regex=r'^[a-zA-Z\s]+$',
            message='Name can only contain letters and spaces. Numbers and special characters are not allowed.'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    
    student_id = forms.CharField(
        label='System ID',
        max_length=10,
        min_length=10,
        validators=[RegexValidator(
            regex=r'^\d{10}$',
            message='System ID must be exactly 10 digits.'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 10-digit System ID'
        })
    )
    
    # User fields
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    
    contact_no = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your contact number'
        })
    )
    
    # School and Department (linked)
    school = forms.ModelChoiceField(
        queryset=School.objects.filter(is_active=True),
        empty_label="Select School",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_school'
        })
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),  # Will be populated via AJAX
        empty_label="Select Department",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_department'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Always set department queryset based on school selection
        school_id = None
        if 'school' in self.data:
            try:
                school_id = int(self.data.get('school'))
            except (ValueError, TypeError):
                school_id = None
        elif self.initial.get('school'):
            try:
                school_id = int(self.initial.get('school').id)
            except (AttributeError, ValueError, TypeError):
                school_id = None
        if school_id:
            self.fields['department'].queryset = Department.objects.filter(
                school=school_id, 
                school__is_active=True, 
                is_active=True
            )
        else:
            self.fields['department'].queryset = Department.objects.none()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email
        email = email.strip().lower()
        
        # Universal email format validation
        import re
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            raise forms.ValidationError("Please enter a valid email address.")
        
        # Check against allowed email domain(s) from SystemSettings if configured
        try:
            from apps.admin_panel.models import SystemSettings
            settings_obj = SystemSettings.load()
            if settings_obj and settings_obj.allowed_email_domains:
                allowed_domains = [d.strip().lower() for d in settings_obj.allowed_email_domains.split(',') if d.strip()]
                if allowed_domains:
                    email_domain = email.split('@')[-1]
                    if not any(email_domain == d or email_domain.endswith('.' + d) for d in allowed_domains):
                        raise forms.ValidationError(f"Please use your school/university email ending with {', '.join(allowed_domains)}.")
        except forms.ValidationError:
            raise
        except Exception:
            pass
            
        # Check both actual users and temporary registrations
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        
        existing_temp = TemporaryRegistration.objects.filter(email=email, is_verified=False).first()
        if existing_temp:
            if existing_temp.is_expired:
                existing_temp.delete()
            else:
                raise forms.ValidationError("A registration with this email is already pending verification. Please complete verification or wait for the OTP to expire.")
        return email
    
    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if not student_id:
            return student_id
        student_id = student_id.strip()
        if not student_id.isdigit() or len(student_id) != 10:
            raise forms.ValidationError("System ID must be exactly 10 digits.")
            
        # Check both actual student profiles and temporary registrations
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("A student with this System ID already exists.")
        
        existing_temp = TemporaryRegistration.objects.filter(student_id=student_id, is_verified=False).first()
        if existing_temp:
            if existing_temp.is_expired:
                existing_temp.delete()
            else:
                raise forms.ValidationError("A registration with this System ID is already pending verification.")
        return student_id
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data
    
    def save(self):
        """Create TemporaryRegistration instead of actual User and StudentProfile"""
        from django.contrib.auth.hashers import make_password
        from django.utils import timezone
        from datetime import timedelta
        import random
        import string
        
        cleaned_data = self.cleaned_data
        
        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Create temporary registration
        temp_registration = TemporaryRegistration.objects.create(
            name=cleaned_data['name'],
            student_id=cleaned_data['student_id'],
            email=cleaned_data['email'],
            password=make_password(cleaned_data['password']),  # Hash the password
            contact_no=cleaned_data['contact_no'],
            school=cleaned_data['school'].name,
            department=cleaned_data['department'].name,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        return temp_registration
