from django import forms
from django.contrib.auth import get_user_model
from apps.students.models import StudentProfile, School, Department

User = get_user_model()


class StudentRegistrationForm(forms.Form):
    """Student Registration Form matching the database schema"""
    
    # Student Profile fields
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    
    student_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your student ID'
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
        queryset=School.objects.all(),
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
        
        # If school is selected, populate departments
        if 'school' in self.data:
            try:
                school_id = int(self.data.get('school'))
                self.fields['department'].queryset = Department.objects.filter(school_id=school_id)
            except (ValueError, TypeError):
                pass
        elif self.initial.get('school'):
            self.fields['department'].queryset = self.initial['school'].departments.all()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("A student with this ID already exists.")
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
        """Create User and StudentProfile"""
        cleaned_data = self.cleaned_data
        
        # Create User
        user = User.objects.create_user(
            email=cleaned_data['email'],
            password=cleaned_data['password'],
            role='student'
        )
        
        # Create StudentProfile
        student_profile = StudentProfile.objects.create(
            user=user,
            name=cleaned_data['name'],
            student_id=cleaned_data['student_id'],
            school=cleaned_data['school'].name,  # Store school name from School model
            department=cleaned_data['department'].name,  # Store department name from Department model
            contact_no=cleaned_data['contact_no']
        )
        
        return user, student_profile
