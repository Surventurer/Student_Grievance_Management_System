"""
Superadmin-only views for user management and system settings
These views require the highest level of permissions
"""
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from datetime import datetime

from apps.authentication.decorators import superadmin_required
from apps.authentication.models import User
from apps.students.models import StudentProfile, AdminProfile, Department
from apps.grievances.models import Grievance, Category, AuditLog


@superadmin_required
def user_management(request):
    """User management view - Superadmin only"""
    # Get all users with their profiles
    users = User.objects.all().order_by('-created_at')
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(student_profile__name__icontains=search_query) |
            Q(student_profile__student_id__icontains=search_query)
        )
    
    # Add role filter
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Pagination
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'role_choices': User.ROLE_CHOICES,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'verified_users': User.objects.filter(is_email_verified=True).count(),
        'students_count': User.objects.filter(role='student').count(),
        'admins_count': User.objects.filter(role='admin').count(),
        'officers_count': User.objects.filter(role='officer').count(),
        'superadmins_count': User.objects.filter(role='superadmin').count(),
    }
    
    return render(request, 'admin_panel/superadmin/user_management.html', context)


@superadmin_required
@require_http_methods(["POST"])
def update_user_role(request, user_id):
    """Update user role - Superadmin only"""
    try:
        user = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        
        if new_role not in dict(User.ROLE_CHOICES):
            return JsonResponse({'error': 'Invalid role'}, status=400)
        
        # Prevent changing own role
        if user.id == request.user.id:
            return JsonResponse({'error': 'Cannot change your own role'}, status=400)
        
        old_role = user.role
        user.role = new_role
        
        # Update staff status based on role
        if new_role in ['admin', 'superadmin', 'officer']:
            user.is_staff = True
        else:
            user.is_staff = False
            
        user.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='update',
            description=f'Changed user {user.email} role from {old_role} to {new_role}',
            target_model='User',
            target_id=str(user_id),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'User role updated from {old_role} to {new_role}'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@superadmin_required
@require_http_methods(["POST"])
def toggle_user_status(request, user_id):
    """Toggle user active status - Superadmin only"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Prevent deactivating self
        if user.id == request.user.id:
            return JsonResponse({'error': 'Cannot deactivate your own account'}, status=400)
        
        user.is_active = not user.is_active
        user.save()
        
        status_text = 'activated' if user.is_active else 'deactivated'
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='status_change',
            description=f'User {user.email} {status_text}',
            target_model='User',
            target_id=str(user_id),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'User {status_text} successfully',
            'is_active': user.is_active
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@superadmin_required
def system_settings(request):
    """System settings view - Superadmin only"""
    import django
    from django.conf import settings
    import os
    
    # Handle form submissions
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'general':
            # Handle general settings (you can implement actual settings storage here)
            messages.success(request, 'General settings updated successfully!')
        elif form_type == 'security':
            # Handle security settings
            messages.success(request, 'Security settings updated successfully!')
        elif form_type == 'grievance':
            # Handle grievance settings
            messages.success(request, 'Grievance settings updated successfully!')
        
        return redirect('admin_panel:system_settings')
    
    # Calculate disk usage (simple approximation)
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        disk_usage_mb = round(used / (1024**2), 2)
    except:
        disk_usage_mb = 0
    
    context = {
        'django_version': django.get_version(),
        'debug': settings.DEBUG,
        'total_users': User.objects.count(),
        'total_grievances': Grievance.objects.count(),
        'disk_usage': disk_usage_mb,
        
        # System settings (defaults - you can implement actual settings storage)
        'settings': {
            'system_name': 'Student Grievance Management System',
            'contact_email': 'admin@university.edu',
            'max_file_size': 10,
            'email_notifications': True,
            'auto_assignment': True,
            'require_email_verification': True,
            'allow_student_registration': True,
            'session_timeout': 60,
            'password_min_length': 8,
            'default_priority': 'medium',
            'auto_resolve_days': 30,
            'escalation_threshold': 7,
            'allow_anonymous': False,
        },
    }
    
    return render(request, 'admin_panel/superadmin/system_settings.html', context)


@superadmin_required
def role_permissions(request):
    """Role permissions overview - Superadmin only"""
    
    context = {
        'superadmin_count': User.objects.filter(role='superadmin').count(),
        'admin_count': User.objects.filter(role='admin').count(),
        'cs_admin_count': User.objects.filter(role='admin', admin_profile__department='cs').count(),
        'ba_admin_count': User.objects.filter(role='admin', admin_profile__department='ba').count(),
        'officer_count': User.objects.filter(role='officer').count(),
        'student_count': User.objects.filter(role='student').count(),
        'role_choices': User.ROLE_CHOICES,
    }
    
    return render(request, 'admin_panel/superadmin/role_permissions.html', context)


@superadmin_required
def audit_logs_view(request):
    """Audit logs view - Superadmin only"""
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    
    # Add filters
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    date_filter = request.GET.get('date', '')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date=filter_date)
        except ValueError:
            pass
    
    user_filter = request.GET.get('user', '')
    if user_filter:
        logs = logs.filter(user__email__icontains=user_filter)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    # Get available actions for filter dropdown
    available_actions = AuditLog.objects.values_list('action', flat=True).distinct()
    
    context = {
        'logs': logs,
        'action_filter': action_filter,
        'date_filter': date_filter,
        'user_filter': user_filter,
        'available_actions': available_actions,
        'total_logs': AuditLog.objects.count(),
    }
    
    return render(request, 'admin_panel/superadmin/audit_logs.html', context)


@superadmin_required
def create_admin_user(request):
    """Create new admin user - Superadmin only"""
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            role = request.POST.get('role')
            department = request.POST.get('department', '')
            employee_id = request.POST.get('employee_id')
            
            # Validate inputs
            if not email or not role or not employee_id:
                messages.error(request, 'Email, role, and employee ID are required')
                return redirect('admin_panel:create_admin_user')
            
            if role not in ['admin', 'officer']:
                messages.error(request, 'Invalid role selected')
                return redirect('admin_panel:create_admin_user')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'User with this email already exists')
                return redirect('admin_panel:create_admin_user')
            
            if AdminProfile.objects.filter(employee_id=employee_id).exists():
                messages.error(request, 'Employee ID already exists')
                return redirect('admin_panel:create_admin_user')
            
            # Create user
            user = User.objects.create(
                email=email,
                role=role,
                is_staff=True,
                is_email_verified=True,
                is_active=True
            )
            user.set_password('admin123')  # Default password
            user.save()
            
            # Create admin profile
            AdminProfile.objects.create(
                user=user,
                employee_id=employee_id,
                department=department,
                role_level=role
            )
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='create',
                description=f'Created new admin user: {email} with role {role}',
                target_model='User',
                target_id=str(user.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, f'Admin user created successfully. Default password: admin123')
            return redirect('admin_panel:user_management')
            
        except Exception as e:
            messages.error(request, f'Error creating admin user: {str(e)}')
            return redirect('admin_panel:create_admin_user')
    
    # GET request - show form
    departments = Department.objects.all()
    
    context = {
        'departments': departments,
        'admin_roles': [('admin', 'Department Admin'), ('officer', 'Grievance Officer')]
    }
    
    return render(request, 'admin_panel/superadmin/create_admin_user.html', context)


@superadmin_required
def role_permissions_matrix(request):
    """View showing role permissions matrix - Superadmin only"""
    
    permissions_matrix = {
        'superadmin': {
            'description': 'Full system access with all permissions',
            'permissions': [
                'View all grievances and reports',
                'Manage all users and admins', 
                'System settings and configuration',
                'Complete audit log access',
                'Category and department management',
                'Data export and analytics',
                'Assign/reassign any grievance'
            ],
            'color': 'danger'
        },
        'admin': {
            'description': 'Department-level administration',
            'permissions': [
                'View department grievances only',
                'Manage department students',
                'Department reports and analytics',
                'Assign grievances within department',
                'Communicate with students'
            ],
            'color': 'warning'
        },
        'officer': {
            'description': 'Grievance handling specialist',
            'permissions': [
                'View assigned grievances only',
                'Update grievance status',
                'Communicate with students',
                'Add comments and resolutions'
            ],
            'color': 'info'
        },
        'student': {
            'description': 'Student user access',
            'permissions': [
                'Submit grievances',
                'View own grievances only',
                'Communicate with admins',
                'Provide feedback',
                'Update profile'
            ],
            'color': 'success'
        }
    }
    
    context = {
        'permissions_matrix': permissions_matrix,
        'total_roles': len(permissions_matrix),
    }
    
    return render(request, 'admin_panel/superadmin/role_permissions.html', context)
