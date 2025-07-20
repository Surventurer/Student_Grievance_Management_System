"""
Role-based permission utilities for the admin panel
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.db import models
from functools import wraps
from apps.students.models import AdminProfile
from apps.grievances.models import Grievance
from apps.students.models import StudentProfile


def get_user_department(user):
    """Get the department of the logged-in admin user"""
    if user.role == 'superadmin':
        return None  # Superadmin has access to all departments
    
    try:
        admin_profile = AdminProfile.objects.get(user=user)
        return admin_profile.department
    except AdminProfile.DoesNotExist:
        return None


def can_access_all_data(user):
    """Check if user can access all system data (superadmin only)"""
    return user.role == 'superadmin'


def can_manage_system_settings(user):
    """Check if user can manage system-wide settings"""
    return user.role == 'superadmin'


def can_manage_auto_assignment(user):
    """Check if user can manage auto-assignment settings"""
    return user.role == 'superadmin'


def can_manage_categories(user):
    """Check if user can manage grievance categories"""
    return user.role == 'superadmin'


def can_view_audit_logs(user):
    """Check if user can view audit logs"""
    return user.role == 'superadmin'


def can_view_system_reports(user):
    """Check if user can view system-wide reports"""
    return user.role == 'superadmin'


def can_access_department_data(user, department_name):
    """Check if user can access data from a specific department"""
    if user.role == 'superadmin':
        return True
    
    user_dept = get_user_department(user)
    if not user_dept:
        return False
    
    return user_dept == department_name


def can_access_grievance(user, grievance):
    """Check if user can access a specific grievance"""
    if user.role == 'superadmin':
        return True
    
    # Department admin can access grievances from their department
    if user.role == 'admin':
        user_dept = get_user_department(user)
        return user_dept and (
            grievance.department == user_dept or 
            grievance.student.department == user_dept
        )
    
    # Officers can access grievances assigned to them
    if user.role == 'officer':
        try:
            admin_profile = AdminProfile.objects.get(user=user)
            return grievance.assigned_to == admin_profile
        except AdminProfile.DoesNotExist:
            return False
    
    return False


def can_access_student(user, student):
    """Check if user can access a specific student"""
    if user.role == 'superadmin':
        return True
    
    # Department admin can access students from their department
    if user.role == 'admin':
        user_dept = get_user_department(user)
        return user_dept and student.department == user_dept
    
    # Officers can access students who have grievances assigned to them
    if user.role == 'officer':
        try:
            admin_profile = AdminProfile.objects.get(user=user)
            return Grievance.objects.filter(
                student=student, 
                assigned_to=admin_profile
            ).exists()
        except AdminProfile.DoesNotExist:
            return False
    
    return False


def filter_grievances_by_access(user, queryset):
    """Filter grievance queryset based on user's access level"""
    if user.role == 'superadmin':
        return queryset
    
    if user.role == 'admin':
        user_dept = get_user_department(user)
        if user_dept:
            return queryset.filter(
                models.Q(department=user_dept) | 
                models.Q(student__department=user_dept)
            )
    
    if user.role == 'officer':
        try:
            admin_profile = AdminProfile.objects.get(user=user)
            return queryset.filter(assigned_to=admin_profile)
        except AdminProfile.DoesNotExist:
            pass
    
    return queryset.none()


def filter_students_by_access(user, queryset):
    """Filter student queryset based on user's access level"""
    if user.role == 'superadmin':
        return queryset
    
    if user.role == 'admin':
        user_dept = get_user_department(user)
        if user_dept:
            return queryset.filter(department=user_dept)
    
    if user.role == 'officer':
        try:
            admin_profile = AdminProfile.objects.get(user=user)
            # Officers can see students who have grievances assigned to them
            student_ids = Grievance.objects.filter(
                assigned_to=admin_profile
            ).values_list('student_id', flat=True).distinct()
            return queryset.filter(id__in=student_ids)
        except AdminProfile.DoesNotExist:
            pass
    
    return queryset.none()


# Decorators for view-level permission checking
def superadmin_required(view_func):
    """Decorator to require superadmin role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if request.user.role != 'superadmin':
            messages.error(request, 'Access denied. Superadmin privileges required.')
            return redirect('admin_panel:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_or_higher_required(view_func):
    """Decorator to require admin or higher role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if request.user.role not in ['superadmin', 'admin']:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('admin_panel:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def department_access_required(view_func):
    """Decorator to check department-specific access for students/grievances"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if not request.user.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('authentication:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper
