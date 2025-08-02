from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Q, Avg
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

from apps.grievances.models import Grievance, Category, GrievanceComment, AuditLog, CategoryAssignment
from apps.students.models import StudentProfile, AdminProfile
from apps.authentication.decorators import admin_required, superadmin_required, permission_required
from apps.admin_panel.permissions import (
    filter_grievances_by_access, filter_students_by_access, can_access_all_data,
    can_manage_system_settings, can_manage_categories, can_manage_auto_assignment,
    can_view_audit_logs, can_view_system_reports, department_access_required
)


@admin_required
def admin_dashboard(request):
    """Admin dashboard view with role-based data filtering"""
    user = request.user
    
    try:
        # Get all grievances first, then filter based on access
        all_grievances = Grievance.objects.select_related('student', 'category', 'assigned_to')
        accessible_grievances = filter_grievances_by_access(user, all_grievances)
        
        # Calculate statistics from accessible grievances
        total_grievances = accessible_grievances.count()
        pending_grievances = accessible_grievances.filter(status='pending').count()
        resolved_grievances = accessible_grievances.filter(status='resolved').count()
        rejected_grievances = accessible_grievances.filter(status='rejected').count()
        recent_grievances = accessible_grievances.order_by('-submitted_at')[:10]
        
        # Get category statistics based on accessible grievances
        if can_access_all_data(user):
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
        
        # Add user role information to context
        context = {
            'total_grievances': total_grievances,
            'pending_grievances': pending_grievances,
            'resolved_grievances': resolved_grievances,
            'rejected_grievances': rejected_grievances,
            'recent_grievances': recent_grievances,
            'category_stats': category_stats,
            'monthly_stats': monthly_stats,
            'monthly_stats_json': json.dumps(monthly_stats),
            'user_role': user.role,
            'is_superadmin': user.role == 'superadmin',
            'is_dept_admin': user.role == 'admin',
            'is_officer': user.role == 'officer',
            'can_manage_categories': can_manage_categories(user),
            'can_manage_auto_assignment': can_manage_auto_assignment(user),
            'can_view_audit_logs': can_view_audit_logs(user),
            'can_view_system_reports': can_view_system_reports(user),
        }
        
        return render(request, 'admin_panel/dashboard_working.html', context)
        
    except Exception as e:
        print(f"Error in admin dashboard: {e}")
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
@department_access_required
def grievance_list(request):
    """Grievance list view with role-based filtering"""
    user = request.user
    
    # Get all grievances and filter based on user's access level
    all_grievances = Grievance.objects.select_related('student__user', 'category')
    accessible_grievances = filter_grievances_by_access(user, all_grievances)
    
    # Order and get categories for filtering
    grievances = accessible_grievances.order_by('-submitted_at')
    
    # Get categories that are relevant to the user's accessible grievances
    if can_access_all_data(user):
        categories = Category.objects.all()
    else:
        # Only show categories that have grievances the user can access
        accessible_category_ids = accessible_grievances.values_list('category_id', flat=True).distinct()
        categories = Category.objects.filter(id__in=accessible_category_ids)
    
    context = {
        'grievances': grievances,
        'categories': categories,
        'user_role': user.role,
        'can_manage_categories': can_manage_categories(user),
    }
    
    return render(request, 'admin_panel/grievance_list.html', context)


@login_required
@department_access_required  
def student_list(request):
    """Enhanced Student list view with search, filtering, and role-based access"""
    user = request.user
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    # Get all students and filter based on user's access level
    all_students = StudentProfile.objects.select_related('user')
    accessible_students = filter_students_by_access(user, all_students)
    
    # Apply additional filters
    students = accessible_students
    
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(student_id__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(department__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            students = students.filter(user__is_active=True)
        elif status_filter == 'inactive':
            students = students.filter(user__is_active=False)
    
    # Department filter - only apply if user can see multiple departments
    if department_filter and can_access_all_data(user):
        students = students.filter(department__icontains=department_filter)
    
    # Get departments for filter dropdown (only departments the user can access)
    if can_access_all_data(user):
        departments = StudentProfile.objects.values_list('department', flat=True).distinct().order_by('department')
    else:
        departments = accessible_students.values_list('department', flat=True).distinct().order_by('department')
    
    # Pagination
    paginator = Paginator(students.order_by('student_id'), 20)
    page_number = request.GET.get('page')
    students_page = paginator.get_page(page_number)
    
    context = {
        'students': students_page,
        'departments': departments,
        'search_query': search_query,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'user_role': user.role,
        'can_access_all_data': can_access_all_data(user),
    }
    
    return render(request, 'admin_panel/student_list.html', context)
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    # Base queryset with related data
    students = StudentProfile.objects.select_related('user').annotate(
        grievance_count=Count('grievances')
    )
    
    # Apply search filter
    if search_query:
        students = students.filter(
            Q(student_id__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(school__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter == 'active':
        students = students.filter(user__is_active=True)
    elif status_filter == 'suspended':
        students = students.filter(user__is_active=False)
    
    # Apply department filter
    if department_filter:
        students = students.filter(department__icontains=department_filter)
    
    # Order by student ID
    students = students.order_by('student_id')
    
    # Pagination
    paginator = Paginator(students, 20)  # 20 students per page
    page_number = request.GET.get('page')
    students_page = paginator.get_page(page_number)
    
    # Get schools for the add student form
    from apps.students.models import School
    schools = School.objects.all().order_by('name')
    
    context = {
        'students': students_page,
        'schools': schools,
        'search_query': search_query,
        'status_filter': status_filter,
        'department_filter': department_filter,
    }
    
    return render(request, 'admin_panel/student_list.html', context)


@login_required
def reports(request):
    """Reports view with role-based data access"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    # Get grievances based on user's access level
    all_grievances = Grievance.objects.all()
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
    
    # Calculate counts
    academic_count = categories.filter(category_type='academic').count()
    non_academic_count = categories.filter(category_type='non_academic').count()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        category_type = request.POST.get('category_type')
        
        if name and category_type:
            Category.objects.create(
                name=name,
                description=f"{name} category",  # Provide a default description
                category_type=category_type,
                is_active=True
            )
            messages.success(request, 'Category created successfully')
            return redirect('admin_panel:manage_categories')
        else:
            messages.error(request, 'Category name and type are required')
    
    context = {
        'categories': categories,
        'academic_count': academic_count,
        'non_academic_count': non_academic_count,
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
def update_category(request):
    """Update category details"""
    if not request.user.is_admin:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_id = data.get('category_id')
        name = data.get('name', '').strip()
        category_type = data.get('category_type')
        
        if not all([category_id, name, category_type]):
            return JsonResponse({'success': False, 'error': 'Category ID, name, and type are required'}, status=400)
        
        if category_type not in ['academic', 'non_academic']:
            return JsonResponse({'success': False, 'error': 'Invalid category type'}, status=400)
        
        category = get_object_or_404(Category, id=category_id)
        
        # Check if name already exists for another category
        if Category.objects.filter(name=name).exclude(id=category_id).exists():
            return JsonResponse({'success': False, 'error': 'Category with this name already exists'}, status=400)
        
        category.name = name
        category.category_type = category_type
        category.description = f"{name} category"  # Auto-generate description
        category.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Category updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def delete_category(request):
    """Delete a single category"""
    if not request.user.is_admin:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_id = data.get('category_id')
        
        if not category_id:
            return JsonResponse({'success': False, 'error': 'Category ID is required'}, status=400)
        
        category = get_object_or_404(Category, id=category_id)
        
        # Check if category has grievances
        if category.grievances.exists():
            return JsonResponse({
                'success': False, 
                'error': f'Cannot delete category "{category.name}" as it has associated grievances'
            }, status=400)
        
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Category deleted successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def bulk_delete_categories(request):
    """Bulk delete categories"""
    if not request.user.is_admin:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_ids = data.get('category_ids', [])
        
        if not category_ids:
            return JsonResponse({'success': False, 'error': 'No categories selected'}, status=400)
        
        # Get categories and check for associated grievances
        categories = Category.objects.filter(id__in=category_ids)
        categories_with_grievances = []
        
        for category in categories:
            if category.grievances.exists():
                categories_with_grievances.append(category.name)
        
        if categories_with_grievances:
            return JsonResponse({
                'success': False,
                'error': f'Cannot delete categories with associated grievances: {", ".join(categories_with_grievances)}'
            }, status=400)
        
        deleted_count = categories.count()
        categories.delete()
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} categories'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def bulk_update_category_status(request):
    """Bulk activate/deactivate categories"""
    if not request.user.is_admin:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        category_ids = data.get('category_ids', [])
        is_active = data.get('is_active', True)
        
        if not category_ids:
            return JsonResponse({'success': False, 'error': 'No categories selected'}, status=400)
        
        updated_count = Category.objects.filter(id__in=category_ids).update(is_active=is_active)
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully {"activated" if is_active else "deactivated"} {updated_count} categories'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
    
    # Pagination
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
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        stats = {
            'total': Grievance.objects.count(),
            'pending': Grievance.objects.filter(status='pending').count(),
            'resolved': Grievance.objects.filter(status='resolved').count(),
            'rejected': Grievance.objects.filter(status='rejected').count(),
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def bulk_delete_grievances(request):
    """API endpoint to bulk delete grievances"""
    if not request.user.is_admin:
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
    if not request.user.is_admin:
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
    if not request.user.is_admin:
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
def departments_api(request):
    """API endpoint to get departments by school"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    school_id = request.GET.get('school')
    if school_id:
        from apps.students.models import Department
        departments = Department.objects.filter(school_id=school_id).values('id', 'name')
        return JsonResponse({'departments': list(departments)})
    else:
        from apps.students.models import Department
        departments = Department.objects.all().values('id', 'name')
        return JsonResponse({'departments': list(departments)})


@login_required
def add_student_api(request):
    """API endpoint to add a new student"""
    if not request.user.is_admin:
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


# Auto-Assignment Management Views

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
def category_assignment_detail(request, category_id):
    """Detailed view for managing assignments for a specific category"""
    if not request.user.role in ['admin', 'superadmin']:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    category = get_object_or_404(Category, id=category_id, is_active=True)
    assignments = CategoryAssignment.objects.filter(
        category=category, 
        is_active=True
    ).select_related('assigned_admin__user').order_by('-priority_level', 'department')
    
    # Get available admins for assignment
    available_admins = AdminProfile.objects.filter(
        role_level__in=['officer', 'dept_admin', 'superadmin']
    ).select_related('user')
    
    # Get departments that need assignment
    from apps.students.models import Department
    departments = Department.objects.all().order_by('name')
    
    # Get assignment statistics for this category
    total_grievances = Grievance.objects.filter(category=category).count()
    auto_assigned = Grievance.objects.filter(
        category=category,
        assigned_to__isnull=False
    ).count()
    unassigned = total_grievances - auto_assigned
    
    context = {
        'category': category,
        'assignments': assignments,
        'available_admins': available_admins,
        'departments': departments,
        'total_grievances': total_grievances,
        'auto_assigned': auto_assigned,
        'unassigned': unassigned,
    }
    
    return render(request, 'admin_panel/category_assignment_detail.html', context)


@login_required
@require_http_methods(["POST"])
def create_category_assignment(request):
    """Create a new category assignment"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        category_id = data.get('category_id')
        admin_id = data.get('admin_id')
        department = data.get('department', '').strip()
        school = data.get('school', '').strip()
        priority_level = int(data.get('priority_level', 1))
        keywords = data.get('keywords', '').strip()
        
        # Validate required fields
        if not category_id or not admin_id or not department:
            return JsonResponse({'success': False, 'error': 'Category, admin, and department are required'})
        
        category = get_object_or_404(Category, id=category_id, is_active=True)
        admin = get_object_or_404(AdminProfile, id=admin_id)
        
        # Check for existing assignment
        existing = CategoryAssignment.objects.filter(
            category=category,
            department__iexact=department,
            assigned_admin=admin
        ).first()
        
        if existing:
            if existing.is_active:
                return JsonResponse({'success': False, 'error': 'This assignment already exists'})
            else:
                # Reactivate existing assignment
                existing.is_active = True
                existing.priority_level = priority_level
                existing.auto_assign_keywords = keywords
                existing.school = school
                existing.save()
                assignment = existing
        else:
            # Create new assignment
            assignment = CategoryAssignment.objects.create(
                category=category,
                assigned_admin=admin,
                department=department,
                school=school,
                priority_level=priority_level,
                auto_assign_keywords=keywords,
                created_by=request.user
            )
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='create',
            target_model='CategoryAssignment',
            target_id=str(assignment.id),
            description=f"Created assignment: {category.name} → {admin} for {department}",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({
            'success': True,
            'assignment': {
                'id': str(assignment.id),
                'admin_name': assignment.assigned_admin.user.get_full_name(),
                'department': assignment.department,
                'school': assignment.school,
                'priority_level': assignment.priority_level,
                'keywords': assignment.auto_assign_keywords or '',
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def update_category_assignment(request, assignment_id):
    """Update an existing category assignment"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        assignment = get_object_or_404(CategoryAssignment, id=assignment_id)
        data = json.loads(request.body)
        
        # Update fields
        assignment.priority_level = int(data.get('priority_level', assignment.priority_level))
        assignment.auto_assign_keywords = data.get('keywords', assignment.auto_assign_keywords)
        assignment.school = data.get('school', assignment.school)
        assignment.is_active = data.get('is_active', assignment.is_active)
        assignment.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='update',
            target_model='CategoryAssignment',
            target_id=str(assignment.id),
            description=f"Updated assignment: {assignment.category.name} → {assignment.assigned_admin}",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def delete_category_assignment(request, assignment_id):
    """Delete a category assignment"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        assignment = get_object_or_404(CategoryAssignment, id=assignment_id)
        
        # Soft delete by setting is_active to False
        assignment.is_active = False
        assignment.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='delete',
            target_model='CategoryAssignment',
            target_id=str(assignment.id),
            description=f"Deleted assignment: {assignment.category.name} → {assignment.assigned_admin}",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def test_auto_assignment(request):
    """Test auto-assignment for unassigned grievances"""
    if not request.user.role in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        # Get unassigned grievances
        unassigned_grievances = Grievance.objects.filter(
            assigned_to__isnull=True,
            status='pending'
        ).select_related('category', 'student')
        
        results = []
        assigned_count = 0
        
        for grievance in unassigned_grievances[:20]:  # Test first 20
            assigned_admin, reason = grievance.auto_assign()
            if assigned_admin:
                assigned_count += 1
                results.append({
                    'grievance_id': grievance.grievance_id,
                    'title': grievance.title,
                    'assigned_to': assigned_admin.user.get_full_name(),
                    'reason': reason
                })
            else:
                results.append({
                    'grievance_id': grievance.grievance_id,
                    'title': grievance.title,
                    'assigned_to': None,
                    'reason': reason
                })
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='update',
            target_model='Grievance',
            target_id='bulk',
            description=f"Ran auto-assignment test: {assigned_count}/{len(results)} grievances assigned",
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return JsonResponse({
            'success': True,
            'assigned_count': assigned_count,
            'total_tested': len(results),
            'results': results[:10]  # Return first 10 results
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


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


# =============================================================================
# CRUD MANAGEMENT VIEWS - Categories, Schools, Departments  
# =============================================================================

@login_required
def crud_management(request):
    """Main CRUD management dashboard"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
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

# Category CRUD Views
@login_required
def category_management(request):
    """Category management view - Superadmin only"""
    if not can_manage_categories(request.user):
        messages.error(request, 'Access denied - Superadmin privileges required for category management')
        return redirect('admin_panel:dashboard')
    
    # Get search and filter parameters
    search = request.GET.get('search', '')
    category_type = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    
    # Build queryset
    categories = Category.objects.all()
    
    if search:
        categories = categories.filter(name__icontains=search)
    
    if category_type:
        categories = categories.filter(category_type=category_type)
        
    if status_filter:
        categories = categories.filter(is_active=(status_filter == 'active'))
    
    categories = categories.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    
    # Process keywords for each category (after pagination)
    for category in categories:
        if hasattr(category, 'keywords') and category.keywords:
            category.keyword_list = [kw.strip() for kw in category.keywords.split(',') if kw.strip()]
        else:
            category.keyword_list = []
    
    context = {
        'categories': categories,
        'search': search,
        'category_type': category_type,
        'status_filter': status_filter,
        'category_types': Category.CATEGORY_TYPES,
        'page_title': 'Category Management'
    }
    return render(request, 'admin_panel/category_management.html', context)

@login_required 
@require_http_methods(["GET", "POST"])
def category_create(request):
    """Create new category"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            category_type = request.POST.get('category_type')
            keywords = request.POST.get('keywords', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            auto_assign_enabled = request.POST.get('auto_assign_enabled') == 'on'
            
            if not name or not category_type:
                messages.error(request, 'Name and category type are required')
                return render(request, 'admin_panel/category_form.html', {
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            # Check for duplicate names
            if Category.objects.filter(name__iexact=name).exists():
                messages.error(request, 'A category with this name already exists')
                return render(request, 'admin_panel/category_form.html', {
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            category = Category.objects.create(
                name=name,
                description=f"{name} category",  # Auto-generate description
                category_type=category_type,
                keywords=keywords,
                is_active=is_active,
                auto_assign_enabled=auto_assign_enabled
            )
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='category_create',
                description=f'Created category: {category.name}',
                target_model='Category',
                target_id=str(category.id)
            )
            
            messages.success(request, f'Category "{category.name}" created successfully')
            return redirect('admin_panel:category_management')
            
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
    
    context = {
        'category_types': Category.CATEGORY_TYPES,
        'action': 'Create',
        'page_title': 'Create Category'
    }
    return render(request, 'admin_panel/category_form.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def category_edit(request, category_id):
    """Edit existing category"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            category_type = request.POST.get('category_type')
            keywords = request.POST.get('keywords', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            auto_assign_enabled = request.POST.get('auto_assign_enabled') == 'on'
            
            if not name or not category_type:
                messages.error(request, 'Name and category type are required')
                return render(request, 'admin_panel/category_form.html', {
                    'category': category,
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            # Check for duplicate names (excluding current category)
            if Category.objects.filter(name__iexact=name).exclude(id=category.id).exists():
                messages.error(request, 'A category with this name already exists')
                return render(request, 'admin_panel/category_form.html', {
                    'category': category,
                    'category_types': Category.CATEGORY_TYPES,
                    'form_data': request.POST
                })
            
            # Store old values for audit
            old_name = category.name
            
            # Update category
            category.name = name
            category.description = f"{name} category"  # Auto-generate description
            category.category_type = category_type
            category.keywords = keywords
            category.is_active = is_active
            category.auto_assign_enabled = auto_assign_enabled
            category.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='category_update',
                description=f'Updated category: {old_name} → {category.name}',
                target_model='Category',
                target_id=str(category.id)
            )
            
            messages.success(request, f'Category "{category.name}" updated successfully')
            return redirect('admin_panel:category_management')
            
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')
    
    context = {
        'category': category,
        'category_types': Category.CATEGORY_TYPES,
        'action': 'Edit',
        'page_title': 'Edit Category'
    }
    return render(request, 'admin_panel/category_form.html', context)

@login_required
@require_http_methods(["POST"])
def category_delete(request, category_id):
    """Delete category"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        category = get_object_or_404(Category, id=category_id)
        
        # Check if category has grievances
        grievance_count = Grievance.objects.filter(category=category).count()
        if grievance_count > 0:
            return JsonResponse({
                'error': f'Cannot delete category. It has {grievance_count} associated grievances.'
            }, status=400)
        
        category_name = category.name
        category.delete()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='category_delete',
            description=f'Deleted category: {category_name}',
            target_model='Category',
            target_id=str(category_id)
        )
        
        return JsonResponse({'success': True, 'message': f'Category "{category_name}" deleted successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# School CRUD Views
@login_required
def school_management(request):
    """School management view"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import School
    
    search = request.GET.get('search', '')
    schools = School.objects.all()
    
    if search:
        schools = schools.filter(name__icontains=search)
    
    schools = schools.annotate(
        department_count=Count('departments')
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(schools, 10)
    page_number = request.GET.get('page')
    schools = paginator.get_page(page_number)
    
    context = {
        'schools': schools,
        'search': search,
        'page_title': 'School Management'
    }
    return render(request, 'admin_panel/school_management.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def school_create(request):
    """Create new school"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        try:
            from apps.students.models import School
            
            name = request.POST.get('name', '').strip()
            
            if not name:
                messages.error(request, 'School name is required')
                return render(request, 'admin_panel/school_form.html', {
                    'form_data': request.POST
                })
            
            # Check for duplicate names
            if School.objects.filter(name__iexact=name).exists():
                messages.error(request, 'A school with this name already exists')
                return render(request, 'admin_panel/school_form.html', {
                    'form_data': request.POST
                })
            
            school = School.objects.create(name=name)
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='school_create',
                description=f'Created school: {school.name}',
                target_model='School',
                target_id=str(school.id)
            )
            
            messages.success(request, f'School "{school.name}" created successfully')
            return redirect('admin_panel:school_management')
            
        except Exception as e:
            messages.error(request, f'Error creating school: {str(e)}')
    
    context = {
        'action': 'Create',
        'page_title': 'Create School'
    }
    return render(request, 'admin_panel/school_form.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def school_edit(request, school_id):
    """Edit existing school"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import School
    
    school = get_object_or_404(School, id=school_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            
            if not name:
                messages.error(request, 'School name is required')
                return render(request, 'admin_panel/school_form.html', {
                    'school': school,
                    'form_data': request.POST
                })
            
            # Check for duplicate names (excluding current school)
            if School.objects.filter(name__iexact=name).exclude(id=school.id).exists():
                messages.error(request, 'A school with this name already exists')
                return render(request, 'admin_panel/school_form.html', {
                    'school': school,
                    'form_data': request.POST
                })
            
            old_name = school.name
            school.name = name
            school.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='school_update',
                description=f'Updated school: {old_name} → {school.name}',
                target_model='School',
                target_id=str(school.id)
            )
            
            messages.success(request, f'School "{school.name}" updated successfully')
            return redirect('admin_panel:school_management')
            
        except Exception as e:
            messages.error(request, f'Error updating school: {str(e)}')
    
    context = {
        'school': school,
        'action': 'Edit',
        'page_title': 'Edit School'
    }
    return render(request, 'admin_panel/school_form.html', context)

@login_required
@require_http_methods(["POST"])
def school_delete(request, school_id):
    """Delete school"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from apps.students.models import School
        
        school = get_object_or_404(School, id=school_id)
        
        # Check if school has departments
        department_count = school.departments.count()
        if department_count > 0:
            return JsonResponse({
                'error': f'Cannot delete school. It has {department_count} associated departments.'
            }, status=400)
        
        school_name = school.name
        school.delete()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='school_delete',
            description=f'Deleted school: {school_name}',
            target_model='School',
            target_id=str(school_id)
        )
        
        return JsonResponse({'success': True, 'message': f'School "{school_name}" deleted successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Department CRUD Views
@login_required
def department_management(request):
    """Department management view"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import Department, School
    
    search = request.GET.get('search', '')
    school_filter = request.GET.get('school', '')
    
    departments = Department.objects.select_related('school')
    
    if search:
        departments = departments.filter(
            Q(name__icontains=search) | 
            Q(school__name__icontains=search)
        )
    
    if school_filter:
        departments = departments.filter(school_id=school_filter)
    
    departments = departments.annotate(
        student_count=Count('studentprofile')
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(departments, 10)
    page_number = request.GET.get('page')
    departments = paginator.get_page(page_number)
    
    context = {
        'departments': departments,
        'schools': School.objects.all().order_by('name'),
        'search': search,
        'school_filter': school_filter,
        'page_title': 'Department Management'
    }
    return render(request, 'admin_panel/department_management.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def department_create(request):
    """Create new department"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        try:
            from apps.students.models import Department, School
            
            name = request.POST.get('name', '').strip()
            school_id = request.POST.get('school')
            
            if not name:
                messages.error(request, 'Department name is required')
                return render(request, 'admin_panel/department_form.html', {
                    'schools': School.objects.all().order_by('name'),
                    'form_data': request.POST
                })
            
            school = None
            if school_id:
                try:
                    school = School.objects.get(id=school_id)
                except School.DoesNotExist:
                    messages.error(request, 'Selected school does not exist')
                    return render(request, 'admin_panel/department_form.html', {
                        'schools': School.objects.all().order_by('name'),
                        'form_data': request.POST
                    })
            
            # Check for duplicate names within the same school
            if school:
                if Department.objects.filter(name__iexact=name, school=school).exists():
                    messages.error(request, f'A department with this name already exists in {school.name}')
                    return render(request, 'admin_panel/department_form.html', {
                        'schools': School.objects.all().order_by('name'),
                        'form_data': request.POST
                    })
            else:
                if Department.objects.filter(name__iexact=name, school__isnull=True).exists():
                    messages.error(request, 'A department with this name already exists')
                    return render(request, 'admin_panel/department_form.html', {
                        'schools': School.objects.all().order_by('name'),
                        'form_data': request.POST
                    })
            
            department = Department.objects.create(
                name=name,
                school=school
            )
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='department_create',
                description=f'Created department: {department.name}' + (f' in {school.name}' if school else ''),
                target_model='Department',
                target_id=str(department.id)
            )
            
            messages.success(request, f'Department "{department.name}" created successfully')
            return redirect('admin_panel:department_management')
            
        except Exception as e:
            messages.error(request, f'Error creating department: {str(e)}')
    
    from apps.students.models import School
    context = {
        'schools': School.objects.all().order_by('name'),
        'action': 'Create',
        'page_title': 'Create Department'
    }
    return render(request, 'admin_panel/department_form.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def department_edit(request, department_id):
    """Edit existing department"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        messages.error(request, 'Access denied - Admin privileges required')
        return redirect('authentication:login')
    
    from apps.students.models import Department, School
    
    department = get_object_or_404(Department, id=department_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            school_id = request.POST.get('school')
            
            if not name:
                messages.error(request, 'Department name is required')
                return render(request, 'admin_panel/department_form.html', {
                    'department': department,
                    'schools': School.objects.all().order_by('name'),
                    'form_data': request.POST
                })
            
            school = None
            if school_id:
                try:
                    school = School.objects.get(id=school_id)
                except School.DoesNotExist:
                    messages.error(request, 'Selected school does not exist')
                    return render(request, 'admin_panel/department_form.html', {
                        'department': department,
                        'schools': School.objects.all().order_by('name'),
                        'form_data': request.POST
                    })
            
            # Check for duplicate names (excluding current department)
            if school:
                if Department.objects.filter(name__iexact=name, school=school).exclude(id=department.id).exists():
                    messages.error(request, f'A department with this name already exists in {school.name}')
                    return render(request, 'admin_panel/department_form.html', {
                        'department': department,
                        'schools': School.objects.all().order_by('name'),
                        'form_data': request.POST
                    })
            else:
                if Department.objects.filter(name__iexact=name, school__isnull=True).exclude(id=department.id).exists():
                    messages.error(request, 'A department with this name already exists')
                    return render(request, 'admin_panel/department_form.html', {
                        'department': department,
                        'schools': School.objects.all().order_by('name'),
                        'form_data': request.POST
                    })
            
            old_name = department.name
            old_school = department.school
            
            department.name = name
            department.school = school
            department.save()
            
            # Create audit log
            school_info = f' in {school.name}' if school else ''
            old_school_info = f' in {old_school.name}' if old_school else ''
            
            AuditLog.objects.create(
                user=request.user,
                action='department_update',
                description=f'Updated department: {old_name}{old_school_info} → {department.name}{school_info}',
                target_model='Department',
                target_id=str(department.id)
            )
            
            messages.success(request, f'Department "{department.name}" updated successfully')
            return redirect('admin_panel:department_management')
            
        except Exception as e:
            messages.error(request, f'Error updating department: {str(e)}')
    
    context = {
        'department': department,
        'schools': School.objects.all().order_by('name'),
        'action': 'Edit',
        'page_title': 'Edit Department'
    }
    return render(request, 'admin_panel/department_form.html', context)

@login_required
@require_http_methods(["POST"])
def department_delete(request, department_id):
    """Delete department"""
    if not hasattr(request.user, 'is_admin') or not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from apps.students.models import Department, StudentProfile
        
        department = get_object_or_404(Department, id=department_id)
        
        # Check if department has students
        student_count = StudentProfile.objects.filter(department=department.name).count()
        if student_count > 0:
            return JsonResponse({
                'error': f'Cannot delete department. It has {student_count} associated students.'
            }, status=400)
        
        # Check if department has admin profiles
        admin_count = AdminProfile.objects.filter(department=department.name).count()
        if admin_count > 0:
            return JsonResponse({
                'error': f'Cannot delete department. It has {admin_count} associated admin profiles.'
            }, status=400)
        
        department_name = department.name
        school_name = department.school.name if department.school else None
        
        department.delete()
        
        # Create audit log
        school_info = f' from {school_name}' if school_name else ''
        AuditLog.objects.create(
            user=request.user,
            action='department_delete',
            description=f'Deleted department: {department_name}{school_info}',
            target_model='Department',
            target_id=str(department_id)
        )
        
        return JsonResponse({'success': True, 'message': f'Department "{department_name}" deleted successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
