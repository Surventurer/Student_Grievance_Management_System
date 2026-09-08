import csv
import json
import uuid
from datetime import datetime, timedelta

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction, IntegrityError
from django.db.models import Count, Q, Avg, Sum, Case, When, IntegerField, F, Max
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.grievances.models import (
    Grievance, Category, GrievanceComment, AuditLog, CategoryAssignment,
    GrievanceAttachment, GrievanceStatusHistory, GrievanceAssignmentHistory
)
from apps.notifications.models import Notification
from apps.students.models import School, Department, StudentProfile, AdminProfile
from apps.authentication.models import User
from apps.authentication.decorators import (
    dept_admin_required, admin_required, superadmin_required, permission_required, role_required
)
from apps.admin_panel.permissions import (
    filter_grievances_by_access, filter_students_by_access, can_access_all_data,
    can_manage_system_settings, can_manage_categories, can_manage_auto_assignment,
    can_view_audit_logs, can_view_system_reports, department_access_required
)


@login_required
@department_access_required  
def department_users_list(request):
    """Department users list view with CRUD operations for students and officers"""
    user = request.user
    
    # Only admin and superadmin can access this view
    if not user.is_admin_or_officer:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    role_filter = request.GET.get('role', '')
    
    # Get all users (students and officers) from user's department
    if user.is_superadmin:
        # Superadmin can see all users
        all_users = User.objects.all()
    else:
        # Department admin can only see users from their department
        user_department = user.department_name
        if not user_department:
            messages.error(request, 'You are not assigned to any department')
            return redirect('admin_panel:dashboard')
        
        # Use Q objects to filter users from the department instead of union
        department_filter = Q(
            role='student',
            student_profile__department=user_department
        ) | Q(
            role='officer',
            admin_profile__department=user_department
        ) | Q(
            role='admin',
            admin_profile__department=user_department
        )
        
        all_users = User.objects.filter(department_filter)
    
    # Apply select_related and filters
    users = all_users.select_related('student_profile', 'admin_profile')
    
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(student_profile__name__icontains=search_query) |
            Q(student_profile__student_id__icontains=search_query) |
            Q(admin_profile__employee_id__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Pagination — current user always sorted to the bottom
    from django.db.models import Case, When, IntegerField
    users = users.annotate(
        is_current_user=Case(
            When(id=request.user.id, then=1),
            default=0,
            output_field=IntegerField()
        )
    ).order_by('is_current_user', '-created_at')
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    # Calculate statistics
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    student_count = users.filter(role='student').count()
    officer_count = users.filter(role='officer').count()
    admin_count = users.filter(role='admin').count()
    
    # Get role choices - department admins can only create students and officers
    if user.is_superadmin:
        role_choices = [
            (role_code, role_name) for role_code, role_name in User.ROLE_CHOICES 
            if role_code != 'superadmin'
        ]
    else:
        # Department admins can only create students and officers
        role_choices = [
            ('student', 'Student'),
            ('officer', 'Grievance Officer')
        ]
    
    context = {
        'users': users_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'role_choices': role_choices,
        'user_department': user.department_name,
        'can_create_users': user.is_admin or user.is_superadmin,
        'can_edit_users': user.is_admin or user.is_superadmin,
        'total_users': total_users,
        'active_users': active_users,
        'student_count': student_count,
        'officer_count': officer_count,
        'admin_count': admin_count,
    }
    
    return render(request, 'admin_panel/department_users.html', context)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_students(request):
    """Manage students API"""
    if not request.user.is_admin_or_officer:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    students = StudentProfile.objects.all()
    
    return Response([
        {
            'id': s.id,
            'student_id': s.student_id,
            'name': s.user.get_full_name(),
            'email': s.user.email,
            'department': s.department,
            'is_active': s.user.is_active,
        }
        for s in students
    ])



@login_required
@department_access_required
def student_detail_view(request, student_id):
    """Student detail view with role-based access control"""
    user = request.user
    
    try:
        student = StudentProfile.objects.select_related('user').get(id=student_id)
        
        # Check if user can access this student
        from apps.admin_panel.permissions import can_access_student
        if not can_access_student(user, student):
            messages.error(request, 'Access denied - You can only view students from your department')
            return redirect('admin_panel:student_list')
        
        # Get student's grievances that the user can access
        all_grievances = Grievance.objects.filter(student=student).select_related('category')
        accessible_grievances = filter_grievances_by_access(user, all_grievances)
        grievances = accessible_grievances.order_by('-submitted_at')
        
        # Get statistics from accessible grievances
        grievance_stats = grievances.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            resolved=Count('id', filter=Q(status='resolved')),
            rejected=Count('id', filter=Q(status='rejected'))
        )
        
        context = {
            'student': student,
            'grievances': grievances,
            'grievance_stats': grievance_stats,
        }
        
        return render(request, 'admin_panel/student_detail.html', context)
        
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student not found')
        return redirect('admin_panel:student_list')



@login_required
def student_stats_api(request):
    """API endpoint to get student statistics"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        total_students = StudentProfile.objects.count()
        active_students = StudentProfile.objects.filter(user__is_active=True).count()
        suspended_students = StudentProfile.objects.filter(user__is_active=False).count()
        
        # Calculate average grievances per student
        avg_grievances = StudentProfile.objects.annotate(
            grievance_count=Count('grievances')
        ).aggregate(
            avg=Avg('grievance_count')
        )['avg']
        
        stats = {
            'total': total_students,
            'active': active_students,
            'suspended': suspended_students,
            'avg_grievances': round(avg_grievances, 1) if avg_grievances else 0,
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def student_actions_api(request):
    """API endpoint to perform bulk actions on students (suspend/activate/delete)"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied - Admin privileges required'}, status=403)
    
    try:
        data = json.loads(request.body)
        action = data.get('action', '')
        student_ids = data.get('student_ids', [])
        
        if not action or not student_ids:
            return JsonResponse({'error': 'Action and student IDs are required'}, status=400)
        
        if action not in ['suspend', 'activate', 'delete']:
            return JsonResponse({'error': 'Invalid action. Must be suspend, activate, or delete'}, status=400)
        
        # Get students to operate on
        students = StudentProfile.objects.filter(id__in=student_ids).select_related('user')
        
        if not students.exists():
            return JsonResponse({'error': 'No valid students found'}, status=404)
        
        affected_students = []
        
        if action == 'delete':
            # Complete deletion including all related data
            for student in students:
                affected_students.append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'name': student.name or student.user.email,
                    'email': student.user.email,
                    'grievance_count': student.grievances.count()
                })
                
                # Log the deletion
                try:
                    AuditLog.objects.create(
                        user=request.user,
                        action='delete',
                        target_model='StudentProfile',
                        target_id=str(student.id),
                        description=f'Deleted student: {student.student_id} - {student.name or student.user.email}',
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                    )
                except Exception as e:
                    print(f"Error creating audit log: {e}")
                
                # Delete user (will cascade to student profile and grievances)
                student.user.delete()
            
            affected_count = len(affected_students)
            
        elif action in ['suspend', 'activate']:
            # Suspend or activate students
            new_status = action == 'activate'
            
            for student in students:
                affected_students.append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'name': student.name or student.user.email,
                    'email': student.user.email,
                    'old_status': 'Active' if student.user.is_active else 'Suspended',
                    'new_status': 'Active' if new_status else 'Suspended'
                })
                
                # Update status
                student.user.is_active = new_status
                student.user.save()
                
                # Log the action
                try:
                    AuditLog.objects.create(
                        user=request.user,
                        action='update',
                        target_model='StudentProfile',
                        target_id=str(student.id),
                        description=f'{action.title()}d student: {student.student_id} - {student.name or student.user.email}',
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                    )
                except Exception as e:
                    print(f"Error creating audit log: {e}")
            
            affected_count = students.count()
        
        return JsonResponse({
            'success': True,
            'action': action,
            'affected_count': affected_count,
            'affected_students': affected_students,
            'message': f'Successfully {action}d {affected_count} student(s)'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error in student_actions_api: {e}")
        return JsonResponse({'error': f'An error occurred while trying to {action} students'}, status=500)



@login_required
def add_student_api(request):
    """API endpoint to add a new student"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from django.contrib.auth import get_user_model
        from apps.students.models import School, Department
        import uuid
        
        User = get_user_model()
        
        # Get form data
        email = request.POST.get('email')
        student_id = request.POST.get('student_id')
        name = request.POST.get('name')
        contact_no = request.POST.get('contact_no')
        school_id = request.POST.get('school')
        department_id = request.POST.get('department')
        year_of_study = request.POST.get('year_of_study')
        password = request.POST.get('password')
        address = request.POST.get('address')
        
        # Validate required fields
        if not all([email, student_id, name, password]):
            return JsonResponse({'error': 'Required fields missing'}, status=400)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'User with this email already exists'}, status=400)
        
        # Check if student ID already exists
        if StudentProfile.objects.filter(student_id=student_id).exists():
            return JsonResponse({'error': 'Student ID already exists'}, status=400)
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            role='student',
            is_active=True
        )
        
        # Get school and department names
        school_name = ''
        department_name = ''
        if school_id:
            try:
                from apps.students.models import School
                school = School.objects.get(id=school_id)
                school_name = school.name
            except School.DoesNotExist:
                pass
        
        if department_id:
            try:
                from apps.students.models import Department
                department = Department.objects.get(id=department_id)
                department_name = department.name
            except Department.DoesNotExist:
                pass
        
        # Create student profile
        student_profile = StudentProfile.objects.create(
            user=user,
            student_id=student_id,
            name=name,
            contact_no=contact_no or '',
            school=school_name,
            department=department_name
        )
        
        # Send email verification OTP
        try:
            from apps.authentication.models import EmailVerification
            from datetime import timedelta
            from django.utils import timezone
            import random
            import string
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))
            expires_at = timezone.now() + timedelta(minutes=30)  # 30 minutes expiry
            
            # Create EmailVerification record
            EmailVerification.objects.create(
                user=user,
                otp=otp,
                expires_at=expires_at
            )
            
            # Send email (if configured)
            try:
                send_mail(
                    subject='Email Verification - Student Grievance System',
                    message=f'''
Dear {name},

Your student account has been created successfully!

Student ID: {student_id}
Email: {email}
Verification OTP: {otp}

To verify your email and activate your account:
1. Go to the login page
2. Click "Verify Email"
3. Enter your Student ID: {student_id}
4. Enter this OTP: {otp}

This OTP will expire in 30 minutes.

Best regards,
Student Grievance Management System
                    ''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Error sending verification email: {e}")
                
        except Exception as e:
            print(f"Error creating verification OTP: {e}")
        
        # Log the action
        try:
            AuditLog.objects.create(
                user=request.user,
                action='create',
                target_model='StudentProfile',
                target_id=str(student_profile.id),
                description=f'Added new student: {student_id} - {name} ({email})',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
        except Exception as e:
            print(f"Error creating audit log: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Student added successfully',
            'student_id': student_profile.id,
            'student': {
                'id': student_profile.id,
                'student_id': student_profile.student_id,
                'name': student_profile.name,
                'email': user.email
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["GET"])
def users_search_api(request):
    """API endpoint for searching users for HOD assignment"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'users': []})
    
    from apps.authentication.models import User
    
    # Search for active users who could be HODs (admin, officer roles)
    users = User.objects.filter(
        Q(is_active=True) &
        Q(role__in=['admin', 'officer']) &  # Only admin and officer roles
        Q(email__icontains=query)  # Search by email only since that's the main field
    ).order_by('email')[:10]  # Limit to 10 results
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'name': user.email.split('@')[0],  # Use email prefix as display name
            'email': user.email,
            'role': user.role.title() if user.role else 'User'
        })
    
    return JsonResponse({'users': users_data})



@login_required
@role_required(['admin', 'superadmin'])
def edit_department_user(request, user_id):
    """Edit department user (student or officer)"""
    user = get_object_or_404(User, id=user_id)
    
    # Check if user can edit this user (department admin can only edit users from their department)
    if not request.user.is_superadmin:
        user_department = request.user.department_name
        if user.role == 'student' and hasattr(user, 'student_profile'):
            if user.student_profile.department != user_department:
                messages.error(request, 'Access denied - You can only edit users from your department')
                return redirect('admin_panel:department_users')
        elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
            if user.admin_profile.department != user_department:
                messages.error(request, 'Access denied - You can only edit users from your department')
                return redirect('admin_panel:department_users')
    
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Update user fields
        user.email = data.get('email', user.email)
        user.is_active = data.get('is_active', user.is_active)
        user.role = data.get('role', user.role)
        
        # Update profile fields based on role
        if user.role == 'student' and hasattr(user, 'student_profile'):
            profile = user.student_profile
            profile.name = data.get('name', profile.name)
            profile.student_id = data.get('student_id', profile.student_id)
            profile.department = data.get('department', profile.department)
            profile.school = data.get('school', profile.school)
            profile.contact_no = data.get('contact_no', profile.contact_no)
            profile.save()
        elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
            profile = user.admin_profile
            profile.employee_id = data.get('employee_id', profile.employee_id)
            profile.department = data.get('department', profile.department)
            profile.phone = data.get('phone', profile.phone)
            profile.office_location = data.get('office_location', profile.office_location)
            profile.save()
        
        user.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='edit_user',
            description=f'Edited user: {user.email}',
            target_model='User',
            target_id=str(user.id)
        )
        
        return JsonResponse({'success': True, 'message': 'User updated successfully'})
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@login_required
@role_required(['admin', 'superadmin'])
def toggle_department_user_status(request, user_id):
    """Toggle user active/inactive status"""
    user = get_object_or_404(User, id=user_id)
    
    # Check department access
    if not request.user.is_superadmin:
        user_department = request.user.department_name
        if user.role == 'student' and hasattr(user, 'student_profile'):
            if user.student_profile.department != user_department:
                return JsonResponse({'error': 'Access denied'}, status=403)
        elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
            if user.admin_profile.department != user_department:
                return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Toggle status
    user.is_active = not user.is_active
    user.save()
    
    # Create audit log
    action = 'activate_user' if user.is_active else 'deactivate_user'
    status_text = 'activated' if user.is_active else 'deactivated'
    
    AuditLog.objects.create(
        user=request.user,
        action=action,
        description=f'User {status_text}: {user.email}',
        target_model='User',
        target_id=str(user.id)
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'User {status_text} successfully',
        'is_active': user.is_active
    })



@login_required
@role_required(['admin', 'superadmin'])
def update_department_user_role(request, user_id):
    """Update user role"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        new_role = data.get('role')
        
        if new_role not in [choice[0] for choice in User.ROLE_CHOICES]:
            return JsonResponse({'error': 'Invalid role'}, status=400)
        
        # Check department access
        if not request.user.is_superadmin:
            user_department = request.user.department_name
            if user.role == 'student' and hasattr(user, 'student_profile'):
                if user.student_profile.department != user_department:
                    return JsonResponse({'error': 'Access denied'}, status=403)
            elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
                if user.admin_profile.department != user_department:
                    return JsonResponse({'error': 'Access denied'}, status=403)
        
        old_role = user.role
        user.role = new_role
        user.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='update_user_role',
            description=f'Changed user role from {old_role} to {new_role}: {user.email}',
            target_model='User',
            target_id=str(user.id)
        )
        
        return JsonResponse({'success': True, 'message': 'User role updated successfully'})
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@login_required
@role_required(['admin', 'superadmin'])
def bulk_activate_department_users(request):
    """Bulk activate users"""
    if request.method == 'POST':
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        # Filter users by department access if not superadmin
        users = User.objects.filter(id__in=user_ids)
        if not request.user.is_superadmin:
            user_department = request.user.department_name
            accessible_users = []
            for user in users:
                if user.role == 'student' and hasattr(user, 'student_profile'):
                    if user.student_profile.department == user_department:
                        accessible_users.append(user)
                elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
                    if user.admin_profile.department == user_department:
                        accessible_users.append(user)
            users = accessible_users
        
        # Activate users
        activated_count = 0
        user_emails = []
        for user in users:
            if not user.is_active:
                user.is_active = True
                user.save()
                activated_count += 1
                user_emails.append(user.email)
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_activate_users',
            description=f'Bulk activated {activated_count} users: {", ".join(user_emails)}',
            target_model='User',
            target_id=str(user_ids)
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully activated {activated_count} user(s)',
            'activated_count': activated_count
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@login_required
@role_required(['admin', 'superadmin'])
def bulk_deactivate_department_users(request):
    """Bulk deactivate users"""
    if request.method == 'POST':
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        # Filter users by department access if not superadmin
        users = User.objects.filter(id__in=user_ids)
        if not request.user.is_superadmin:
            user_department = request.user.department_name
            accessible_users = []
            for user in users:
                if user.role == 'student' and hasattr(user, 'student_profile'):
                    if user.student_profile.department == user_department:
                        accessible_users.append(user)
                elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
                    if user.admin_profile.department == user_department:
                        accessible_users.append(user)
            users = accessible_users
        
        # Deactivate users
        deactivated_count = 0
        user_emails = []
        for user in users:
            if user.is_active:
                user.is_active = False
                user.save()
                deactivated_count += 1
                user_emails.append(user.email)
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_deactivate_users',
            description=f'Bulk deactivated {deactivated_count} users: {", ".join(user_emails)}',
            target_model='User',
            target_id=str(user_ids)
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully deactivated {deactivated_count} user(s)',
            'deactivated_count': deactivated_count
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@login_required
@role_required(['admin', 'superadmin'])
def bulk_delete_department_users(request):
    """Bulk delete users (soft delete by deactivation)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        # Filter users by department access if not superadmin
        users = User.objects.filter(id__in=user_ids)
        if not request.user.is_superadmin:
            user_department = request.user.department_name
            accessible_users = []
            for user in users:
                if user.role == 'student' and hasattr(user, 'student_profile'):
                    if user.student_profile.department == user_department:
                        accessible_users.append(user)
                elif user.role in ['admin', 'officer'] and hasattr(user, 'admin_profile'):
                    if user.admin_profile.department == user_department:
                        accessible_users.append(user)
            users = accessible_users
        
        # Soft delete users (deactivate them)
        deleted_count = 0
        user_emails = []
        for user in users:
            if user.is_active:
                user.is_active = False
                user.save()
                deleted_count += 1
                user_emails.append(user.email)
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='bulk_delete_users',
            description=f'Bulk deleted (deactivated) {deleted_count} users: {", ".join(user_emails)}',
            target_model='User',
            target_id=str(user_ids)
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted {deleted_count} user(s)',
            'deleted_count': deleted_count
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@login_required
@role_required(['admin', 'superadmin'])
@dept_admin_required
def create_department_user(request):
    """Create new department user - Department admins can only create students and officers"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        # Validate required fields
        email = data.get('email', '').strip()
        role = data.get('role', '').strip()
        
        if not email or not role:
            return JsonResponse({'error': 'Email and role are required'}, status=400)
        
        # Department admins can only create students and officers, not other admins
        if role not in ['student', 'officer']:
            return JsonResponse({'error': 'You can only create students and officers'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'User with this email already exists'}, status=400)
        
        # Get admin's department
        try:
            admin_profile = AdminProfile.objects.get(user=request.user)
            department = admin_profile.department
        except AdminProfile.DoesNotExist:
            return JsonResponse({'error': 'Admin profile not found'}, status=400)
        
        # Create user with default password
        user = User.objects.create_user(
            email=email,
            password='TempPassword123!',  # User should change this on first login
            role=role,
            is_active=True,
            is_email_verified=True
        )
        
        # Create profile based on role
        if role == 'student':
            from apps.students.models import StudentProfile
            StudentProfile.objects.create(
                user=user,
                name=data.get('name', '').strip(),
                student_id=data.get('student_id', '').strip(),
                department=department,  # Use admin's department
                school=data.get('school', '').strip(),
                contact_no=data.get('contact_no', '').strip()
            )
        elif role == 'officer':
            AdminProfile.objects.create(
                user=user,
                role_level='officer',
                department=department,  # Use admin's department
                employee_id=data.get('employee_id', '').strip(),
                phone=data.get('phone', '').strip(),
                office_location=data.get('office_location', '').strip()
            )
        
        return JsonResponse({
            'success': True, 
            'message': f'User created successfully. Default password: TempPassword123!'
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@dept_admin_required
def get_department_user_details(request, user_id):
    """Get detailed information about a department user"""
    try:
        from apps.students.models import StudentProfile, AdminProfile
        
        # Get the current admin's department
        admin_profile = AdminProfile.objects.get(user=request.user)
        department = admin_profile.department
        
        # Check if user belongs to the same department
        user = get_object_or_404(User, id=user_id)
        
        # Verify user is in the same department
        user_belongs_to_dept = False
        if user.role == 'student':
            try:
                student_profile = StudentProfile.objects.get(user=user)
                user_belongs_to_dept = student_profile.department == department
            except StudentProfile.DoesNotExist:
                pass
        elif user.role in ['admin', 'officer']:
            try:
                user_admin_profile = AdminProfile.objects.get(user=user)
                user_belongs_to_dept = user_admin_profile.department == department
            except AdminProfile.DoesNotExist:
                pass
        
        if not user_belongs_to_dept:
            return JsonResponse({'error': 'User not found in your department'}, status=404)
        
        # Basic user information
        user_details = {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'role_display': user.get_role_display(),
            'is_active': user.is_active,
            'is_email_verified': user.is_email_verified,
            'date_joined': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            'deactivation_reason': user.deactivation_reason,
            'name': None,
            'student_profile': None,
            'admin_profile': None,
        }
        
        # Add student profile information if user is a student
        if user.role == 'student':
            try:
                student_profile = StudentProfile.objects.get(user=user)
                user_details['student_profile'] = {
                    'student_id': student_profile.student_id,
                    'name': student_profile.name,
                    'school': student_profile.school,
                    'department': student_profile.department,
                    'contact_no': student_profile.contact_no,
                }
                user_details['name'] = student_profile.name
            except StudentProfile.DoesNotExist:
                user_details['student_profile'] = None
        
        # Add admin profile information if user is an admin or officer
        elif user.role in ['admin', 'officer']:
            try:
                user_admin_profile = AdminProfile.objects.get(user=user)
                user_details['admin_profile'] = {
                    'employee_id': user_admin_profile.employee_id,
                    'department': user_admin_profile.department,
                    'phone': user_admin_profile.phone,
                    'office_location': user_admin_profile.office_location,
                    'role_level': user_admin_profile.get_role_level_display(),
                }
                user_details['name'] = f"{user_admin_profile.get_role_level_display()} ({user_admin_profile.employee_id})"
            except AdminProfile.DoesNotExist:
                user_details['admin_profile'] = None
        
        # For other roles, try to get name from email
        if not user_details['name']:
            user_details['name'] = user.email.split('@')[0].title()
        
        return JsonResponse({
            'success': True,
            'user': user_details
        })
        
    except AdminProfile.DoesNotExist:
        return JsonResponse({'error': 'Admin profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@dept_admin_required
@require_http_methods(["POST"])
def toggle_department_user_status(request, user_id):
    """Toggle department user active status"""
    try:
        from apps.students.models import StudentProfile, AdminProfile
        
        # Get the current admin's department
        admin_profile = AdminProfile.objects.get(user=request.user)
        department = admin_profile.department
        
        user = get_object_or_404(User, id=user_id)
        
        # Prevent deactivating self
        if user.id == request.user.id:
            return JsonResponse({'error': 'Cannot deactivate your own account'}, status=400)
        
        # Verify user is in the same department
        user_belongs_to_dept = False
        if user.role == 'student':
            try:
                student_profile = StudentProfile.objects.get(user=user)
                user_belongs_to_dept = student_profile.department == department
            except StudentProfile.DoesNotExist:
                pass
        elif user.role in ['admin', 'officer']:
            try:
                user_admin_profile = AdminProfile.objects.get(user=user)
                user_belongs_to_dept = user_admin_profile.department == department
            except AdminProfile.DoesNotExist:
                pass
        
        if not user_belongs_to_dept:
            return JsonResponse({'error': 'User not found in your department'}, status=404)
        
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
        
        return JsonResponse({
            'success': True,
            'message': f'User {status_text} successfully',
            'is_active': user.is_active
        })
        
    except AdminProfile.DoesNotExist:
        return JsonResponse({'error': 'Admin profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@dept_admin_required
def bulk_department_users_action(request):
    """Handle bulk actions for department users"""
    print(f"bulk_department_users_action called with method: {request.method}")
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    action = request.POST.get('action')
    user_ids = request.POST.getlist('user_ids[]')
    print(f"Action: {action}, User IDs: {user_ids}")
    
    if not action or not user_ids:
        return JsonResponse({'error': 'Action and user IDs are required'}, status=400)
    
    try:
        from apps.students.models import StudentProfile, AdminProfile
        
        admin_profile = AdminProfile.objects.get(user=request.user)
        department = admin_profile.department
        
        # Get users from the same department (excluding self)
        department_users = []
        for user_id in user_ids:
            if int(user_id) == request.user.id:
                continue  # Skip self
                
            try:
                user = User.objects.get(id=user_id)
                user_belongs_to_dept = False
                
                if user.role == 'student':
                    try:
                        student_profile = StudentProfile.objects.get(user=user)
                        user_belongs_to_dept = student_profile.department == department
                    except StudentProfile.DoesNotExist:
                        pass
                elif user.role in ['admin', 'officer']:
                    try:
                        user_admin_profile = AdminProfile.objects.get(user=user)
                        user_belongs_to_dept = user_admin_profile.department == department
                    except AdminProfile.DoesNotExist:
                        pass
                
                if user_belongs_to_dept:
                    department_users.append(user)
            except User.DoesNotExist:
                continue
        
        if not department_users:
            return JsonResponse({'error': 'No valid users found for this action'}, status=400)
        
        count = len(department_users)
        
        if action == 'activate':
            for user in department_users:
                user.is_active = True
                user.deactivation_reason = None
                user.save()
            message = f'Successfully activated {count} users'
        elif action == 'deactivate':
            reason = request.POST.get('reason', 'Bulk deactivation by department admin')
            for user in department_users:
                user.is_active = False
                user.deactivation_reason = reason
                user.save()
            message = f'Successfully deactivated {count} users'
        elif action == 'delete':
            for user in department_users:
                user.delete()
            message = f'Successfully deleted {count} users'
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        return JsonResponse({'success': True, 'message': message})
        
    except AdminProfile.DoesNotExist:
        return JsonResponse({'error': 'Admin profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

