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
from apps.grievances.models import (
    Grievance, Category, AuditLog, GrievanceComment,
    GrievanceStatusHistory, GrievanceAssignmentHistory, CategoryAssignment
)
from apps.notifications.models import ReadNotification


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
        
        # Sync HOD assignment if user is an admin
        if user.role == 'admin' and hasattr(user, 'admin_profile') and user.admin_profile:
            dept_name = user.admin_profile.department
            if dept_name:
                for dept in Department.objects.filter(name__iexact=dept_name.strip()):
                    dept.auto_assign_hod_if_needed(save=True)

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
def clear_failed_login_attempts(request, user_id=None):
    """Clear failed login attempts and restore login access - Superadmin only"""
    try:
        target_user_id = user_id
        if not target_user_id and request.body:
            try:
                data = json.loads(request.body)
                target_user_id = data.get('user_id')
            except Exception:
                pass
        
        if target_user_id:
            user = get_object_or_404(User, id=target_user_id)
            from apps.authentication.security_utils import clear_user_failed_attempts
            clear_user_failed_attempts(user, request=request)
            
            # Audit log superadmin action
            try:
                from apps.grievances.models import AuditLog
                from apps.admin_panel.audit_utils import get_client_ip
                AuditLog.objects.create(
                    user=request.user,
                    action='update',
                    target_model='User',
                    target_id=str(user.id),
                    description=f"Superadmin restored failed login attempts to 0 for {user.email}",
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
            except Exception as e:
                print(f"Failed to log clear_failed_login_attempts: {e}")
                
            return JsonResponse({
                'success': True,
                'message': f'Successfully restored failed login attempts to 0 for {user.email}.',
                'failed_login_attempts': 0
            })
        else:
            # Clear all old AdminLoginOTP records
            from apps.authentication.models import AdminLoginOTP
            deleted_count = AdminLoginOTP.objects.filter(
                created_at__lt=timezone.now() - timedelta(hours=1)
            ).delete()[0]
            return JsonResponse({
                'success': True,
                'message': f'Cleared expired login OTP records. Cleaned {deleted_count} record(s).'
            })
        
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@superadmin_required
def system_settings(request):
    """System settings view - Superadmin only"""
    from apps.admin_panel.models import SystemSettings
    
    settings_obj = SystemSettings.load()
    
    # Handle form submissions
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'all':
            # General
            settings_obj.system_name = request.POST.get('system_name', settings_obj.system_name)
            settings_obj.contact_email = request.POST.get('contact_email', settings_obj.contact_email)
            
            # Security & Access
            settings_obj.allow_student_registration = request.POST.get('allow_student_registration') == 'on'
            settings_obj.allowed_email_domains = request.POST.get('allowed_email_domains', '').strip()
            settings_obj.session_timeout = int(request.POST.get('session_timeout', settings_obj.session_timeout))
            settings_obj.password_min_length = int(request.POST.get('password_min_length', settings_obj.password_min_length))
            
            # Grievance Rules
            settings_obj.default_priority = request.POST.get('default_priority', settings_obj.default_priority)
            settings_obj.auto_resolve_days = int(request.POST.get('auto_resolve_days', settings_obj.auto_resolve_days))
            settings_obj.escalation_threshold = int(request.POST.get('escalation_threshold', settings_obj.escalation_threshold))
            
            # Workflow & SLA
            settings_obj.auto_assignment = request.POST.get('auto_assignment') == 'on'
            settings_obj.max_reopen_count = int(request.POST.get('max_reopen_count', settings_obj.max_reopen_count))
            settings_obj.sla_breach_action = request.POST.get('sla_breach_action', settings_obj.sla_breach_action)
            settings_obj.require_closure_remark = request.POST.get('require_closure_remark') == 'on'
            
            # Notifications
            settings_obj.email_notifications = request.POST.get('email_notifications') == 'on'
            
            # Student Experience
            settings_obj.allow_anonymous = request.POST.get('allow_anonymous') == 'on'
            settings_obj.allow_attachments_in_replies = request.POST.get('allow_attachments_in_replies') == 'on'
            settings_obj.max_file_size = int(request.POST.get('max_file_size', settings_obj.max_file_size))
            settings_obj.support_hours = request.POST.get('support_hours', settings_obj.support_hours)
            
            settings_obj.save()
            messages.success(request, 'System settings updated successfully!')
            return redirect('admin_panel:system_settings')
    
    context = {
        'settings': settings_obj,
    }
    
    return render(request, 'admin_panel/superadmin/system_settings.html', context)


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
                    name = request.POST.get('admin_name', '').strip() or request.POST.get('name', '').strip()
                    department = request.POST.get('admin_department')  # Changed from 'department' to 'admin_department'
                    employee_id = request.POST.get('employee_id')
                    phone = request.POST.get('phone', '')
                    office_location = request.POST.get('office_location', '')
                    
                    # Debug: Log the received values
                    print(f"DEBUG - Admin fields received:")
                    print(f"  name: '{name}'")
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
                        name=name,
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
        is_sqlite = connection.vendor == 'sqlite'
        
        import io
        import csv
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['User Email', 'Role', 'Grievance ID', 'Title', 'Status', 'Submitted At'])
        
        with transaction.atomic():
            for user in users_to_delete:
                user_id = user.id
                user_email = user.email
                user_role = user.role
                user_role_display = user.get_role_display()

                deleted_users_info.append({
                    'id': user_id,
                    'email': user_email,
                    'role': user_role
                })

                # Write user and grievance data to CSV backup before deletion
                if user.role == 'student' and hasattr(user, 'student_profile') and user.student_profile:
                    grievances = user.student_profile.grievances.all()
                    if grievances.exists():
                        for g in grievances:
                            csv_writer.writerow([user_email, user_role, g.grievance_id, g.title, g.status, g.submitted_at])
                    else:
                        csv_writer.writerow([user_email, user_role, 'No Grievances', 'N/A', 'N/A', 'N/A'])
                else:
                    csv_writer.writerow([user_email, user_role, 'N/A', 'N/A', 'N/A', 'N/A'])

                # 1. Clean up HOD reference if user heads any department
                affected_depts = list(Department.objects.filter(head_of_department=user))
                Department.objects.filter(head_of_department=user).update(head_of_department=None)

                # 2. Clean up CategoryAssignment & assigned grievances if admin profile exists
                if hasattr(user, 'admin_profile') and user.admin_profile:
                    Grievance.objects.filter(assigned_to=user.admin_profile).update(assigned_to=None)
                    CategoryAssignment.objects.filter(assigned_admin=user.admin_profile).delete()

                # 3. Clean up read notifications for this user
                ReadNotification.objects.filter(student=user).delete()

                # 4. Create AuditLog entry before user deletion to keep full record
                AuditLog.objects.create(
                    user=request.user,
                    action='delete',
                    description=f'Permanently deleted user {user_email} (Role: {user_role_display})',
                    target_model='User',
                    target_id=str(user_id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                # 5. Permanently delete the user account (cascades cleanly)
                user.delete()

                # Re-sync HODs for affected departments
                for dept in affected_depts:
                    dept.refresh_from_db()
                    dept.auto_assign_hod_if_needed(save=True)
        
        deleted_count = len(deleted_users_info)
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'deleted_users': deleted_users_info,
            'message': f'Successfully deleted {deleted_count} user(s)',
            'csv_report': csv_buffer.getvalue()
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

        # Sync HODs for any departments affected by deactivated admins
        for user_info in deactivated_users_info:
            if user_info.get('role') == 'admin':
                try:
                    user_obj = User.objects.get(id=user_info['id'])
                    if hasattr(user_obj, 'admin_profile') and user_obj.admin_profile:
                        for dept in Department.objects.filter(name__iexact=user_obj.admin_profile.department.strip()):
                            dept.auto_assign_hod_if_needed(save=True)
                except Exception:
                    pass
        
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

        # Sync HODs for any departments affected by reactivated admins
        for user_info in activated_users_info:
            if user_info.get('role') == 'admin':
                try:
                    user_obj = User.objects.get(id=user_info['id'])
                    if hasattr(user_obj, 'admin_profile') and user_obj.admin_profile:
                        for dept in Department.objects.filter(name__iexact=user_obj.admin_profile.department.strip()):
                            dept.auto_assign_hod_if_needed(save=True)
                except Exception:
                    pass
        
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
            'failed_login_attempts': user.failed_login_attempts,
            'last_failed_login': user.last_failed_login,
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
        
        # Add admin profile information if user is an admin, officer, or superadmin
        elif user.role in ['admin', 'officer', 'superadmin']:
            print("User is an admin/officer/superadmin, looking for AdminProfile...")
            try:
                admin_profile = AdminProfile.objects.get(user=user)
                print(f"Found admin profile: role_level={admin_profile.role_level}, department={admin_profile.department}")
                user_details['admin_profile'] = {
                    'name': admin_profile.name,
                    'employee_id': admin_profile.employee_id,
                    'department': admin_profile.department,
                    'phone': admin_profile.phone,
                    'office_location': admin_profile.office_location,
                    'role_level': admin_profile.get_role_level_display(),
                }
                user_details['name'] = admin_profile.name or (f"{admin_profile.get_role_level_display()} ({admin_profile.employee_id})" if user.role != 'superadmin' else 'Super Administrator')
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
                    'name': admin_data.get('name', ''),
                    'role_level': new_role,
                    'department': admin_data.get('department', ''),
                    'employee_id': admin_data.get('employee_id', ''),
                    'phone': admin_data.get('phone', ''),
                    'office_location': admin_data.get('office_location', ''),
                }
            )
            
            if not created:
                # Update existing profile - Superadmin is authorized to update name & employee_id
                admin_profile.role_level = new_role
                admin_profile.department = admin_data.get('department', admin_profile.department)
                if 'name' in admin_data:
                    admin_profile.name = admin_data.get('name', '').strip()
                if 'employee_id' in admin_data and admin_data.get('employee_id'):
                    new_emp_id = admin_data.get('employee_id').strip()
                    if AdminProfile.objects.exclude(id=admin_profile.id).filter(employee_id=new_emp_id).exists():
                        return JsonResponse({'error': f'Employee ID "{new_emp_id}" is already in use by another user.'}, status=400)
                    admin_profile.employee_id = new_emp_id
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
            # For superadmin, update display name if provided
            name = data.get('name')
            if name:
                try:
                    admin_profile = AdminProfile.objects.get(user=user)
                    admin_profile.name = name.strip()
                    admin_profile.save()
                except AdminProfile.DoesNotExist:
                    pass
            # Remove student profile if role was somehow changed
            try:
                student_profile = StudentProfile.objects.get(user=user)
                student_profile.delete()
                print("Removed existing student profile for superadmin")
            except StudentProfile.DoesNotExist:
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

@superadmin_required
def import_users_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        import csv
        import io
        from django.contrib.auth.hashers import make_password
        
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('admin_panel:user_management')
            
        dataset = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(dataset)
        reader = csv.reader(io_string, delimiter=',')
        
        header = next(reader, None)  # Skip header
        created_count = 0
        error_count = 0
        
        with transaction.atomic():
            for row in reader:
                try:
                    if len(row) >= 6: # email, password, role, name, student_id/emp_id, department
                        email = row[0].strip()
                        password = row[1].strip()
                        role = row[2].strip()
                        name = row[3].strip()
                        sid_eid = row[4].strip()
                        dept = row[5].strip()
                        
                        if User.objects.filter(email=email).exists():
                            error_count += 1
                            continue
                            
                        user = User.objects.create(
                            email=email,
                            role=role,
                            is_email_verified=True
                        )
                        user.set_password(password)
                        user.save()
                        
                        if role == 'student':
                            StudentProfile.objects.create(
                                user=user, name=name, student_id=sid_eid, department=dept, school="Default"
                            )
                        else:
                            AdminProfile.objects.create(
                                user=user, role_level=role, employee_id=sid_eid, department=dept
                            )
                        created_count += 1
                except Exception as e:
                    error_count += 1
                    
        messages.success(request, f'Successfully imported {created_count} users. {error_count} errors.')
    return redirect('admin_panel:user_management')

