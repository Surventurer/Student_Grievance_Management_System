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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_logs(request):
    """Get audit logs API - Superadmin only"""
    if not can_view_audit_logs(request.user):
        return Response({'error': 'Access denied - Superadmin privileges required'}, status=status.HTTP_403_FORBIDDEN)
    
    logs = AuditLog.objects.all().order_by('-timestamp')[:50]
    
    return Response([
        {
            'id': log.id,
            'user': log.user.email,
            'action': log.action,
            'description': log.description,
            'timestamp': log.timestamp,
        }
        for log in logs
    ])



@login_required
def audit_logs_view(request):
    """Enhanced view for audit logs with filtering - Superadmin only"""
    if not can_view_audit_logs(request.user):
        messages.error(request, 'Access denied - Superadmin privileges required for audit logs')
        return redirect('admin_panel:dashboard')
    
    # Get all audit logs
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    
    # Filtering
    action_filter = request.GET.get('action')
    user_filter = request.GET.get('user')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('search', '').strip()
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if user_filter:
        logs = logs.filter(user__email__icontains=user_filter)
    
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__lte=date_to_obj)
        except ValueError:
            pass
    
    if search_query:
        logs = logs.filter(
            Q(description__icontains=search_query) |
            Q(target_model__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Get unique action types for filter dropdown
    action_types = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
    
    # Get recent admin users for filter dropdown
    admin_users = AuditLog.objects.select_related('user').values(
        'user__email'
    ).distinct().order_by('user__email')[:20]
    
    # Pagination or Print all
    is_print = request.GET.get('print') == 'true'
    if is_print:
        audit_logs = logs  # Return all filtered logs without pagination
    else:
        paginator = Paginator(logs, 25)
        page_number = request.GET.get('page')
        audit_logs = paginator.get_page(page_number)
    
    # Statistics
    total_logs = AuditLog.objects.count()
    today_logs = AuditLog.objects.filter(timestamp__date=timezone.now().date()).count()
    
    # Action statistics
    action_stats = AuditLog.objects.values('action').annotate(
        count=Count('action')
    ).order_by('-count')[:5]
    
    context = {
        'audit_logs': audit_logs,
        'action_types': action_types,
        'admin_users': admin_users,
        'total_logs': total_logs,
        'today_logs': today_logs,
        'action_stats': action_stats,
        'filters': {
            'action': action_filter,
            'user': user_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search_query,
        }
    }
    
    return render(request, 'admin_panel/audit_logs.html', context)

