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
    GrievanceAttachment, GrievanceStatusHistory, GrievanceAssignmentHistory,
    Appeal
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
def grievance_list(request):
    """Grievance list view with department-based filtering"""
    user = request.user
    
    # Get accessible grievances based on user's department assignment
    accessible_grievances = user.get_accessible_grievances().select_related('student__user', 'category')
    
    # Order grievances
    grievances = accessible_grievances.order_by('-submitted_at')
    
    # Get categories that are relevant to the user's accessible grievances
    if user.is_superadmin:
        categories = Category.objects.all()
    else:
        # Only show categories that have grievances the user can access
        accessible_category_ids = accessible_grievances.values_list('category_id', flat=True).distinct()
        categories = Category.objects.filter(id__in=accessible_category_ids)
    
    context = {
        'grievances': grievances,
        'categories': categories,
        'user_role': user.role,
        'assigned_department': user.assigned_department,
        'department_name': user.department_name,
        'can_manage_categories': can_manage_categories(user),
    }
    
    return render(request, 'admin_panel/grievance_list.html', context)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_grievances(request):
    """Manage grievances API"""
    if not request.user.is_admin_or_officer:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    grievances = Grievance.objects.filter(is_archived=False).order_by('-submitted_at')
    
    return Response([
        {
            'id': g.id,
            'title': g.title,
            'status': g.status,
            'student': g.student.student_id,
            'category': g.category.name,
            'submitted_at': g.submitted_at,
        }
        for g in grievances
    ])



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_detail(request, grievance_id):
    """Get grievance details"""
    if not request.user.is_admin_or_officer:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        grievance = Grievance.objects.get(id=grievance_id)
        is_anon = getattr(grievance, 'is_anonymous', False)
        student_identifier = 'Anonymous' if is_anon else (grievance.student.student_id if grievance.student else None)
        return Response({
            'id': grievance.id,
            'title': grievance.title,
            'description': grievance.description,
            'status': grievance.status,
            'student': student_identifier,
            'is_anonymous': is_anon,
            'category': grievance.category.name if grievance.category else None,
            'submitted_at': grievance.submitted_at,
            'assigned_to': grievance.assigned_to.user.get_full_name() if grievance.assigned_to else None,
        })
    except Grievance.DoesNotExist:
        return Response({'error': 'Grievance not found'}, status=status.HTTP_404_NOT_FOUND)



@login_required
@department_access_required
def grievance_detail_view(request, grievance_id):
    """Detailed view of a specific grievance with role-based access control"""
    user = request.user
    
    try:
        grievance = get_object_or_404(Grievance, id=grievance_id)
        
        # Check if user can access this grievance
        from apps.admin_panel.permissions import can_access_grievance
        if not can_access_grievance(user, grievance):
            messages.error(request, 'Access denied - You can only view grievances from your department or assigned to you')
            return redirect('admin_panel:grievance_list')
        
        # Fetch appeals and appeal evidence attachments
        appeals = grievance.appeals.select_related('student__user', 'reviewed_by__user').order_by('-created_at')
        appeal_attachments = grievance.attachments.filter(file_name__startswith='[Appeal #')
        
        context = {
            'grievance': grievance,
            'appeals': appeals,
            'appeal_attachments': appeal_attachments,
            'user_role': user.role,
            'can_manage_categories': can_manage_categories(user),
        }
        
        return render(request, 'admin_panel/grievance_detail.html', context)
        
    except Grievance.DoesNotExist:
        messages.error(request, 'Grievance not found')
        return redirect('admin_panel:grievance_list')


@login_required
@department_access_required
def process_grievance_appeal(request, grievance_id):
    """Process decision on a student grievance appeal (Accept & Reopen or Uphold Resolution)"""
    if not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied.')
        return redirect('admin_panel:grievance_list')
    
    grievance = get_object_or_404(Grievance, id=grievance_id)
    
    from apps.admin_panel.permissions import can_access_grievance
    if not can_access_grievance(request.user, grievance):
        messages.error(request, 'Access denied - You can only view grievances from your department or assigned to you.')
        return redirect('admin_panel:grievance_list')
        
    if request.method == 'POST':
        action = request.POST.get('action')  # 'accept' or 'reject'
        decision_notes = request.POST.get('decision_notes', '').strip()
        appeal_id = request.POST.get('appeal_id')
        
        appeal = None
        if appeal_id:
            appeal = Appeal.objects.filter(id=appeal_id, grievance=grievance).first()
        if not appeal:
            appeal = grievance.appeals.filter(status='pending').order_by('-created_at').first()
            
        admin_prof = getattr(request.user, 'admin_profile', None)
        
        if action == 'accept':
            # Reopen grievance for supervisory re-hearing
            grievance.status = 'in_progress'
            grievance.is_appealed = False
            grievance.resolved_at = None
            grievance.resolution_notes = None
            grievance.save()
            
            if appeal:
                appeal.status = 'accepted'
                appeal.review_notes = decision_notes or 'Appeal accepted for institutional re-examination.'
                appeal.reviewed_by = admin_prof
                appeal.save()
                
            # Create AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='update',
                target_model='Grievance',
                target_id=str(grievance.id),
                description=f'Appeal accepted by {request.user.get_full_name()} for grievance {grievance.grievance_id}. Case reopened for re-investigation.',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            # Create comment in thread
            appeal_comment = GrievanceComment.objects.create(
                grievance=grievance,
                user=request.user,
                message=f"Appeal Accepted: Case reopened for supervisory re-hearing.\nOfficer Remarks: {decision_notes or 'Reopening for further inquiry.'}",
                comment_type='status_update',
                is_internal=False
            )

            # Broadcast live status update to WebSocket channel layer
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{grievance.id}',
                        {
                            'type': 'chat_message',
                            'id': str(appeal_comment.id),
                            'comment_id': str(appeal_comment.id),
                            'message': appeal_comment.message,
                            'user_name': request.user.get_full_name() or request.user.email,
                            'user_email': request.user.email,
                            'timestamp': appeal_comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'is_internal': False,
                            'is_student': False,
                            'status_changed': True,
                            'new_status': 'in_progress',
                            'new_status_display': 'In Progress'
                        }
                    )
            except Exception as ws_err:
                print(f"WebSocket broadcast error on appeal acceptance: {ws_err}")
            
            # Notify student
            if grievance.student and grievance.student.user:
                from django.urls import reverse
                Notification.objects.create(
                    recipient=grievance.student.user,
                    title='Appeal Accepted - Case Reopened',
                    message=f'Your appeal for grievance #{grievance.grievance_id} has been accepted and reopened for supervisory re-examination.',
                    notification_type='status_update',
                    related_link=reverse('students:grievance_detail', kwargs={'grievance_id': grievance.id})
                )
                
            messages.success(request, 'Appeal accepted successfully. Grievance reopened for supervisory review.')
            
        elif action == 'reject':
            if appeal:
                appeal.status = 'rejected'
                appeal.review_notes = decision_notes or 'Appeal reviewed and prior resolution upheld.'
                appeal.reviewed_by = admin_prof
                appeal.save()
                
            grievance.is_appealed = False
            grievance.status = 'resolved'
            grievance.save()
            
            # Create AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='update',
                target_model='Grievance',
                target_id=str(grievance.id),
                description=f'Appeal rejected/resolution upheld by {request.user.get_full_name()} for grievance {grievance.grievance_id}.',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            # Create comment
            reject_comment = GrievanceComment.objects.create(
                grievance=grievance,
                user=request.user,
                message=f"Appeal Reviewed: Prior resolution upheld.\nSupervisory Justification: {decision_notes or 'After review, the existing resolution stands.'}",
                comment_type='status_update',
                is_internal=False
            )

            # Broadcast live status update to WebSocket channel layer
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{grievance.id}',
                        {
                            'type': 'chat_message',
                            'id': str(reject_comment.id),
                            'comment_id': str(reject_comment.id),
                            'message': reject_comment.message,
                            'user_name': request.user.get_full_name() or request.user.email,
                            'user_email': request.user.email,
                            'timestamp': reject_comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'is_internal': False,
                            'is_student': False,
                            'status_changed': True,
                            'new_status': 'resolved',
                            'new_status_display': 'Resolved'
                        }
                    )
            except Exception as ws_err:
                print(f"WebSocket broadcast error on appeal rejection: {ws_err}")
            
            # Notify student
            if grievance.student and grievance.student.user:
                from django.urls import reverse
                Notification.objects.create(
                    recipient=grievance.student.user,
                    title='Appeal Decision - Resolution Upheld',
                    message=f'Your appeal for grievance #{grievance.grievance_id} was reviewed. The existing resolution has been upheld.',
                    notification_type='status_update',
                    related_link=reverse('students:grievance_detail', kwargs={'grievance_id': grievance.id})
                )
                
            messages.info(request, 'Appeal decision recorded. Original resolution upheld.')
            
    return redirect('admin_panel:grievance_detail', grievance_id=grievance.id)



@login_required
@require_http_methods(["PATCH", "POST"])
def update_grievance_status(request, grievance_id):
    """Update grievance status"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        grievance = get_object_or_404(Grievance, id=grievance_id)
        
        from apps.admin_panel.permissions import can_access_grievance
        if not can_access_grievance(request.user, grievance):
            return JsonResponse({'success': False, 'error': 'Access denied: You cannot modify this grievance'}, status=403)
            
        data = {}
        if request.body:
            try:
                data = json.loads(request.body)
            except Exception:
                pass
        
        new_status = data.get('status') or request.POST.get('status')
        resolution_notes = (data.get('resolution_notes') or request.POST.get('resolution_notes') or '').strip()
        
        if new_status in ['pending', 'pending_student', 'resolved', 'rejected']:
            old_status = grievance.status
            
            # If resolution_notes is empty, assign standard professional remarks
            if not resolution_notes:
                if new_status == 'resolved':
                    resolution_notes = 'Grievance marked as resolved by staff.'
                elif new_status == 'pending_student':
                    resolution_notes = 'Status updated to awaiting student reply. SLA clock paused.'
                elif new_status == 'rejected':
                    resolution_notes = 'Grievance rejected upon administrative review.'
                elif new_status == 'pending':
                    resolution_notes = 'Case resumed / reopened for active inquiry.'

            # Handle SLA pause tracking
            if new_status == 'pending_student' and old_status != 'pending_student':
                grievance.sla_pause_time = timezone.now()
            elif old_status == 'pending_student' and new_status != 'pending_student':
                if grievance.sla_pause_time:
                    pause_duration = timezone.now() - grievance.sla_pause_time
                    grievance.accumulated_sla_pause_minutes += int(pause_duration.total_seconds() / 60)
                    grievance.sla_pause_time = None
                    
            grievance.status = new_status
            if new_status in ['resolved', 'rejected']:
                grievance.actual_resolution_date = timezone.now()
            elif new_status == 'pending':
                grievance.actual_resolution_date = None
            grievance.save()

            # Record formal Status History
            from apps.grievances.models import GrievanceStatusHistory
            history_reason = resolution_notes or f"Status changed from {old_status} to {new_status}"
            GrievanceStatusHistory.objects.create(
                grievance=grievance,
                previous_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                reason=history_reason
            )

            # Post an official status_update comment
            prefix = "Official Resolution / Action Taken" if new_status == 'resolved' else (
                "Reason for Rejection" if new_status == 'rejected' else (
                    "Information Requested from Student" if new_status == 'pending_student' else "Status Update"
                )
            )
            comment_text = f"{prefix}: {resolution_notes}" if resolution_notes else f"Status changed to {grievance.get_status_display()}."
            status_comment = GrievanceComment.objects.create(
                grievance=grievance,
                user=request.user,
                message=comment_text,
                comment_type='status_update',
                is_internal=False
            )

            # Broadcast live status update to WebSocket channel layer
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{grievance.id}',
                        {
                            'type': 'chat_message',
                            'id': str(status_comment.id),
                            'comment_id': str(status_comment.id),
                            'message': comment_text,
                            'user_name': request.user.get_full_name() or request.user.email,
                            'user_email': request.user.email,
                            'timestamp': status_comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'is_internal': False,
                            'is_student': False,
                            'status_changed': True,
                            'new_status': new_status,
                            'new_status_display': grievance.get_status_display()
                        }
                    )
            except Exception as ws_err:
                print(f"WebSocket broadcast error: {ws_err}")

            # Notify student of status change
            if grievance.student and grievance.student.user:
                from django.urls import reverse
                from apps.notifications.models import Notification

                if new_status == 'pending':
                    notif_title = f'Grievance Reopened: #{grievance.grievance_id}'
                    notif_msg = f'Your grievance #{grievance.grievance_id} has been reopened by administration for active inquiry.'
                elif new_status == 'resolved':
                    notif_title = f'Grievance Resolved: #{grievance.grievance_id}'
                    notif_msg = f'Your grievance #{grievance.grievance_id} has been marked as Resolved by administration.'
                elif new_status == 'rejected':
                    notif_title = f'Grievance Rejected: #{grievance.grievance_id}'
                    notif_msg = f'Your grievance #{grievance.grievance_id} has been marked as Rejected upon review.'
                elif new_status == 'pending_student':
                    notif_title = f'Action Required: Grievance #{grievance.grievance_id}'
                    notif_msg = f'Administration requested additional information on grievance #{grievance.grievance_id}. SLA clock is paused.'
                else:
                    notif_title = f'Grievance {grievance.get_status_display()}: #{grievance.grievance_id}'
                    notif_msg = f'Your grievance #{grievance.grievance_id} status updated to {grievance.get_status_display()}.'

                if resolution_notes:
                    notif_msg += f' Remarks: {resolution_notes[:140]}'

                Notification.objects.create(
                    recipient=grievance.student.user,
                    title=notif_title,
                    message=notif_msg,
                    notification_type='status_update',
                    related_link=reverse('students:grievance_detail', kwargs={'grievance_id': grievance.id})
                )

                # Send email notification to student
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    if grievance.student.user.email:
                        email_subj = f"UPDATE: Grievance #{grievance.grievance_id} - {notif_title}"
                        email_body = (
                            f"Dear {grievance.student.user.get_full_name() or 'Student'},\n\n"
                            f"{notif_msg}\n\n"
                            f"Grievance: {grievance.title}\n"
                            f"Status: {grievance.get_status_display()}\n\n"
                            f"You can log in to view the complete thread and submit replies.\n\n"
                            f"Student Grievance Management System"
                        )
                        send_mail(
                            email_subj,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            [grievance.student.user.email],
                            fail_silently=True
                        )
                except Exception as email_err:
                    print(f"Status update email error: {email_err}")
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='update',
                target_model='Grievance',
                target_id=str(grievance.id),
                description=f'Changed grievance {grievance.grievance_id} status from {old_status} to {new_status}. Remarks: {resolution_notes[:100] if resolution_notes else "None"}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            return JsonResponse({
                'success': True, 
                'status': new_status,
                'status_display': grievance.get_status_display()
            })
        else:
            return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'}, status=400)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def add_admin_response(request, grievance_id):
    """Add admin response to a grievance"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST requests allowed'}, status=405)
    
    try:
        grievance = get_object_or_404(Grievance, id=grievance_id)
        
        # IDOR Protection: Enforce department access boundary
        from apps.admin_panel.permissions import can_access_grievance
        if not can_access_grievance(request.user, grievance):
            return JsonResponse({'success': False, 'error': 'Access denied: You cannot view or comment on this grievance'}, status=403)
            
        # Lock communication if grievance is resolved or rejected
        if grievance.status in ['resolved', 'rejected']:
            status_text = 'resolved' if grievance.status == 'resolved' else 'rejected'
            return JsonResponse({
                'success': False, 
                'error': f'This grievance is {status_text}. The communication thread is closed until an appeal is processed or the case is reopened.'
            }, status=400)

        admin_response = request.POST.get('admin_response', '').strip()
        is_internal = request.POST.get('is_internal', 'false').lower() == 'true'
        
        if not admin_response and not request.FILES.get('attachment'):
            return JsonResponse({'success': False, 'error': 'Response or attachment is required'}, status=400)
            
        attachment_obj = None
        attachment_file = request.FILES.get('attachment')
        if attachment_file:
            import os
            from apps.grievances.models import GrievanceAttachment
            ext = os.path.splitext(attachment_file.name)[1].lower().lstrip('.')
            if ext not in GrievanceAttachment.ALLOWED_EXTENSIONS:
                return JsonResponse({'success': False, 'error': f'Invalid file type. Allowed: {", ".join(GrievanceAttachment.ALLOWED_EXTENSIONS)}'}, status=400)
            if attachment_file.size > 10 * 1024 * 1024:
                return JsonResponse({'success': False, 'error': 'Attachment exceeds maximum size of 10MB'}, status=400)
                
            attachment_prefix = "[Internal Note]" if is_internal else "[Staff Reply]"
            attachment_obj = GrievanceAttachment.objects.create(
                grievance=grievance,
                file=attachment_file,
                file_name=f"{attachment_prefix} {attachment_file.name}",
                file_size=attachment_file.size,
                file_type=attachment_file.content_type or ext
            )
        
        # Format comment message
        full_message = admin_response
        if attachment_obj:
            attachment_tag = f"\n📎 Attached: {attachment_file.name}"
            full_message = (full_message + attachment_tag) if full_message else f"📎 Attached: {attachment_file.name}"

        # Create single comment record
        comment = GrievanceComment.objects.create(
            grievance=grievance,
            user=request.user,
            message=full_message,
            comment_type='internal_note' if is_internal else 'comment',
            is_internal=is_internal
        )

        # Broadcast live to connected WebSockets via Channel Layer
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{grievance.id}',
                    {
                        'type': 'chat_message',
                        'id': str(comment.id),
                        'comment_id': str(comment.id),
                        'message': full_message,
                        'user_name': request.user.get_full_name() or request.user.email,
                        'user_email': request.user.email,
                        'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_internal': is_internal,
                        'is_student': False,
                        'attachment_url': attachment_obj.file.url if attachment_obj else None,
                        'attachment_name': attachment_file.name if attachment_obj else None
                    }
                )
        except Exception as ws_err:
            print(f"WebSocket broadcast warning: {ws_err}")

        # Only create notification if student is not currently viewing the grievance
        if not is_internal and grievance.student and grievance.student.user:
            from django.core.cache import cache
            from apps.grievances.views import is_user_viewing_grievance
            student_user = grievance.student.user
            
            # Check if student is viewing this grievance
            if not is_user_viewing_grievance(student_user, grievance.id):
                from django.urls import reverse
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=student_user,
                    title='New grievance update',
                    message=f'An admin replied on grievance {grievance.grievance_id}: {full_message[:120]}',
                    notification_type='comment',
                    related_link=reverse('students:grievance_detail', kwargs={'grievance_id': grievance.id}) + '#message-form'
                )
        
        return JsonResponse({
            'success': True, 
            'message': f'{"Internal note" if is_internal else "Response"} added successfully',
            'id': str(comment.id),
            'comment_id': str(comment.id),
            'timestamp': comment.timestamp.strftime('%b %d, %Y %H:%M'),
            'attachment_url': attachment_obj.file.url if attachment_obj else None,
            'attachment_name': attachment_file.name if attachment_obj else None
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def grievance_list_advanced(request):
    """Advanced grievance list with filtering and search"""
    if not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    # Get accessible grievances based on user's role and department
    accessible_grievances = request.user.get_accessible_grievances()
    grievances = accessible_grievances.select_related('student__user', 'category').order_by('-submitted_at')
    
    # Filtering
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status_filter:
        grievances = grievances.filter(status=status_filter)
    
    if category_filter:
        grievances = grievances.filter(category_id=category_filter)
    
    if search_query:
        # Enhanced search - search by ID, Title, or Category as shown in the image
        # Include search by grievance_id property (GRV-XXXXXXXX format)
        search_q = Q(title__icontains=search_query) | \
                   Q(description__icontains=search_query) | \
                   Q(category__name__icontains=search_query) | \
                   Q(student__name__icontains=search_query) | \
                   Q(student__student_id__icontains=search_query) | \
                   Q(student__user__email__icontains=search_query)
        
        # If search query looks like a grievance ID (contains GRV or is alphanumeric)
        if 'GRV' in search_query.upper() or search_query.replace('-', '').isalnum():
            # Extract the UUID part from GRV-XXXXXXXX format
            clean_query = search_query.upper().replace('GRV-', '').replace('GRV', '')
            search_q |= Q(id__icontains=clean_query)
        
        grievances = grievances.filter(search_q)
    
    if date_from:
        grievances = grievances.filter(submitted_at__date__gte=date_from)
    
    if date_to:
        grievances = grievances.filter(submitted_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(grievances, 20)
    page_number = request.GET.get('page')
    grievances_page = paginator.get_page(page_number)
    
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    context = {
        'grievances': grievances_page,
        'categories': categories,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'admin_panel/grievance_list.html', context)



@login_required
def grievance_stats_api(request):
    """API endpoint to get grievance statistics for the dashboard"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        accessible_grievances = request.user.get_accessible_grievances()
        stats = {
            'total': accessible_grievances.count(),
            'pending': accessible_grievances.filter(status='pending').count(),
            'resolved': accessible_grievances.filter(status='resolved').count(),
            'rejected': accessible_grievances.filter(status='rejected').count(),
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_http_methods(["POST"])
def bulk_delete_grievances(request):
    """API endpoint to bulk delete grievances"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied - Admin privileges required'}, status=403)
    
    try:
        data = json.loads(request.body)
        grievance_ids = data.get('grievance_ids', [])
        
        if not grievance_ids:
            return JsonResponse({'error': 'No grievance IDs provided'}, status=400)
        
        # Validate that all IDs are valid UUIDs and grievances exist within user's accessible scope
        accessible_grievances = request.user.get_accessible_grievances()
        grievances_to_delete = accessible_grievances.filter(id__in=grievance_ids)
        
        if not grievances_to_delete.exists():
            return JsonResponse({'error': 'No valid grievances found'}, status=404)
        
        # Log the deletion for audit trail
        deleted_grievance_info = []
        for grievance in grievances_to_delete:
            deleted_grievance_info.append({
                'id': str(grievance.id),
                'grievance_id': grievance.grievance_id,
                'title': grievance.title,
                'student_email': grievance.student.user.email if grievance.student else 'Unknown',
                'status': grievance.status,
                'submitted_at': grievance.submitted_at.isoformat()
            })
            
            # Create audit log entry
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action='delete',
                    target_model='Grievance',
                    target_id=str(grievance.id),
                    description=f'Bulk deleted grievance: {grievance.grievance_id} - {grievance.title}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
            except Exception as e:
                print(f"Error creating audit log: {e}")
        
        # Perform the bulk deletion
        deleted_count = grievances_to_delete.count()
        grievances_to_delete.delete()
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'deleted_grievances': deleted_grievance_info,
            'message': f'Successfully deleted {deleted_count} grievance(s)'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error in bulk_delete_grievances: {e}")
        return JsonResponse({'error': 'An error occurred while deleting grievances'}, status=500)


@require_http_methods(["POST"])
def bulk_update_grievances_status(request):
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
        
    try:
        data = json.loads(request.body)
        grievance_ids = data.get('grievance_ids', [])
        new_status = data.get('status')
        
        if not grievance_ids or not new_status:
            return JsonResponse({'error': 'Grievance IDs and status are required'}, status=400)
            
        if new_status not in ['pending', 'pending_student', 'resolved', 'rejected']:
            return JsonResponse({'error': 'Invalid status'}, status=400)
            
        # Get accessible grievances
        accessible_grievances = request.user.get_accessible_grievances()
        grievances_to_update = accessible_grievances.filter(id__in=grievance_ids)
        
        updated_count = 0
        with transaction.atomic():
            for grievance in grievances_to_update:
                old_status = grievance.status
                if new_status == 'pending_student' and old_status != 'pending_student':
                    grievance.sla_pause_time = timezone.now()
                elif old_status == 'pending_student' and new_status != 'pending_student':
                    if grievance.sla_pause_time:
                        pause_duration = timezone.now() - grievance.sla_pause_time
                        grievance.accumulated_sla_pause_minutes += int(pause_duration.total_seconds() / 60)
                        grievance.sla_pause_time = None
                        
                grievance.status = new_status
                if new_status in ['resolved', 'rejected']:
                    grievance.actual_resolution_date = timezone.now()
                grievance.save()
                
                AuditLog.objects.create(
                    user=request.user,
                    action='update',
                    target_model='Grievance',
                    target_id=str(grievance.id),
                    description=f'Bulk changed status to {new_status}',
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                updated_count += 1
                
        return JsonResponse({'success': True, 'updated_count': updated_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def bulk_reassign_grievances(request):
    if not request.user.is_admin_or_officer:
        return JsonResponse({'error': 'Access denied'}, status=403)
        
    try:
        data = json.loads(request.body)
        grievance_ids = data.get('grievance_ids', [])
        assignee_id = data.get('assignee_id')
        
        if not grievance_ids or not assignee_id:
            return JsonResponse({'error': 'Grievance IDs and Assignee ID are required'}, status=400)
            
        assignee = get_object_or_404(AdminProfile, id=assignee_id)
        
        if not request.user.is_superadmin and request.user.department_name and request.user.department_name.lower() != (assignee.department or '').lower():
            return JsonResponse({'error': 'Access denied: Assignee belongs to a different department'}, status=403)
        
        accessible_grievances = request.user.get_accessible_grievances()
        grievances_to_update = accessible_grievances.filter(id__in=grievance_ids)
        
        updated_count = 0
        with transaction.atomic():
            for grievance in grievances_to_update:
                old_assignee = grievance.assigned_to
                grievance.assigned_to = assignee
                grievance.save()
                
                GrievanceAssignmentHistory.objects.create(
                    grievance=grievance,
                    previous_assignee=old_assignee,
                    new_assignee=assignee,
                    assigned_by=request.user,
                    reason="Bulk reassignment"
                )
                
                AuditLog.objects.create(
                    user=request.user,
                    action='assign',
                    target_model='Grievance',
                    target_id=str(grievance.id),
                    description=f'Bulk reassigned to {assignee}',
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                updated_count += 1
                
        return JsonResponse({'success': True, 'updated_count': updated_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
