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
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, connection
from datetime import datetime, timedelta
import json

from apps.authentication.decorators import superadmin_required, api_superadmin_required
from apps.authentication.models import User, TemporaryRegistration, AdminLoginOTP
from apps.students.models import StudentProfile, AdminProfile, Department, School
from apps.grievances.models import Grievance, Category, AuditLog


@superadmin_required
def user_management(request):
    """User management view - Superadmin only"""
    # Get all verified users with their profiles
    users = User.objects.all().order_by('-created_at')
    
    # Check if we should show unverified students (temporary registrations)
    # Hidden field ensures '0' is sent when checkbox is unchecked
    # Checkbox sends '1' when checked (overrides hidden field)
    show_unverified = request.GET.get('show_unverified', '1') == '1'
    
    # Get all temporary registrations (unverified users) only if checkbox is checked
    if show_unverified:
        temp_registrations = TemporaryRegistration.objects.all().order_by('-created_at')
    else:
        temp_registrations = TemporaryRegistration.objects.none()
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(student_profile__name__icontains=search_query) |
            Q(student_profile__student_id__icontains=search_query)
        )
        if show_unverified:
            temp_registrations = temp_registrations.filter(
                Q(email__icontains=search_query) |
                Q(name__icontains=search_query) |
                Q(student_id__icontains=search_query)
            )
    
    # Add role filter (only applies to verified users)
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
        # If filtering by role other than student, exclude temp registrations
        if role_filter != 'student':
            temp_registrations = temp_registrations.none()
    
    # Create a combined list of users and temporary registrations
    all_users = []
    
    # Add verified users
    for user in users:
        user.is_temporary = False
        user.user_type = 'verified'
        all_users.append(user)
    
    # Add temporary registrations (only if show_unverified is True)
    for temp_reg in temp_registrations:
        temp_reg.is_temporary = True
        temp_reg.user_type = 'temporary'
        temp_reg.role = 'student'  # All temp registrations are students
        temp_reg.is_active = not temp_reg.is_expired
        temp_reg.is_email_verified = temp_reg.is_verified
        # Add methods as attributes instead of lambdas
        temp_reg.get_role_display = 'Student (Unverified)'
        temp_reg.get_display_name = temp_reg.name
        temp_reg.created_at = temp_reg.created_at
        temp_reg.id = f"temp_{temp_reg.id}"  # Prefix to distinguish from real users
        all_users.append(temp_reg)
    
    # Sort all users by creation date (newest first)
    all_users.sort(key=lambda x: x.created_at, reverse=True)
    
    # Pagination
    paginator = Paginator(all_users, 20)
    page = request.GET.get('page')
    users_page = paginator.get_page(page)
    
    # Exclude superadmin from role choices since there's only one
    filtered_role_choices = [
        (role_code, role_name) for role_code, role_name in User.ROLE_CHOICES 
        if role_code != 'superadmin'
    ]
    
    context = {
        'users': users_page,
        'search_query': search_query,
        'role_filter': role_filter,
        'show_unverified': show_unverified,
        'role_choices': filtered_role_choices,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'verified_users': User.objects.filter(is_email_verified=True).count(),
        'students_count': User.objects.filter(role='student').count(),
        'admins_count': User.objects.filter(role='admin').count(),
        'officers_count': User.objects.filter(role='officer').count(),
        'superadmins_count': User.objects.filter(role='superadmin').count(),
        'temp_registrations_count': TemporaryRegistration.objects.count(),
        'unverified_temp_count': TemporaryRegistration.objects.filter(is_verified=False).count(),
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
        
        new_status = not user.is_active
        
        # If deactivating, get the reason
        if not new_status:  # deactivating (making is_active = False)
            deactivation_reason = request.POST.get('deactivation_reason', '').strip()
            if not deactivation_reason:
                return JsonResponse({'error': 'Deactivation reason is required'}, status=400)
            user.deactivation_reason = deactivation_reason
        else:  # activating (making is_active = True)
            user.deactivation_reason = None  # Clear reason when reactivating
        
        user.is_active = new_status
        user.save()
        
        status_text = 'activated' if user.is_active else 'deactivated'
        
        # Create audit log with reason if deactivating
        description = f'User {user.email} {status_text}'
        if not user.is_active and user.deactivation_reason:
            description += f' - Reason: {user.deactivation_reason}'
            
        AuditLog.objects.create(
            user=request.user,
            action='status_change',
            description=description,
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
def update_deactivation_reason(request, user_id):
    """Update deactivation reason for a user - Superadmin only"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
        
    try:
        user = get_object_or_404(User, id=user_id)
        
        deactivation_reason = request.POST.get('deactivation_reason', '').strip()
        if not deactivation_reason:
            return JsonResponse({'error': 'Deactivation reason is required'}, status=400)
        
        user.deactivation_reason = deactivation_reason
        user.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='deactivation_reason_update',
            description=f'Updated deactivation reason for {user.email}: {deactivation_reason}',
            target_model='User',
            target_id=str(user_id),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Deactivation reason updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@superadmin_required
def system_settings(request):
    """System settings view - Superadmin only"""
    import django
    from django.conf import settings
    
    context = {
        'django_version': django.get_version(),
        'debug': settings.DEBUG,
        'total_users': User.objects.count(),
        'total_grievances': Grievance.objects.count(),
    }
    
    return render(request, 'admin_panel/superadmin/system_settings.html', context)


@superadmin_required
def role_permissions(request):
    """Role permissions overview - Superadmin only"""
    context = {
        'superadmin_count': User.objects.filter(role='superadmin').count(),
        'admin_count': User.objects.filter(role='admin').count(),
        'officer_count': User.objects.filter(role='officer').count(),
        'student_count': User.objects.filter(role='student').count(),
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'admin_panel/superadmin/role_permissions.html', context)


@superadmin_required
def audit_logs_view(request):
    """Audit logs view - Superadmin only"""
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'total_logs': AuditLog.objects.count(),
    }
    return render(request, 'admin_panel/superadmin/audit_logs.html', context)


@superadmin_required
def create_user(request):
    """Create new user - Superadmin only"""
    if request.method == 'POST':
        # Implementation here
        pass
    
    context = {
        'role_choices': [
            ('student', 'Student'),
            ('admin', 'Department Admin'), 
            ('officer', 'Grievance Officer')
        ],
    }
    return render(request, 'admin_panel/superadmin/create_user.html', context)


@superadmin_required
def create_admin_user(request):
    """Legacy function - redirect to create_user"""
    return redirect('admin_panel:create_user')


@superadmin_required
def role_permissions_matrix(request):
    """Role permissions matrix - Superadmin only"""
    return render(request, 'admin_panel/superadmin/role_permissions.html', {})


@superadmin_required
@require_http_methods(["POST"])
def bulk_delete_users(request):
    """Bulk delete users - Superadmin only"""
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        # Check if trying to delete own account
        if request.user.id in [int(uid) for uid in user_ids]:
            return JsonResponse({'error': 'Cannot delete your own account'}, status=400)
        
        users_to_delete = User.objects.filter(id__in=user_ids)
        deleted_count = users_to_delete.delete()[0]
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} user(s)'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)





@superadmin_required
@require_http_methods(["POST"])
def delete_temporary_registration(request, temp_id):
    """Delete a temporary registration - Superadmin only"""
    try:
        temp_registration = get_object_or_404(TemporaryRegistration, id=temp_id)
        
        temp_info = {
            'id': temp_registration.id,
            'email': temp_registration.email,
            'student_id': temp_registration.student_id,
            'name': temp_registration.name
        }
        
        temp_registration.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted temporary registration for {temp_info["name"]}',
            'deleted_registration': temp_info
        })
        
    except TemporaryRegistration.DoesNotExist:
        return JsonResponse({'error': 'Temporary registration not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@superadmin_required
@require_http_methods(["POST"])
def approve_temporary_registration(request, temp_id):
    """Approve a temporary registration - Superadmin only"""
    try:
        temp_registration = get_object_or_404(TemporaryRegistration, id=temp_id)
        
        # Check if registration is already expired
        if temp_registration.is_expired:
            return JsonResponse({'error': 'Registration has expired and cannot be approved'}, status=400)
        
        # Create the actual user
        user, student_profile = temp_registration.create_actual_user()
        temp_registration.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully approved registration for {student_profile.name}',
            'user_id': user.id,
        })
        
    except TemporaryRegistration.DoesNotExist:
        return JsonResponse({'error': 'Temporary registration not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@superadmin_required
def get_temporary_registration_details(request, temp_id):
    """Get temporary registration details - Superadmin only"""
    try:
        temp_registration = get_object_or_404(TemporaryRegistration, id=temp_id)
        
        details = {
            'id': temp_registration.id,
            'name': temp_registration.name,
            'student_id': temp_registration.student_id,
            'email': temp_registration.email,
            'contact_no': temp_registration.contact_no,
            'school': temp_registration.school,
            'department': temp_registration.department,
            'created_at': temp_registration.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'expires_at': temp_registration.expires_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_expired': temp_registration.is_expired,
            'is_verified': temp_registration.is_verified,
        }
        
        return JsonResponse({
            'success': True,
            'registration': details
        })
        
    except TemporaryRegistration.DoesNotExist:
        return JsonResponse({'error': 'Temporary registration not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@superadmin_required
@require_http_methods(["POST"])
def clear_failed_login_attempts(request):
    """Clear failed login attempts - Superadmin only"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        if user_id:
            user = get_object_or_404(User, id=user_id)
            # Clear AdminLoginOTP records for this user
            deleted_count = AdminLoginOTP.objects.filter(user=user).delete()[0]
            message = f'Cleared failed login attempts for {user.email}. Cleaned {deleted_count} OTP records.'
        else:
            # Clear all old AdminLoginOTP records
            deleted_count = AdminLoginOTP.objects.filter(
                created_at__lt=timezone.now() - timedelta(hours=1)
            ).delete()[0]
            message = f'Cleared all failed login attempts. Cleaned {deleted_count} old OTP records.'
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


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
def create_user(request):
    """Create new user of any role (except superadmin) - Superadmin only"""
    if request.method == 'POST':
        try:
            # Debug: Print all POST data
            print("=== CREATE_USER DEBUG ===")
            print("All POST data:")
            for key, value in request.POST.items():
                print(f"  {key}: '{value}'")
            print("========================")
            
            email = request.POST.get('email')
            role = request.POST.get('role')
            password = request.POST.get('password', 'default123')  # Default password
            
            # Validate inputs
            if not email or not role:
                messages.error(request, 'Email and role are required')
                return redirect('admin_panel:create_user')
            
            # Superadmin cannot create another superadmin
            if role not in ['student', 'admin', 'officer']:
                messages.error(request, 'Invalid role selected. Cannot create superadmin users.')
                return redirect('admin_panel:create_user')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'User with this email already exists')
                return redirect('admin_panel:create_user')
            
            # Create user with transaction for data consistency
            with transaction.atomic():
                # Create the user
                user = User.objects.create(
                    email=email,
                    role=role,
                    is_staff=(role != 'student'),  # Only students are not staff
                    is_email_verified=True,
                    is_active=True
                )
                user.set_password(password)
                user.save()
                
                # Create appropriate profile based on role
                if role == 'student':
                    # Student-specific fields
                    name = request.POST.get('name', '').strip()
                    student_id = request.POST.get('student_id', '').strip()
                    school = request.POST.get('school', '').strip()
                    department = request.POST.get('department', '').strip()
                    contact_no = request.POST.get('contact_no', '').strip()
                    
                    # Debug: Log the received values
                    print(f"DEBUG - Student fields received:")
                    print(f"  name: '{name}'")
                    print(f"  student_id: '{student_id}'")
                    print(f"  school: '{school}'")
                    print(f"  department: '{department}'")
                    print(f"  contact_no: '{contact_no}'")
                    
                    if not student_id or not school or not department:
                        raise ValueError('Please fill in all required fields: Student ID, School, and Department are mandatory for student accounts.')
                    
                    if StudentProfile.objects.filter(student_id=student_id).exists():
                        raise ValueError('Student ID already exists')
                    
                    StudentProfile.objects.create(
                        user=user,
                        name=name or '',
                        student_id=student_id,
                        school=school,
                        department=department,
                        contact_no=contact_no
                    )
                    
                else:  # admin or officer
                    # Admin-specific fields
                    department = request.POST.get('admin_department')  # Changed from 'department' to 'admin_department'
                    employee_id = request.POST.get('employee_id')
                    phone = request.POST.get('phone', '')
                    office_location = request.POST.get('office_location', '')
                    
                    # Debug: Log the received values
                    print(f"DEBUG - Admin fields received:")
                    print(f"  admin_department: '{department}'")
                    print(f"  employee_id: '{employee_id}'")
                    print(f"  phone: '{phone}'")
                    print(f"  office_location: '{office_location}'")
                    
                    if not employee_id or not department:
                        raise ValueError('Please fill in all required fields: Employee ID and Department are mandatory for admin/officer accounts.')
                    
                    if AdminProfile.objects.filter(employee_id=employee_id).exists():
                        raise ValueError('Employee ID already exists')
                    
                    AdminProfile.objects.create(
                        user=user,
                        role_level=role,
                        department=department,
                        employee_id=employee_id,
                        phone=phone,
                        office_location=office_location
                    )
                
                # Create audit log
                AuditLog.objects.create(
                    user=request.user,
                    action='create',
                    description=f'Created new {role} user: {email}',
                    target_model='User',
                    target_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                messages.success(request, f'{role.title()} user created successfully. Default password: {password}')
                return redirect('admin_panel:user_management')
            
        except ValueError as ve:
            messages.error(request, str(ve))
            return redirect('admin_panel:create_user')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('admin_panel:create_user')
    
    # GET request - show form
    departments = Department.objects.all()
    
    context = {
        'departments': departments,
        'role_choices': [
            ('student', 'Student'),
            ('admin', 'Department Admin'), 
            ('officer', 'Grievance Officer')
        ],
        'schools': School.objects.all()
    }
    
    return render(request, 'admin_panel/superadmin/create_user.html', context)


@superadmin_required
def create_admin_user(request):
    """Legacy function - redirect to create_user"""
    return redirect('admin_panel:create_user')


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


@superadmin_required
@require_http_methods(["POST"])
def bulk_delete_users(request):
    """Bulk delete users - Superadmin only"""
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        # Validate that user_ids is a list of integers
        try:
            user_ids = [int(uid) for uid in user_ids]
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid user IDs provided'}, status=400)
        
        # Get users to delete
        users_to_delete = User.objects.filter(id__in=user_ids)
        
        if not users_to_delete.exists():
            return JsonResponse({'error': 'No valid users found to delete'}, status=400)
        
        # Check if trying to delete own account
        if request.user.id in user_ids:
            return JsonResponse({'error': 'Cannot delete your own account'}, status=400)
        
        # Prevent deletion of all superadmins
        superadmin_ids = list(User.objects.filter(role='superadmin').values_list('id', flat=True))
        superadmins_to_delete = [uid for uid in user_ids if uid in superadmin_ids]
        
        if len(superadmins_to_delete) >= len(superadmin_ids):
            return JsonResponse({'error': 'Cannot delete all superadmin accounts'}, status=400)
        
        deleted_users_info = []
        
        with transaction.atomic():
            # For SQLite, temporarily disable foreign key checks
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF")
            
            try:
                # Create audit logs before deletion
                for user in users_to_delete:
                    deleted_users_info.append({
                        'id': user.id,
                        'email': user.email,
                        'role': user.role
                    })
                    
                    # Create audit log before deletion
                    AuditLog.objects.create(
                        user=request.user,
                        action='delete',
                        description=f'Bulk deleted user {user.email} (Role: {user.get_role_display()})',
                        target_model='User',
                        target_id=str(user.id),
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                
                # Manually delete related objects in correct order to avoid foreign key issues
                for user in users_to_delete:
                    # Delete related objects first
                    if hasattr(user, 'student_profile') and user.student_profile:
                        # Delete grievances first (they reference student profile)
                        user.student_profile.grievances.all().delete()
                        # Delete student profile
                        user.student_profile.delete()
                    
                    if hasattr(user, 'admin_profile') and user.admin_profile:
                        # Update any category assignments that reference this admin
                        user.admin_profile.category_assignments.all().delete()
                        # Delete admin profile
                        user.admin_profile.delete()
                    
                    # Set user references to NULL in remaining records (audit logs, etc.)
                    # This is handled automatically by our model changes
                
                # Now delete users
                deleted_count = users_to_delete.delete()[0]
                
            finally:
                # Re-enable foreign key checks
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = ON")
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'deleted_users': deleted_users_info,
            'message': f'Successfully deleted {deleted_count} user(s)'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@superadmin_required
@require_http_methods(["POST"])
def bulk_deactivate_users(request):
    """Bulk deactivate users (soft delete) - Superadmin only"""
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        deactivation_reason = data.get('deactivation_reason', '').strip()
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        if not deactivation_reason:
            return JsonResponse({'error': 'Deactivation reason is required'}, status=400)
        
        # Validate that user_ids is a list of integers
        try:
            user_ids = [int(uid) for uid in user_ids]
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid user IDs provided'}, status=400)
        
        # Get users to deactivate
        users_to_deactivate = User.objects.filter(id__in=user_ids, is_active=True)
        
        if not users_to_deactivate.exists():
            return JsonResponse({'error': 'No valid active users found to deactivate'}, status=400)
        
        # Check if trying to deactivate own account
        if request.user.id in user_ids:
            return JsonResponse({'error': 'Cannot deactivate your own account'}, status=400)
        
        deactivated_users_info = []
        
        with transaction.atomic():
            for user in users_to_deactivate:
                # Store user info before deactivation
                user_info = {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role
                }
                
                # Deactivate the user
                user.is_active = False
                user.deactivation_reason = deactivation_reason
                user.save()
                
                # Create audit log
                AuditLog.objects.create(
                    user=request.user,
                    action='update',
                    description=f'Bulk deactivated user {user.email} (Role: {user.get_role_display()}) - Reason: {deactivation_reason}',
                    target_model='User',
                    target_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                deactivated_users_info.append(user_info)
        
        return JsonResponse({
            'success': True,
            'deactivated_count': len(deactivated_users_info),
            'deactivated_users': deactivated_users_info,
            'message': f'Successfully deactivated {len(deactivated_users_info)} user(s)'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@superadmin_required
@require_http_methods(["POST"])
def bulk_activate_users(request):
    """Bulk activate users - Superadmin only"""
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        # Validate that user_ids is a list of integers
        try:
            user_ids = [int(uid) for uid in user_ids]
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid user IDs provided'}, status=400)
        
        # Get users to activate (only inactive users)
        users_to_activate = User.objects.filter(id__in=user_ids, is_active=False)
        
        if not users_to_activate.exists():
            return JsonResponse({'error': 'No valid inactive users found to activate'}, status=400)
        
        activated_users_info = []
        
        with transaction.atomic():
            for user in users_to_activate:
                # Store user info before activation
                user_info = {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role
                }
                
                # Activate the user and clear deactivation reason
                user.is_active = True
                user.deactivation_reason = None  # Clear the deactivation reason
                user.save()
                
                # Create audit log
                AuditLog.objects.create(
                    user=request.user,
                    action='update',
                    description=f'Bulk activated user {user.email} (Role: {user.get_role_display()})',
                    target_model='User',
                    target_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                activated_users_info.append(user_info)
        
        return JsonResponse({
            'success': True,
            'activated_count': len(activated_users_info),
            'activated_users': activated_users_info,
            'message': f'Successfully activated {len(activated_users_info)} user(s)'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@api_superadmin_required
def get_user_details(request, user_id):
    """Get detailed information about a permanent user - Superadmin only"""
    print(f"=== GET_USER_DETAILS CALLED ===")
    print(f"User ID: {user_id}")
    print(f"Request user: {request.user}")
    print(f"Request method: {request.method}")
    
    try:
        from apps.students.models import StudentProfile, AdminProfile
        
        print(f"Fetching details for user ID: {user_id}")
        user = get_object_or_404(User, id=user_id)
        print(f"Found user: {user.email}, role: {user.role}")
        
        # Basic user information
        user_details = {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'role_display': user.get_role_display(),
            'is_active': user.is_active,
            'is_email_verified': user.is_email_verified,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            'failed_login_attempts': getattr(user, 'failed_login_attempts', 0),
            'last_failed_login': getattr(user, 'last_failed_login', None),
            'name': None,
            'student_profile': None,
            'admin_profile': None,
        }
        
        # Add student profile information if user is a student
        if user.role == 'student':
            print("User is a student, looking for StudentProfile...")
            try:
                student_profile = StudentProfile.objects.get(user=user)
                print(f"Found student profile: {student_profile.name}")
                user_details['student_profile'] = {
                    'student_id': student_profile.student_id,
                    'name': student_profile.name,
                    'school': student_profile.school,  # school is CharField, not ForeignKey
                    'department': student_profile.department,  # department is CharField, not ForeignKey
                    'contact_no': student_profile.contact_no,
                }
                user_details['name'] = student_profile.name
                print(f"Student profile details: {user_details['student_profile']}")
            except StudentProfile.DoesNotExist:
                print("StudentProfile not found!")
                user_details['student_profile'] = None
        
        # Add admin profile information if user is an admin or officer
        elif user.role in ['admin', 'officer']:
            print("User is an admin/officer, looking for AdminProfile...")
            try:
                admin_profile = AdminProfile.objects.get(user=user)
                print(f"Found admin profile: role_level={admin_profile.role_level}, department={admin_profile.department}")
                user_details['admin_profile'] = {
                    'employee_id': admin_profile.employee_id,
                    'department': admin_profile.department,
                    'phone': admin_profile.phone,
                    'office_location': admin_profile.office_location,
                    'role_level': admin_profile.get_role_level_display(),
                }
                user_details['name'] = f"{admin_profile.get_role_level_display()} ({admin_profile.employee_id})"
                print(f"Admin profile details: {user_details['admin_profile']}")
            except AdminProfile.DoesNotExist:
                print("AdminProfile not found!")
                user_details['admin_profile'] = None
        
        # For other roles, try to get name from related profiles or use email
        if not user_details['name']:
            user_details['name'] = user.email.split('@')[0].title()
        
        print(f"Final user_details: {user_details}")
        return JsonResponse({
            'success': True,
            'user': user_details
        })
        
    except User.DoesNotExist:
        print(f"User with ID {user_id} not found!")
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error in get_user_details: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@api_superadmin_required
def edit_user(request, user_id):
    """Edit user profile and role - Superadmin only"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        import json
        from apps.students.models import StudentProfile, AdminProfile
        
        print(f"=== EDIT_USER CALLED ===")
        print(f"User ID: {user_id}")
        print(f"Request user: {request.user}")
        
        user = get_object_or_404(User, id=user_id)
        print(f"Found user: {user.email}, current role: {user.role}")
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
            print(f"Received data: {data}")
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        # Get the new role and basic info
        new_role = data.get('role', user.role)
        is_active = data.get('is_active', user.is_active)
        is_verified = data.get('is_email_verified', user.is_email_verified)
        
        print(f"New role: {new_role}, Active: {is_active}, Verified: {is_verified}")
        
        # Prevent role changes for superadmin users
        if user.role == 'superadmin' and new_role != 'superadmin':
            return JsonResponse({'error': 'Super Admin role cannot be changed'}, status=400)
        
        # Prevent changing other users to superadmin role
        if user.role != 'superadmin' and new_role == 'superadmin':
            return JsonResponse({'error': 'Cannot change user to Super Admin role'}, status=400)
        
        # Update basic user information
        user.role = new_role
        user.is_active = is_active
        user.is_email_verified = is_verified
        user.save()
        
        print(f"Updated user basic info")
        
        # Handle role-specific profile updates
        if new_role == 'student':
            student_data = data.get('student_profile', {})
            print(f"Processing student profile data: {student_data}")
            
            # Get or create student profile
            student_profile, created = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    'name': student_data.get('name', ''),
                    'student_id': student_data.get('student_id', ''),
                    'school': student_data.get('school', ''),
                    'department': student_data.get('department', ''),
                    'contact_no': student_data.get('contact_no', ''),
                }
            )
            
            if not created:
                # Update existing profile
                student_profile.name = student_data.get('name', student_profile.name)
                student_profile.student_id = student_data.get('student_id', student_profile.student_id)
                student_profile.school = student_data.get('school', student_profile.school)
                student_profile.department = student_data.get('department', student_profile.department)
                student_profile.contact_no = student_data.get('contact_no', student_profile.contact_no)
                student_profile.save()
            
            print(f"{'Created' if created else 'Updated'} student profile")
            
            # Remove admin profile if it exists (role changed from admin to student)
            try:
                admin_profile = AdminProfile.objects.get(user=user)
                admin_profile.delete()
                print("Removed existing admin profile")
            except AdminProfile.DoesNotExist:
                pass
                
        elif new_role in ['admin', 'officer']:
            admin_data = data.get('admin_profile', {})
            print(f"Processing admin profile data: {admin_data}")
            
            # Get or create admin profile
            admin_profile, created = AdminProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role_level': new_role,
                    'department': admin_data.get('department', ''),
                    'employee_id': admin_data.get('employee_id', ''),
                    'phone': admin_data.get('phone', ''),
                    'office_location': admin_data.get('office_location', ''),
                }
            )
            
            if not created:
                # Update existing profile
                admin_profile.role_level = new_role
                admin_profile.department = admin_data.get('department', admin_profile.department)
                admin_profile.employee_id = admin_data.get('employee_id', admin_profile.employee_id)
                admin_profile.phone = admin_data.get('phone', admin_profile.phone)
                admin_profile.office_location = admin_data.get('office_location', admin_profile.office_location)
                admin_profile.save()
            
            print(f"{'Created' if created else 'Updated'} admin profile")
            
            # Remove student profile if it exists (role changed from student to admin)
            try:
                student_profile = StudentProfile.objects.get(user=user)
                student_profile.delete()
                print("Removed existing student profile")
            except StudentProfile.DoesNotExist:
                pass
        
        elif new_role == 'superadmin':
            # For superadmin, we might just update the name if provided
            name = data.get('name')
            if name:
                # We could store this in a separate field or handle it differently
                print(f"Updated superadmin name: {name}")
            
            # Remove both student and admin profiles for superadmin
            try:
                student_profile = StudentProfile.objects.get(user=user)
                student_profile.delete()
                print("Removed existing student profile for superadmin")
            except StudentProfile.DoesNotExist:
                pass
                
            try:
                admin_profile = AdminProfile.objects.get(user=user)
                admin_profile.delete()
                print("Removed existing admin profile for superadmin")
            except AdminProfile.DoesNotExist:
                pass
        
        print(f"Successfully updated user {user.email} to role {new_role}")
        
        return JsonResponse({
            'success': True,
            'message': f'User profile updated successfully. Role changed to {new_role}.',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'role_display': user.get_role_display(),
                'is_active': user.is_active,
                'is_email_verified': user.is_email_verified
            }
        })
        
    except User.DoesNotExist:
        print(f"User with ID {user_id} not found!")
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error in edit_user: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@api_superadmin_required
def get_schools_departments(request):
    """Get list of schools and departments for dropdowns - Superadmin only"""
    try:
        from apps.students.models import School, Department
        
        schools = list(School.objects.filter(is_active=True).values('id', 'name'))
        departments = list(Department.objects.filter(is_active=True).values('id', 'name', 'school_id'))
        
        return JsonResponse({
            'success': True,
            'schools': schools,
            'departments': departments
        })
        
    except Exception as e:
        print(f"Error in get_schools_departments: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
