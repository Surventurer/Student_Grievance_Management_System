from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count, Max
from django.utils import timezone
from datetime import timedelta

from .models import StudentProfile, AdminProfile, Department
from .serializers import StudentProfileSerializer, AdminProfileSerializer, DepartmentSerializer
from apps.authentication.models import User
from apps.grievances.models import Grievance, GrievanceComment
from apps.notifications.models import ReadNotification, Notification
from apps.admin_panel.models import SystemSettings
from django.shortcuts import get_object_or_404


def get_student_notifications(user, exclude_viewed=True):
    """Get unread admin messages for student"""
    if not user.is_authenticated or not user.is_student:
        return []
    
    try:
        student_profile = user.student_profile
        
        # Get recent admin messages (within last 7 days)
        recent_time = timezone.now() - timedelta(days=7)
        
        notifications = GrievanceComment.objects.filter(
            grievance__student=student_profile,
            user__role__in=['admin', 'superadmin', 'officer'],  # Filter by admin roles
            is_internal=False,  # Only public messages
            timestamp__gte=recent_time
        ).select_related('grievance', 'user')
        
        # Exclude read notifications if requested
        if exclude_viewed:
            read_notification_ids = ReadNotification.objects.filter(
                student=user
            ).values_list('comment_id', flat=True)
            notifications = notifications.exclude(id__in=read_notification_ids)
            
        return notifications.order_by('-timestamp')[:10]
    except StudentProfile.DoesNotExist:
        return []


def mark_grievance_notifications_read(user, grievance):
    """Mark all notifications for a specific grievance as read"""
    if not user.is_authenticated or not user.is_student:
        return
    
    try:
        # Get all unread admin comments for this grievance
        admin_comments = GrievanceComment.objects.filter(
            grievance=grievance,
            user__role__in=['admin', 'superadmin', 'officer'],
            is_internal=False
        )
        
        # Mark them as read (bulk create, ignore duplicates)
        read_notifications = []
        for comment in admin_comments:
            read_notifications.append(
                ReadNotification(student=user, comment=comment)
            )
        
        # Use bulk_create with ignore_conflicts to avoid duplicate key errors
        ReadNotification.objects.bulk_create(
            read_notifications, 
            ignore_conflicts=True
        )
        
    except Exception as e:
        # Log error but don't fail the main request
        print(f"Error marking notifications as read: {e}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard(request):
    """Student dashboard API"""
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get student's grievances
    grievances = Grievance.objects.filter(student=student_profile, is_archived=False).order_by('-submitted_at')
    
    # Dashboard statistics
    total_grievances = grievances.count()
    pending_grievances = grievances.filter(status='pending').count()
    resolved_grievances = grievances.filter(status='resolved').count()
    
    # Recent grievances
    recent_grievances = grievances[:5]
    
    return Response({
        'student_profile': StudentProfileSerializer(student_profile).data,
        'statistics': {
            'total_grievances': total_grievances,
            'pending_grievances': pending_grievances,
            'resolved_grievances': resolved_grievances,
        },
        'recent_grievances': [
            {
                'id': g.id,
                'title': g.title,
                'status': g.status,
                'submitted_at': g.submitted_at,
                'category': g.category.name if g.category else None,
            }
            for g in recent_grievances
        ]
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def student_profile(request):
    """Get or update student profile"""
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = StudentProfileSerializer(student_profile)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = StudentProfileSerializer(student_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    """Admin dashboard API"""
    if not request.user.is_admin:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        admin_profile = request.user.admin_profile
    except AdminProfile.DoesNotExist:
        return Response({'error': 'Admin profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get grievances assigned to this admin
    if admin_profile.role_level == 'superadmin':
        grievances = Grievance.objects.all()
    else:
        grievances = Grievance.objects.filter(assigned_to=admin_profile)
    
    # Dashboard statistics
    total_grievances = grievances.count()
    pending_grievances = grievances.filter(status='pending').count()
    under_review_grievances = grievances.filter(status='under_review').count()
    resolved_grievances = grievances.filter(status='resolved').count()
    rejected_grievances = grievances.filter(status='rejected').count()
    
    # Recent grievances
    recent_grievances = grievances.order_by('-submitted_at')[:10]
    
    return Response({
        'admin_profile': AdminProfileSerializer(admin_profile).data,
        'statistics': {
            'total_grievances': total_grievances,
            'pending_grievances': pending_grievances,
            'under_review_grievances': under_review_grievances,
            'resolved_grievances': resolved_grievances,
            'rejected_grievances': rejected_grievances,
        },
        'recent_grievances': [
            {
                'id': g.id,
                'title': g.title,
                'status': g.status,
                'submitted_at': g.submitted_at,
                'student': g.student.student_id,
                'category': g.category.name if g.category else None,
            }
            for g in recent_grievances
        ]
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def admin_profile(request):
    """Get or update admin profile"""
    if not request.user.is_admin:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        admin_profile = request.user.admin_profile
    except AdminProfile.DoesNotExist:
        return Response({'error': 'Admin profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = AdminProfileSerializer(admin_profile)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = AdminProfileSerializer(admin_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_students(request):
    """Manage students - Admin only"""
    if not request.user.is_admin:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Search and filter students
    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')
    
    students = StudentProfile.objects.select_related('user').all()
    
    if search_query:
        students = students.filter(
            Q(student_id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    if department_filter:
        students = students.filter(department=department_filter)
    
    # Pagination
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return Response({
        'students': [
            {
                'id': s.id,
                'student_id': s.student_id,
                'name': s.user.get_full_name(),
                'email': s.user.email,
                'department': s.department,
                'is_active': s.user.is_active,
                'created_at': s.created_at,
            }
            for s in page_obj
        ],
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def departments(request):
    """Get all departments"""
    departments = Department.objects.all()
    serializer = DepartmentSerializer(departments, many=True)
    return Response(serializer.data)


# Web views
@login_required
def student_dashboard_view(request):
    """Student dashboard web view"""
    if not request.user.is_student:
        return redirect('admin_panel:dashboard')
    
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found')
        return redirect('authentication:login')
    
    # Get student's grievances
    grievances = Grievance.objects.filter(student=student_profile, is_archived=False).order_by('-submitted_at')
    
    context = {
        'student_profile': student_profile,
        'grievances': grievances[:5],  # Recent 5 grievances
        'total_grievances': grievances.count(),
        'pending_grievances': grievances.filter(status='pending').count(),
        'resolved_grievances': grievances.filter(status='resolved').count(),
    }
    
    return render(request, 'students/dashboard.html', context)


@login_required
def student_profile_view(request):
    """Student profile web view - restricted to only show profile info"""
    if not request.user.is_student:
        return redirect('admin_panel:dashboard')
    
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found')
        return redirect('authentication:login')
    
    return render(request, 'students/profile.html', {'student_profile': student_profile})


@login_required
def update_contact_view(request):
    """Update only contact number - restricted functionality"""
    if not request.user.is_student:
        return redirect('admin_panel:dashboard')
    
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        contact_no = request.POST.get('contact_no', '').strip()
        
        # Validate contact number
        if contact_no and not contact_no.isdigit():
            messages.error(request, 'Contact number should contain only digits')
            return redirect('students:profile')
        
        if contact_no and (len(contact_no) < 10 or len(contact_no) > 15):
            messages.error(request, 'Contact number should be between 10-15 digits')
            return redirect('students:profile')
        
        # Update contact number
        student_profile.contact_no = contact_no
        student_profile.save()
        
        messages.success(request, 'Contact number updated successfully')
        return redirect('students:profile')
    
    return redirect('students:profile')


@login_required  
def change_password_view(request):
    """Change password for student - restricted functionality"""
    if not request.user.is_student:
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('students:profile')
        
        # Validate new passwords match
        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match')
            return redirect('students:profile')
        
        # Validate password strength
        if len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('students:profile')
        
        # Update password
        request.user.set_password(new_password1)
        request.user.save()
        
        messages.success(request, 'Password changed successfully. Please login again.')
        return redirect('authentication:login')
    
    return redirect('students:profile')


@login_required
def student_grievances_view(request):
    """View all student grievances"""
    if not request.user.is_student:
        return redirect('admin_panel:dashboard')
    
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found')
        return redirect('authentication:login')
    
    # Get all student's grievances
    all_grievances = Grievance.objects.filter(student=student_profile, is_archived=False)
    grievances = all_grievances.order_by('-submitted_at')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Handle GRV-XXXX format search
        if search_query.upper().startswith('GRV-'):
            # Extract the UUID part after GRV-
            uuid_part = search_query[4:].upper()
            grievances = grievances.filter(
                Q(id__istartswith=uuid_part) |
                Q(title__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        else:
            grievances = grievances.filter(
                Q(id__icontains=search_query.upper()) |  # Search by UUID (case-insensitive)
                Q(title__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        grievances = grievances.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(grievances, 10)  # Show 10 grievances per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'student_profile': student_profile,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_grievances': all_grievances.count(),
        'pending_grievances': all_grievances.filter(status='pending').count(),
        'resolved_grievances': all_grievances.filter(status='resolved').count(),
        'filtered_count': grievances.count() if search_query or status_filter else all_grievances.count(),
    }
    
    return render(request, 'students/grievances.html', context)


@login_required
def student_grievance_detail_view(request, grievance_id):
    """View individual grievance details"""
    if not request.user.is_student:
        return redirect('admin_panel:dashboard')
    
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found')
        return redirect('authentication:login')
    
    try:
        grievance = Grievance.objects.get(id=grievance_id, student=student_profile)
    except Grievance.DoesNotExist:
        messages.error(request, 'Grievance not found')
        return redirect('students:grievances')
    
    # Mark all notifications for this grievance as read
    mark_grievance_notifications_read(request.user, grievance)
    
    appeals = grievance.appeals.select_related('reviewed_by__user').order_by('-created_at')
    appeal_attachments = grievance.attachments.filter(file_name__startswith='[Appeal #')
    latest_resolution = grievance.status_history.filter(new_status__in=['resolved', 'rejected']).order_by('-timestamp').first()
    
    context = {
        'student_profile': student_profile,
        'grievance': grievance,
        'appeals': appeals,
        'appeal_attachments': appeal_attachments,
        'latest_resolution': latest_resolution,
    }
    
    return render(request, 'students/grievance_detail.html', context)


@login_required
def add_student_response(request, grievance_id):
    """Add student response/reply to grievance"""
    if not request.user.is_student:
        messages.error(request, 'Access denied.')
        return redirect('students:dashboard')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('students:grievance_detail', grievance_id=grievance_id)
    
    try:
        student_profile = request.user.student_profile
        grievance = get_object_or_404(Grievance, id=grievance_id, student=student_profile)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', '')

        # Lock communication if grievance is resolved or rejected
        if grievance.status in ['resolved', 'rejected']:
            status_text = 'resolved' if grievance.status == 'resolved' else 'rejected'
            err_msg = f'This grievance has been {status_text}. No further messages can be sent unless an appeal is filed.'
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': err_msg
                }, status=400)
            messages.info(request, err_msg)
            from django.urls import reverse
            return redirect(reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id}))

        system_settings = SystemSettings.load()

        # Enforce support hours: Students cannot send messages outside active support hours
        if not system_settings.is_support_active:
            err_msg = f'Messages cannot be sent outside support hours ({system_settings.support_hours}). {system_settings.support_hours_message}'
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': err_msg
                }, status=403)
            messages.error(request, err_msg)
            from django.urls import reverse
            return redirect(reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id}))

        student_response = request.POST.get('student_response', '').strip()
        
        if not student_response and not request.FILES.get('attachment'):
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Response message or file attachment is required.'}, status=400)
            messages.error(request, 'Response message or file attachment is required.')
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            url = reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})
            return HttpResponseRedirect(f"{url}#message-form")
            
        attachment_obj = None
        attachment_file = request.FILES.get('attachment')
        
        if attachment_file and not system_settings.allow_attachments_in_replies:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Attachments in replies are disabled.'}, status=400)
            messages.error(request, 'Attachments in replies are currently disabled by the administration.')
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(f"{reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})}#message-form")

        if attachment_file:
            import os
            from apps.grievances.models import GrievanceAttachment
            ext = os.path.splitext(attachment_file.name)[1].lower().lstrip('.')
            if ext not in GrievanceAttachment.ALLOWED_EXTENSIONS:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': f'Invalid file type. Allowed: {", ".join(GrievanceAttachment.ALLOWED_EXTENSIONS)}'}, status=400)
                messages.error(request, f'Invalid file type. Allowed: {", ".join(GrievanceAttachment.ALLOWED_EXTENSIONS)}')
                from django.http import HttpResponseRedirect
                from django.urls import reverse
                return HttpResponseRedirect(f"{reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})}#message-form")
            
            max_size_bytes = system_settings.max_file_size * 1024 * 1024
            if attachment_file.size > max_size_bytes:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': f'Attachment exceeds maximum size of {system_settings.max_file_size}MB'}, status=400)
                messages.error(request, 'Attachment exceeds maximum size limit')
                from django.http import HttpResponseRedirect
                from django.urls import reverse
                return HttpResponseRedirect(f"{reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})}#message-form")
                
            attachment_obj = GrievanceAttachment.objects.create(
                grievance=grievance,
                file=attachment_file,
                file_name=f"[Student Response] {attachment_file.name}",
                file_size=attachment_file.size,
                file_type=attachment_file.content_type or ext
            )

        full_message = student_response
        if attachment_obj:
            tag = f"\n📎 Attached: {attachment_file.name}"
            full_message = (full_message + tag) if full_message else f"📎 Attached: {attachment_file.name}"
        
        # Create the student response comment
        comment = GrievanceComment.objects.create(
            grievance=grievance,
            user=request.user,
            message=full_message,
            comment_type='comment',
            is_internal=False  # Student responses are always public
        )

        # Automatic SLA Unpause & Status Transition if case was Awaiting Student Reply
        status_changed = False
        if grievance.status == 'pending_student':
            old_status = grievance.status
            if grievance.sla_pause_time:
                pause_duration = timezone.now() - grievance.sla_pause_time
                grievance.accumulated_sla_pause_minutes += int(pause_duration.total_seconds() / 60)
                grievance.sla_pause_time = None
            
            grievance.status = 'pending'
            grievance.save()
            status_changed = True

            # Record formal Status History
            from apps.grievances.models import GrievanceStatusHistory
            GrievanceStatusHistory.objects.create(
                grievance=grievance,
                previous_status=old_status,
                new_status='pending',
                changed_by=request.user,
                reason='Student replied in communication thread; SLA clock resumed.'
            )

            # Record AuditLog
            from apps.grievances.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='update',
                target_model='Grievance',
                target_id=str(grievance.id),
                description=f'Grievance {grievance.grievance_id} auto-resumed to pending upon student reply. SLA unpaused.',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )

            # Add automated system status comment in the thread
            status_comment = GrievanceComment.objects.create(
                grievance=grievance,
                user=None,
                message="Case status automatically returned to Active (Pending): Student replied to inquiry; SLA clock resumed.",
                comment_type='status_update',
                is_internal=False
            )

        # Broadcast live to connected WebSockets via Channel Layer
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                user_name = 'Anonymous Student' if grievance.is_anonymous else (request.user.get_full_name() or request.user.email)
                user_email = 'hidden@anonymous.local' if grievance.is_anonymous else request.user.email
                async_to_sync(channel_layer.group_send)(
                    f'chat_{grievance.id}',
                    {
                        'type': 'chat_message',
                        'id': str(comment.id),
                        'comment_id': str(comment.id),
                        'message': full_message,
                        'user_name': user_name,
                        'user_email': user_email,
                        'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_internal': False,
                        'is_student': True,
                        'status_changed': status_changed,
                        'new_status': grievance.status if status_changed else None,
                        'new_status_display': grievance.get_status_display() if status_changed else None,
                        'attachment_url': attachment_obj.file.url if attachment_obj else None,
                        'attachment_name': attachment_file.name if attachment_obj else None
                    }
                )
                if status_changed:
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{grievance.id}',
                        {
                            'type': 'chat_message',
                            'id': str(status_comment.id),
                            'comment_id': str(status_comment.id),
                            'message': status_comment.message,
                            'user_name': 'System',
                            'user_email': 'system@university.local',
                            'timestamp': status_comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'is_internal': False,
                            'is_student': False
                        }
                    )
        except Exception as ws_err:
            print(f"WebSocket broadcast warning: {ws_err}")

        # Notification delivery to assigned officer or department admin(s)
        from apps.notifications.models import Notification
        recipients = set()
        if grievance.assigned_to and grievance.assigned_to.user:
            recipients.add(grievance.assigned_to.user)
        else:
            from apps.students.models import AdminProfile
            dept_admins = AdminProfile.objects.filter(department=grievance.department, role_level='admin', user__is_active=True).select_related('user')
            for a in dept_admins:
                recipients.add(a.user)
        
        notif_msg = f'Student reply received on #{grievance.grievance_id}: {full_message[:120]}'
        if status_changed:
            notif_msg = f'Student replied on #{grievance.grievance_id}. SLA timer resumed and case returned to active status.'

        from apps.grievances.views import is_user_viewing_grievance
        from django.urls import reverse

        for admin_user in recipients:
            if not is_user_viewing_grievance(admin_user, grievance.id):
                Notification.objects.create(
                    recipient=admin_user,
                    title='Student Response Received' if status_changed else 'New student message',
                    message=notif_msg,
                    notification_type='comment',
                    related_link=reverse('admin_panel:grievance_detail', args=[grievance.id]) + '#admin_response'
                )
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'id': str(comment.id),
                'comment_id': str(comment.id),
                'timestamp': comment.timestamp.strftime('%b %d, %Y %H:%M'),
                'status_changed': status_changed,
                'new_status': grievance.status if status_changed else None,
                'new_status_display': grievance.get_status_display() if status_changed else None,
                'attachment_url': attachment_obj.file.url if attachment_obj else None,
                'attachment_name': attachment_file.name if attachment_obj else None
            })

        # Redirect with fragment to maintain scroll position near message form
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})
        return HttpResponseRedirect(f"{url}#message-form")
        
    except Exception as e:
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', '')
        if is_ajax:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f'Error sending response: {str(e)}')
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})
        return HttpResponseRedirect(f"{url}#message-form")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications_api(request):
    """API endpoint to get student notifications"""
    if not request.user.is_student:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    notifications = get_student_notifications(request.user)
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': str(notification.id),
            'message': notification.message,
            'timestamp': notification.timestamp,
            'admin_name': notification.user.get_full_name(),
            'grievance_id': str(notification.grievance.id),
            'grievance_title': notification.grievance.title,
            'grievance_status': notification.grievance.status,
        })
    
    return Response({
        'notifications': notifications_data,
        'count': len(notifications_data)
    })


@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    if not request.user.is_student:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Get the comment/notification
        comment = get_object_or_404(GrievanceComment, id=notification_id)
        
        # Create or get the read notification record
        read_notification, created = ReadNotification.objects.get_or_create(
            student=request.user,
            comment=comment,
            defaults={'read_at': timezone.now()}
        )
        
        return JsonResponse({
            'success': True,
            'was_new': created  # True if this was the first time marking as read
        })
        
    except GrievanceComment.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def appeal_grievance_view(request, grievance_id):
    """Submit an appeal for a resolved or rejected grievance"""
    if not request.user.is_student:
        messages.error(request, 'Access denied.')
        return redirect('students:dashboard')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('students:grievance_detail', grievance_id=grievance_id)
        
    try:
        from apps.grievances.models import Appeal
        student_profile = request.user.student_profile
        grievance = get_object_or_404(Grievance, id=grievance_id, student=student_profile)
        
        if grievance.status not in ['resolved', 'rejected']:
            messages.error(request, 'You can only appeal resolved or rejected grievances.')
            return redirect('students:grievance_detail', grievance_id=grievance_id)
            
        from apps.admin_panel.models import SystemSettings
        max_appeals = SystemSettings.load().max_reopen_count
        
        appeal_count = grievance.appeals.count()
        if appeal_count >= max_appeals:
            messages.warning(request, f'Maximum appeal limit reached ({max_appeals} appeals allowed). Further appeals cannot be submitted.')
            return redirect('students:grievance_detail', grievance_id=grievance_id)
            
        # Read reason from POST request
        reason = request.POST.get('reason', '').strip() or "Appealed by student with new grounds/evidence."
        
        # Handle optional new supporting document
        evidence_file = request.FILES.get('evidence_file')
        if evidence_file:
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt'}
            import os
            ext = os.path.splitext(evidence_file.name)[1].lower()
            if ext in allowed_extensions and evidence_file.size <= 5 * 1024 * 1024:
                from apps.grievances.models import GrievanceAttachment
                GrievanceAttachment.objects.create(
                    grievance=grievance,
                    file=evidence_file,
                    file_name=f"[Appeal #{appeal_count + 1} Evidence] {evidence_file.name}",
                    file_size=evidence_file.size,
                    file_type=evidence_file.content_type or 'application/octet-stream'
                )
        
        # Create Appeal record
        Appeal.objects.create(
            grievance=grievance,
            student=student_profile,
            reason=reason
        )
        
        # Re-open the grievance
        grievance.is_appealed = True
        grievance.status = 'pending'
        grievance.save()
        
        # Escalate grievance to supervisory authority
        from apps.grievances.tasks import escalate_grievance
        escalated = escalate_grievance(grievance, is_appeal=True, appeal_reason=reason)
        
        # Create a system comment in the grievance thread
        from apps.grievances.models import GrievanceComment
        appeal_comment = GrievanceComment.objects.create(
            grievance=grievance,
            user=request.user,
            message=f"Appeal #{appeal_count + 1} submitted: {reason}",
            comment_type='status_update',
            is_internal=False
        )

        # Broadcast live appeal status update to WebSocket channel layer
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                sender_name = 'Anonymous Student' if grievance.is_anonymous else request.user.get_full_name()
                sender_email = 'hidden@anonymous.local' if grievance.is_anonymous else request.user.email
                async_to_sync(channel_layer.group_send)(
                    f'chat_{grievance.id}',
                    {
                        'type': 'chat_message',
                        'id': str(appeal_comment.id),
                        'comment_id': str(appeal_comment.id),
                        'message': f"Appeal #{appeal_count + 1} submitted: {reason}",
                        'user_name': sender_name,
                        'user_email': sender_email,
                        'timestamp': appeal_comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_internal': False,
                        'is_student': True,
                        'status_changed': True,
                        'new_status': 'pending',
                        'new_status_display': 'Pending (Appealed)'
                    }
                )
        except Exception as ws_err:
            print(f"WebSocket broadcast error on appeal: {ws_err}")

        # Send in-app notifications and email alerts to all relevant admins & officers
        try:
            from apps.notifications.models import Notification
            from apps.authentication.models import User, AdminProfile
            from django.urls import reverse

            staff_recipients = set()

            # 1. Assigned officer
            if grievance.assigned_to and grievance.assigned_to.user and grievance.assigned_to.user.is_active:
                staff_recipients.add(grievance.assigned_to.user)

            # 2. Department Admins / HODs for this department
            if grievance.department:
                dept_admins = AdminProfile.objects.filter(
                    department__iexact=grievance.department.strip(),
                    role_level='admin',
                    user__is_active=True
                ).select_related('user')
                for da in dept_admins:
                    if da.user and da.user.is_active:
                        staff_recipients.add(da.user)

            # 3. Superadmins (Appellate Authority)
            for sa in User.objects.filter(is_superadmin=True, is_active=True):
                staff_recipients.add(sa)

            admin_link = reverse('admin_panel:grievance_detail', kwargs={'grievance_id': grievance.id})
            appeal_title = f"Appeal #{appeal_count + 1} Filed: #{grievance.grievance_id}"
            appeal_msg = f'Student filed Appeal #{appeal_count + 1} on grievance #{grievance.grievance_id} ("{grievance.title}"). Grounds: {reason[:140]}'

            # Create in-app notifications for each staff member
            for staff_user in staff_recipients:
                Notification.objects.create(
                    recipient=staff_user,
                    title=appeal_title,
                    message=appeal_msg,
                    notification_type='appeal',
                    related_link=admin_link
                )

            # Send email notifications to staff members
            from django.core.mail import send_mail
            from django.conf import settings
            staff_emails = [u.email for u in staff_recipients if u.email]
            if staff_emails:
                email_subj = f"URGENT: Appeal Filed for Grievance #{grievance.grievance_id}"
                email_body = (
                    f"A student has filed Appeal #{appeal_count + 1} on grievance #{grievance.grievance_id}.\n\n"
                    f"Title: {grievance.title}\n"
                    f"Department: {grievance.department or 'N/A'}\n"
                    f"Priority: {grievance.get_priority_display()}\n\n"
                    f"Appeal Reason / Grounds:\n{reason}\n\n"
                    f"The grievance has been reopened and escalated for supervisory review.\n"
                    f"Please log in to the admin panel to examine evidence and adjudicate.\n\n"
                    f"Student Grievance Management System"
                )
                send_mail(
                    email_subj,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    staff_emails,
                    fail_silently=True
                )
        except Exception as notif_err:
            print(f"Error dispatching appeal notifications to admins: {notif_err}")

        messages.success(
            request, 
            'Your appeal has been submitted successfully. The grievance has been re-opened and escalated to the supervisory authority for review.'
        )
        return redirect('students:grievance_detail', grievance_id=grievance_id)
        
    except Exception as e:
        messages.error(request, f'Error submitting appeal: {str(e)}')
        return redirect('students:grievance_detail', grievance_id=grievance_id)
