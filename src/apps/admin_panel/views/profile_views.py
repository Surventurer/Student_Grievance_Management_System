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
@role_required(['admin', 'officer', 'superadmin'])
def admin_profile_view(request):
    """Admin profile view - similar to student profile but for admin/officer users"""
    
    try:
        # Get admin profile - handle both admin and officer roles
        if hasattr(request.user, 'admin_profile'):
            admin_profile = request.user.admin_profile
        else:
            # If no admin profile exists, auto-create for superadmin, otherwise show error
            if request.user.role == 'superadmin':
                from apps.students.models import AdminProfile
                admin_profile = AdminProfile.objects.create(
                    user=request.user,
                    role_level='superadmin',
                    employee_id=f'SA-{request.user.id}',
                    department='Administration'
                )
            else:
                messages.error(request, 'Admin profile not found. Please contact system administrator.')
                return redirect('admin_panel:dashboard')
    except AdminProfile.DoesNotExist:
        if request.user.role == 'superadmin':
            from apps.students.models import AdminProfile
            admin_profile = AdminProfile.objects.create(
                user=request.user,
                role_level='superadmin',
                employee_id=f'SA-{request.user.id}',
                department='Administration'
            )
        else:
            messages.error(request, 'Admin profile not found. Please contact system administrator.')
            return redirect('admin_panel:dashboard')
    
    return render(request, 'admin_panel/profile.html', {
        'admin_profile': admin_profile,
        'user_role': request.user.role,
        'user_department': request.user.department_name
    })



@login_required
@role_required(['admin', 'officer', 'superadmin'])
def update_admin_contact_view(request):
    """Update admin contact information"""
    
    try:
        admin_profile = request.user.admin_profile
    except AdminProfile.DoesNotExist:
        messages.error(request, 'Admin profile not found')
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        employee_id = request.POST.get('employee_id', '').strip()
        phone = request.POST.get('phone', '').strip()
        office_location = request.POST.get('office_location', '').strip()
        
        # Validate phone number
        if phone and not phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            messages.error(request, 'Phone number should contain only digits, spaces, hyphens, and plus sign')
            return redirect('admin_panel:profile')
        
        if phone and (len(phone.replace('+', '').replace('-', '').replace(' ', '')) < 10 or 
                     len(phone.replace('+', '').replace('-', '').replace(' ', '')) > 15):
            messages.error(request, 'Phone number should be between 10-15 digits')
            return redirect('admin_panel:profile')
        
        # Update contact information
        admin_profile.name = name
        if employee_id:
            # Check if employee_id is already taken by someone else
            if AdminProfile.objects.exclude(id=admin_profile.id).filter(employee_id=employee_id).exists():
                messages.error(request, 'This Employee ID is already in use by another user.')
                return redirect('admin_panel:profile')
            admin_profile.employee_id = employee_id
            
        admin_profile.phone = phone
        admin_profile.office_location = office_location
        admin_profile.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='update_profile',
            description=f'Updated contact information',
            target_model='AdminProfile',
            target_id=str(admin_profile.id)
        )
        
        messages.success(request, 'Contact information updated successfully')
        return redirect('admin_panel:profile')
    
    return redirect('admin_panel:profile')



@login_required
@role_required(['admin', 'officer', 'superadmin'])
def admin_send_verification_otp(request):
    """Send email verification OTP to admin/superadmin"""
    user = request.user
    if user.is_email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('admin_panel:profile')
        
    from apps.authentication.models import EmailVerification
    from apps.authentication.views import generate_otp
    from django.core.mail import send_mail
    from django.utils import timezone
    from datetime import timedelta
    from django.conf import settings
    
    # Generate new OTP
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=10)
    
    # Invalidate previous unused OTPs
    EmailVerification.objects.filter(user=user, is_used=False).update(is_used=True)
    
    EmailVerification.objects.create(
        user=user,
        otp=otp,
        expires_at=expires_at
    )
    
    try:
        send_mail(
            'Verify Your Email - Student Grievance System',
            f'Hello {user.email},\n\nYour OTP for email verification is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nThank you!',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(request, 'Verification OTP sent to your email! Please enter it below.')
        # We can store a flag in session to show the OTP modal/field on the profile page
        request.session['show_verify_otp'] = True
    except Exception as e:
        messages.error(request, 'Failed to send OTP email. Please try again later.')
        
    return redirect('admin_panel:profile')



@login_required
@role_required(['admin', 'officer', 'superadmin'])
def admin_verify_email_otp(request):
    """Verify OTP and mark email as verified"""
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        user = request.user
        
        from apps.authentication.models import EmailVerification
        
        verification = EmailVerification.objects.filter(
            user=user,
            otp=otp,
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification:
            messages.error(request, 'Invalid OTP. Please check and try again.')
            request.session['show_verify_otp'] = True
            return redirect('admin_panel:profile')
            
        if verification.is_expired:
            messages.error(request, 'OTP has expired. Please request a new one.')
            request.session['show_verify_otp'] = True
            return redirect('admin_panel:profile')
            
        # Success!
        verification.is_used = True
        verification.save()
        
        user.is_email_verified = True
        user.save()
        
        request.session.pop('show_verify_otp', None)
        messages.success(request, 'Your email has been successfully verified!')
        
    return redirect('admin_panel:profile')



@login_required
@role_required(['admin', 'officer', 'superadmin'])
def change_admin_password_view(request):
    """Change password for admin/officer users"""
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('admin_panel:profile')
        
        # Validate new passwords match
        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match')
            return redirect('admin_panel:profile')
        
        # Validate password strength
        if len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('admin_panel:profile')
        
        # Check if password contains common weak patterns
        if new_password1.lower() in ['password', '12345678', 'qwerty123']:
            messages.error(request, 'Password is too common. Please choose a stronger password')
            return redirect('admin_panel:profile')
        
        # Update password
        request.user.set_password(new_password1)
        request.user.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='change_password',
            description=f'Changed password',
            target_model='User',
            target_id=str(request.user.id)
        )
        
        messages.success(request, 'Password changed successfully. Please login again.')
        return redirect('authentication:login')
    
    return redirect('admin_panel:profile')

