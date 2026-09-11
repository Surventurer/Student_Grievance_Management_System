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
@staff_member_required
def download_grievances_csv(request):
    """Download grievances report as CSV"""
    import csv
    from django.http import HttpResponse
    
    # Get filters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    
    # Base queryset
    grievances = Grievance.objects.select_related(
        'student', 'category', 'assigned_to'
    ).order_by('-submitted_at')
    
    # Apply filters
    if from_date and to_date:
        grievances = grievances.filter(
            submitted_at__date__gte=from_date,
            submitted_at__date__lte=to_date
        )
    
    if status_filter:
        grievances = grievances.filter(status=status_filter)
    
    if category_filter:
        grievances = grievances.filter(category_id=category_filter)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f'grievances_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # CSV Headers
    writer.writerow([
        'Grievance ID',
        'Student ID',
        'Student Name',
        'Student Email',
        'School',
        'Department',
        'Category',
        'Title',
        'Description',
        'Status',
        'Priority',
        'Assigned To',
        'Created Date',
        'Updated Date',
        'Resolution Date',
        'Days to Resolve'
    ])
    
    # CSV Data
    for grievance in grievances:
        days_to_resolve = ''
        if grievance.status == 'resolved' and grievance.updated_at:
            days_diff = (grievance.updated_at - grievance.submitted_at).days
            days_to_resolve = str(days_diff)
        
        writer.writerow([
            f'GRV-{grievance.id}',
            grievance.student.student_id if grievance.student else '',
            grievance.student.name if grievance.student else '',
            grievance.student.user.email if grievance.student and grievance.student.user else '',
            grievance.student.school if grievance.student else '',
            grievance.student.department if grievance.student else '',
            grievance.category.name if grievance.category else '',
            grievance.title,
            grievance.description[:200] + '...' if len(grievance.description) > 200 else grievance.description,
            grievance.get_status_display(),
            grievance.get_priority_display() if grievance.priority else '',
            grievance.assigned_to.user.get_full_name() if grievance.assigned_to else 'Unassigned',
            grievance.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
            grievance.updated_at.strftime('%Y-%m-%d %H:%M:%S') if grievance.updated_at else '',
            grievance.updated_at.strftime('%Y-%m-%d') if grievance.status == 'resolved' and grievance.updated_at else '',
            days_to_resolve
        ])
    
    return response



@login_required
@staff_member_required
def download_monthly_stats_csv(request):
    """Download monthly statistics as CSV"""
    import csv
    from django.http import HttpResponse
    
    year = request.GET.get('year', timezone.now().year)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f'monthly_grievances_stats_{year}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # CSV Headers
    writer.writerow([
        'Month',
        'Total Grievances',
        'Resolved',
        'Pending',
        'Rejected',
        'Resolution Rate (%)'
    ])
    
    # Monthly data
    for month_num in range(1, 13):
        month_grievances = Grievance.objects.filter(
            submitted_at__year=year,
            submitted_at__month=month_num
        )
        
        total = month_grievances.count()
        resolved = month_grievances.filter(status='resolved').count()
        pending = month_grievances.filter(status='pending').count()
        rejected = month_grievances.filter(status='rejected').count()
        
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        
        month_name = datetime(int(year), month_num, 1).strftime('%B %Y')
        
        writer.writerow([
            month_name,
            total,
            resolved,
            pending,
            rejected,
            f'{resolution_rate:.1f}'
        ])
    
    return response



@login_required
@staff_member_required
def download_category_stats_csv(request):
    """Download category-wise statistics as CSV"""
    import csv
    from django.http import HttpResponse
    
    # Get filters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Base queryset
    grievances = Grievance.objects.all()
    
    if from_date and to_date:
        grievances = grievances.filter(
            submitted_at__date__gte=from_date,
            submitted_at__date__lte=to_date
        )
    
    # Category statistics
    category_stats = grievances.values('category__name').annotate(
        total=Count('id'),
        resolved=Count('id', filter=Q(status='resolved')),
        pending=Count('id', filter=Q(status='pending')),
        rejected=Count('id', filter=Q(status='rejected'))
    ).order_by('-total')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f'category_stats_{timezone.now().strftime("%Y%m%d")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # CSV Headers
    writer.writerow([
        'Category',
        'Total Grievances',
        'Resolved',
        'Pending',
        'Rejected',
        'Resolution Rate (%)'
    ])
    
    # Category data
    for stat in category_stats:
        total = stat['total']
        resolved = stat['resolved']
        pending = stat['pending']
        rejected = stat['rejected']
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        
        writer.writerow([
            stat['category__name'] or 'Uncategorized',
            total,
            resolved,
            pending,
            rejected,
            f'{resolution_rate:.1f}'
        ])
    
    return response

