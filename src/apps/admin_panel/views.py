from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.grievances.models import Grievance, Category, AuditLog
from apps.students.models import StudentProfile, AdminProfile


@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    # Get basic statistics
    total_grievances = Grievance.objects.count()
    pending_grievances = Grievance.objects.filter(status='pending').count()
    under_review_grievances = Grievance.objects.filter(status='under_review').count()
    resolved_grievances = Grievance.objects.filter(status='resolved').count()
    
    # Get recent grievances
    recent_grievances = Grievance.objects.select_related('student__user', 'category').order_by('-submitted_at')[:10]
    
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
        'pending_grievances': pending_grievances,
        'under_review_grievances': under_review_grievances,
        'resolved_grievances': resolved_grievances,
        'recent_grievances': recent_grievances,
        'category_stats': category_stats,
        'monthly_stats': monthly_stats,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


@login_required
def grievance_list(request):
    """Grievance list view"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    grievances = Grievance.objects.select_related('student__user', 'category').order_by('-submitted_at')
    categories = Category.objects.all()
    
    context = {
        'grievances': grievances,
        'categories': categories,
    }
    
    return render(request, 'admin_panel/grievance_list.html', context)


@login_required
def student_list(request):
    """Student list view"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    students = StudentProfile.objects.select_related('user').annotate(
        grievance_count=Count('grievances')
    ).order_by('student_id')
    
    context = {
        'students': students,
    }
    
    return render(request, 'admin_panel/student_list.html', context)


@login_required
def reports(request):
    """Reports view"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    # Get basic statistics
    total_grievances = Grievance.objects.count()
    pending_count = Grievance.objects.filter(status='pending').count()
    under_review_count = Grievance.objects.filter(status='under_review').count()
    resolved_count = Grievance.objects.filter(status='resolved').count()
    rejected_count = Grievance.objects.filter(status='rejected').count()
    
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
        'under_review_count': under_review_count,
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
def manage_grievances(request):
    """Manage grievances API"""
    if not request.user.is_admin:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    grievances = Grievance.objects.all().order_by('-submitted_at')
    
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
    if not request.user.is_admin:
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_students(request):
    """Manage students API"""
    if not request.user.is_admin:
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_categories(request):
    """Manage categories API"""
    if not request.user.is_admin:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    categories = Category.objects.all()
    
    return Response([
        {
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'category_type': c.category_type,
            'is_active': c.is_active,
        }
        for c in categories
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_api(request):
    """Generate reports API"""
    if not request.user.is_admin:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Sample report data
    return Response({
        'monthly_stats': {
            'total_grievances': Grievance.objects.count(),
            'resolved_grievances': Grievance.objects.filter(status='resolved').count(),
            'pending_grievances': Grievance.objects.filter(status='pending').count(),
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_logs(request):
    """Get audit logs API"""
    if not request.user.is_superadmin:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
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
