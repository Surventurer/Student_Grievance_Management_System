from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import json

from apps.grievances.models import Grievance, Category, GrievanceComment, AuditLog
from apps.students.models import StudentProfile, AdminProfile


@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    print(f"Admin dashboard accessed by: {request.user.email}")
    print(f"User is admin: {getattr(request.user, 'is_admin', False)}")
    
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    try:
        # Get basic statistics with error handling
        total_grievances = Grievance.objects.count()
        pending_grievances = Grievance.objects.filter(status='pending').count()
        resolved_grievances = Grievance.objects.filter(status='resolved').count()
        rejected_grievances = Grievance.objects.filter(status='rejected').count()
        
        print(f"Statistics: Total={total_grievances}, Pending={pending_grievances}")
        
        # Get recent grievances with proper error handling
        recent_grievances = []
        try:
            recent_grievances = Grievance.objects.select_related('student', 'category').order_by('-submitted_at')[:5]
            print(f"Recent grievances count: {len(list(recent_grievances))}")
        except Exception as e:
            print(f"Error getting recent grievances: {e}")
        
        # Get category statistics with error handling
        category_stats = []
        try:
            category_stats = Category.objects.annotate(
                count=Count('grievances')
            ).order_by('-count')[:5]
            print(f"Category stats count: {len(list(category_stats))}")
        except Exception as e:
            print(f"Error getting category stats: {e}")
        
        # Simple monthly stats
        monthly_stats = [
            {'month': 'January 2025', 'count': 10},
            {'month': 'February 2025', 'count': 15},
            {'month': 'March 2025', 'count': 8},
            {'month': 'April 2025', 'count': 12},
            {'month': 'May 2025', 'count': 18},
            {'month': 'June 2025', 'count': 14},
        ]
        
        context = {
            'total_grievances': total_grievances,
            'pending_grievances': pending_grievances,
            'resolved_grievances': resolved_grievances,
            'rejected_grievances': rejected_grievances,
            'recent_grievances': recent_grievances,
            'category_stats': category_stats,
            'monthly_stats': monthly_stats,
        }
        
        print("Rendering admin dashboard template...")
        return render(request, 'admin_panel/dashboard_working.html', context)
        
    except Exception as e:
        print(f"Error in admin dashboard: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'admin_panel/dashboard_working.html', {
            'total_grievances': 0,
            'pending_grievances': 0,
            'resolved_grievances': 0,
            'rejected_grievances': 0,
            'recent_grievances': [],
            'category_stats': [],
            'monthly_stats': [],
        })


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


@login_required
def grievance_detail_view(request, grievance_id):
    """Detailed view of a specific grievance"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    grievance = get_object_or_404(Grievance, id=grievance_id)
    
    context = {
        'grievance': grievance,
    }
    
    return render(request, 'admin_panel/grievance_detail.html', context)


@login_required
@require_http_methods(["PATCH"])
def update_grievance_status(request, grievance_id):
    """Update grievance status"""
    if not request.user.is_admin:
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
                action=f'Update Grievance Status',
                description=f'Changed grievance {grievance.grievance_id} status to {new_status}'
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
    if not request.user.is_admin:
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
        
        return JsonResponse({
            'success': True, 
            'message': f'{"Internal note" if is_internal else "Response"} added successfully',
            'comment_id': str(comment.id),
            'timestamp': comment.timestamp.strftime('%b %d, %Y %H:%M')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def manage_categories_view(request):
    """View for managing grievance categories"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    categories = Category.objects.all().order_by('category_type', 'name')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_type = request.POST.get('category_type')
        
        if name and description and category_type:
            Category.objects.create(
                name=name,
                description=description,
                category_type=category_type,
                is_active=True
            )
            messages.success(request, 'Category created successfully')
            return redirect('admin_panel:manage_categories')
        else:
            messages.error(request, 'All fields are required')
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'admin_panel/manage_categories.html', context)


@login_required
def toggle_category_status(request, category_id):
    """Toggle category active status"""
    if not request.user.is_admin:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        category = get_object_or_404(Category, id=category_id)
        category.is_active = not category.is_active
        category.save()
        
        return JsonResponse({
            'success': True, 
            'is_active': category.is_active,
            'status': 'activated' if category.is_active else 'deactivated'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def student_detail_view(request, student_id):
    """Detailed view of a specific student"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    student = get_object_or_404(StudentProfile, id=student_id)
    student_grievances = Grievance.objects.filter(student=student).order_by('-submitted_at')
    
    # Pagination for grievances
    paginator = Paginator(student_grievances, 10)
    page_number = request.GET.get('page')
    grievances = paginator.get_page(page_number)
    
    context = {
        'student': student,
        'grievances': grievances,
        'total_grievances': student_grievances.count(),
        'pending_grievances': student_grievances.filter(status='pending').count(),
        'resolved_grievances': student_grievances.filter(status='resolved').count(),
        'rejected_grievances': student_grievances.filter(status='rejected').count(),
    }
    
    return render(request, 'admin_panel/student_detail.html', context)


@login_required
def audit_logs_view(request):
    """View for audit logs"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    audit_logs = paginator.get_page(page_number)
    
    context = {
        'audit_logs': audit_logs,
    }
    
    return render(request, 'admin_panel/audit_logs.html', context)


@login_required
def grievance_list_advanced(request):
    """Advanced grievance list with filtering and search"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    grievances = Grievance.objects.select_related('student__user', 'category').order_by('-submitted_at')
    
    # Filtering
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status_filter:
        grievances = grievances.filter(status=status_filter)
    
    if category_filter:
        grievances = grievances.filter(category_id=category_filter)
    
    if search_query:
        grievances = grievances.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )
    
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
