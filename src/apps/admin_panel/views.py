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
    """Enhanced Student list view with search, filtering, and pagination"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
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
def student_detail_view(request, student_id):
    """Student detail view"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied')
        return redirect('authentication:login')
    
    try:
        student = StudentProfile.objects.select_related('user').get(id=student_id)
        
        # Get student's grievances
        grievances = Grievance.objects.filter(student=student).select_related('category').order_by('-submitted_at')
        
        # Get statistics
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
