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
        return Response({
            'id': grievance.id,
            'title': grievance.title,
            'description': grievance.description,
            'status': grievance.status,
            'student': grievance.student.student_id,
            'category': grievance.category.name,
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
        
        context = {
            'grievance': grievance,
            'user_role': user.role,
            'can_manage_categories': can_manage_categories(user),
        }
        
        return render(request, 'admin_panel/grievance_detail.html', context)
        
    except Grievance.DoesNotExist:
        messages.error(request, 'Grievance not found')
        return redirect('admin_panel:grievance_list')



@login_required
@require_http_methods(["PATCH"])
def update_grievance_status(request, grievance_id):
    """Update grievance status"""
    if not request.user.is_admin_or_officer:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        grievance = get_object_or_404(Grievance, id=grievance_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status in ['pending', 'resolved', 'rejected']:
            grievance.status = new_status
            if new_status in ['resolved', 'rejected']:
                grievance.resolved_at = timezone.now()
                grievance.resolved_by = request.user
            grievance.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='update',
                target_model='Grievance',
                target_id=str(grievance.id),
                description=f'Changed grievance {grievance.grievance_id} status to {new_status}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            return JsonResponse({'success': True, 'status': new_status})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
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
        admin_response = request.POST.get('admin_response', '').strip()
        is_internal = request.POST.get('is_internal', 'false').lower() == 'true'
        
        if not admin_response:
            return JsonResponse({'success': False, 'error': 'Response cannot be empty'}, status=400)
        
        # Create the comment
        comment = GrievanceComment.objects.create(
            grievance=grievance,
            user=request.user,
            message=admin_response,
            comment_type='internal_note' if is_internal else 'comment',
            is_internal=is_internal
        )

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
                    message=f'An admin replied on grievance {grievance.grievance_id}: {admin_response[:120]}',
                    notification_type='comment',
                    related_link=reverse('students:grievance_detail', kwargs={'grievance_id': grievance.id}) + '#message-form'
                )
        
        return JsonResponse({
            'success': True, 
            'message': f'{"Internal note" if is_internal else "Response"} added successfully',
            'comment_id': str(comment.id),
            'timestamp': comment.timestamp.strftime('%b %d, %Y %H:%M')
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
        
        # Validate that all IDs are valid UUIDs and grievances exist
        grievances_to_delete = Grievance.objects.filter(id__in=grievance_ids)
        
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

