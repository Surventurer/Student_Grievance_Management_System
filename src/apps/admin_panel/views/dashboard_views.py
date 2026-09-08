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


@role_required(['admin', 'officer', 'superadmin'])
def admin_dashboard(request):
    """Admin dashboard view with department-based data filtering"""
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.models import Session
    from apps.students.models import AdminProfile
    
    User = get_user_model()
    user = request.user
    
    try:
        # Get accessible data based on user's department assignment
        accessible_grievances = user.get_accessible_grievances()
        accessible_students = user.get_accessible_students()
        
        # Calculate statistics from accessible data
        total_grievances = accessible_grievances.count()
        pending_grievances = accessible_grievances.filter(status='pending').count()
        resolved_grievances = accessible_grievances.filter(status='resolved').count()
        rejected_grievances = accessible_grievances.filter(status='rejected').count()
        recent_grievances = accessible_grievances.order_by('-submitted_at')[:10]
        
        # Student statistics
        total_students = accessible_students.count()
        
        # Get category statistics based on accessible grievances
        if user.is_superadmin:
            category_stats = Category.objects.annotate(count=Count('grievances')).order_by('-count')[:5]
        else:
            # Get categories for accessible grievances only
            accessible_grievance_ids = accessible_grievances.values_list('id', flat=True)
            category_stats = Category.objects.annotate(
                count=Count('grievances', filter=Q(grievances__id__in=accessible_grievance_ids))
            ).filter(count__gt=0).order_by('-count')[:5]
        
        # Monthly statistics for chart visualization
        current_year = timezone.now().year
        monthly_stats = []
        
        for month_num in range(1, 13):
            month_data = accessible_grievances.filter(
                submitted_at__year=current_year,
                submitted_at__month=month_num
            ).aggregate(
                total=Count('id'),
                pending=Count('id', filter=Q(status='pending')),
                resolved=Count('id', filter=Q(status='resolved')),
                rejected=Count('id', filter=Q(status='rejected'))
            )
            
            monthly_stats.append({
                'month': month_num,
                'month_name': datetime(current_year, month_num, 1).strftime('%b'),
                'total': month_data['total'] or 0,
                'pending': month_data['pending'] or 0,
                'resolved': month_data['resolved'] or 0,
                'rejected': month_data['rejected'] or 0,
            })
        
        # Add user role and department information to context
        
        # Additional statistics for the right panel
        total_users = 0
        active_sessions = 0
        department_students = 0
        department_officers = 0
        
        if user.is_superadmin:
            total_users = User.objects.count()
            # Count distinct users from active sessions
            active_session_qs = Session.objects.filter(expire_date__gte=timezone.now())
            active_user_ids = set()
            for session in active_session_qs:
                data = session.get_decoded()
                user_id = data.get('_auth_user_id')
                if user_id:
                    active_user_ids.add(user_id)
            active_sessions = len(active_user_ids)
            
        elif user.role in ['admin', 'officer']:
            department_students = accessible_students.count()
            department_officers = AdminProfile.objects.filter(department=user.assigned_department, role_level='officer').count() if user.assigned_department else 0
            
        context = {
            'total_grievances': total_grievances,
            'pending_grievances': pending_grievances,
            'resolved_grievances': resolved_grievances,
            'rejected_grievances': rejected_grievances,
            'recent_grievances': recent_grievances,
            'category_stats': category_stats,
            'monthly_stats': monthly_stats,
            'monthly_stats_json': json.dumps(monthly_stats),
            'total_students': total_students,
            'user_role': user.role,
            'is_superadmin': user.role == 'superadmin',
            'is_dept_admin': user.role == 'admin',
            'is_officer': user.role == 'officer',
            'assigned_department': user.assigned_department,
            'department_name': user.department_name,
            'total_users': total_users,
            'active_sessions': active_sessions,
            'department_students': department_students,
            'department_officers': department_officers,
            'can_manage_categories': can_manage_categories(user),
            'can_manage_auto_assignment': can_manage_auto_assignment(user),
            'can_view_audit_logs': can_view_audit_logs(user),
            'can_view_system_reports': can_view_system_reports(user),
        }
        
        return render(request, 'admin_panel/dashboard.html', context)
        
    except Exception as e:
        print(f"Error in admin dashboard: {e}")
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'admin_panel/dashboard.html', {
            'total_grievances': 0,
            'pending_grievances': 0,
            'resolved_grievances': 0,
            'rejected_grievances': 0,
            'recent_grievances': [],
            'category_stats': [],
            'monthly_stats': [],
        })



@login_required
def reports(request):
    """Reports view with role-based data access"""
    if not request.user.is_admin_or_officer:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    # Get grievances based on user's access level
    all_grievances = Grievance.objects.filter(is_archived=False)
    accessible_grievances = filter_grievances_by_access(request.user, all_grievances)
    
    # Get basic statistics from accessible grievances
    total_grievances = accessible_grievances.count()
    pending_count = accessible_grievances.filter(status='pending').count()
    resolved_count = accessible_grievances.filter(status='resolved').count()
    rejected_count = accessible_grievances.filter(status='rejected').count()
    
    # Calculate resolution rate
    resolution_rate = (resolved_count / total_grievances * 100) if total_grievances > 0 else 0
    
    # Get active students count
    active_students = StudentProfile.objects.filter(user__is_active=True).count()
    
    # Get category statistics
    category_stats = Category.objects.annotate(
        count=Count('grievances')
    ).order_by('-count')
    
    # Get monthly statistics (last 6 months)
    monthly_stats = []
    for i in range(6):
        date = timezone.now() - timedelta(days=30*i)
        month_name = date.strftime("%B %Y")
        count = Grievance.objects.filter(
            submitted_at__year=date.year,
            submitted_at__month=date.month
        ).count()
        monthly_stats.append({
            'month': month_name,
            'count': count
        })
    monthly_stats.reverse()
    
    context = {
        'total_grievances': total_grievances,
        'pending_count': pending_count,
        'resolved_count': resolved_count,
        'rejected_count': rejected_count,
        'resolution_rate': round(resolution_rate, 1),
        'avg_resolution_time': 5,  # Placeholder - implement actual calculation
        'active_students': active_students,
        'category_stats': category_stats,
        'monthly_stats': monthly_stats,
    }
    
    return render(request, 'admin_panel/reports.html', context)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_api(request):
    """Generate reports API"""
    if not request.user.is_admin_or_officer:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Sample report data
    return Response({
        'monthly_stats': {
            'total_grievances': Grievance.objects.count(),
            'resolved_grievances': Grievance.objects.filter(status='resolved').count(),
            'pending_grievances': Grievance.objects.filter(status='pending').count(),
        }
    })



@login_required
@staff_member_required
def reports_dashboard(request):
    """Admin reports dashboard with statistics"""
    
    # Get date filters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    month = request.GET.get('month')
    year = request.GET.get('year', timezone.now().year)
    
    # Base queryset
    grievances = Grievance.objects.all()
    
    # Apply filters
    if from_date and to_date:
        grievances = grievances.filter(
            submitted_at__date__gte=from_date,
            submitted_at__date__lte=to_date
        )
    elif month and year:
        grievances = grievances.filter(
            submitted_at__year=year,
            submitted_at__month=month
        )
    
    # Calculate statistics
    total_grievances = grievances.count()
    solved_grievances = grievances.filter(status='resolved').count()
    pending_grievances = grievances.filter(status='pending').count()
    rejected_grievances = grievances.filter(status='rejected').count()
    
    # Category wise statistics
    category_stats = grievances.values('category__name').annotate(
        count=Count('id'),
        solved=Count('id', filter=Q(status='resolved')),
        pending=Count('id', filter=Q(status='pending')),
        rejected=Count('id', filter=Q(status='rejected'))
    ).order_by('-count')
    
    # Monthly statistics for current year
    monthly_stats = []
    for month_num in range(1, 13):
        month_grievances = Grievance.objects.filter(
            submitted_at__year=year,
            submitted_at__month=month_num
        )
        monthly_stats.append({
            'month': month_num,
            'month_name': datetime(int(year), month_num, 1).strftime('%B'),
            'total': month_grievances.count(),
            'solved': month_grievances.filter(status='resolved').count(),
            'pending': month_grievances.filter(status='pending').count(),
            'rejected': month_grievances.filter(status='rejected').count(),
        })
    
    # School/Department wise statistics
    school_stats = grievances.values('student__school').annotate(
        count=Count('id'),
        solved=Count('id', filter=Q(status='resolved')),
        pending=Count('id', filter=Q(status='pending'))
    ).order_by('-count')[:10]
    
    department_stats = grievances.values('student__department').annotate(
        count=Count('id'),
        solved=Count('id', filter=Q(status='resolved')),
        pending=Count('id', filter=Q(status='pending'))
    ).order_by('-count')[:10]
    
    context = {
        'total_grievances': total_grievances,
        'solved_grievances': solved_grievances,
        'pending_grievances': pending_grievances,
        'rejected_grievances': rejected_grievances,
        'category_stats': category_stats,
        'monthly_stats': monthly_stats,
        'monthly_stats_json': json.dumps(list(monthly_stats)),
        'school_stats': school_stats,
        'department_stats': department_stats,
        'from_date': from_date,
        'to_date': to_date,
        'selected_month': month,
        'selected_year': year,
        'years': range(timezone.now().year - 5, timezone.now().year + 2),  # Current year - 5 to current year + 1
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'),
            (4, 'April'), (5, 'May'), (6, 'June'),
            (7, 'July'), (8, 'August'), (9, 'September'),
            (10, 'October'), (11, 'November'), (12, 'December')
        ]
    }
    
    return render(request, 'admin_panel/reports.html', context)



@login_required
def auto_assign_management(request):
    """Main view for managing auto-assignment of grievances - Superadmin only"""
    if not can_manage_auto_assignment(request.user):
        messages.error(request, 'Access denied - Superadmin privileges required for auto-assignment management')
        return redirect('admin_panel:dashboard')
    
    # Get all categories with their assignments
    categories = Category.objects.filter(is_active=True).prefetch_related('assignments__assigned_admin')
    
    # Get assignment statistics
    total_assignments = CategoryAssignment.objects.filter(is_active=True).count()
    categories_with_assignments = categories.filter(assignments__is_active=True).distinct().count()
    categories_without_assignments = categories.exclude(assignments__is_active=True).count()
    
    # Get recent auto-assignments
    recent_assignments = AuditLog.objects.filter(
        action='assign',
        description__icontains='Auto-assigned'
    ).select_related('user').order_by('-timestamp')[:10]
    
    context = {
        'categories': categories,
        'total_assignments': total_assignments,
        'categories_with_assignments': categories_with_assignments,
        'categories_without_assignments': categories_without_assignments,
        'recent_assignments': recent_assignments,
    }
    
    return render(request, 'admin_panel/auto_assign_management.html', context)



@login_required
def crud_management(request):
    """Main CRUD management dashboard"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied - Superadmin privileges required')
        return redirect('admin_panel:dashboard')
    
    # Get statistics
    from apps.students.models import School, Department
    
    stats = {
        'categories': Category.objects.count(),
        'active_categories': Category.objects.filter(is_active=True).count(),
        'schools': School.objects.count(),
        'departments': Department.objects.count(),
        'category_assignments': CategoryAssignment.objects.filter(is_active=True).count()
    }
    
    context = {
        'stats': stats,
        'page_title': 'CRUD Management'
    }
    return render(request, 'admin_panel/crud_management.html', context)

