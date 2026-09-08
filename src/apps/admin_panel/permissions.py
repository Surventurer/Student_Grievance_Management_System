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
        # Use the new department assignment system
        if user.role in ['admin', 'officer', 'chief_warden', 'warden']:
            return user.assigned_department
        elif user.role == 'student' and hasattr(user, 'student_profile') and user.student_profile:
            return user.student_profile.department
    except Exception as e:
        # Handle case where profile doesn't exist
        print(f"Error getting user department: {e}")
        
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
    # Use the new User model access methods
    accessible_grievances = user.get_accessible_grievances()
    return accessible_grievances.filter(id=grievance.id).exists()


def can_access_student(user, student):
    """Check if user can access a specific student"""
    if user.role == 'superadmin':
        return True
    
    # Department admin / Chief Warden can access students from their department
    if user.role in ['admin', 'chief_warden']:
        user_dept = get_user_department(user)
        if user_dept:
            return student.department == user_dept
    
    # Officers / Wardens can access students who have grievances assigned to them
    if user.role in ['officer', 'warden']:
        try:
            if hasattr(user, 'admin_profile') and user.admin_profile:
                return Grievance.objects.filter(
                    student=student, 
                    assigned_to=user.admin_profile
                ).exists()
        except Exception as e:
            print(f"Error checking officer student access: {e}")
            return False
    
    # Students can access their own profile
    if user.role == 'student':
        try:
            if hasattr(user, 'student_profile') and user.student_profile:
                return student == user.student_profile
        except Exception as e:
            print(f"Error checking student self access: {e}")
            return False
    
    return False


def filter_grievances_by_access(user, queryset):
    """Filter grievance queryset based on user's access level"""
    # Use the new User model access methods
    return user.get_accessible_grievances().filter(id__in=queryset.values_list('id', flat=True))


def filter_students_by_access(user, queryset):
    """Filter student queryset based on user's access level"""
    # Use the new User model access methods
    return user.get_accessible_students().filter(id__in=queryset.values_list('id', flat=True))


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
        
        if request.user.role not in ['superadmin', 'admin', 'chief_warden']:
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
        
        if not request.user.is_admin_or_officer:
            messages.error(request, 'Access denied.')
            return redirect('authentication:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper
