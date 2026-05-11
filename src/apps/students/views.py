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

from .models import StudentProfile, AdminProfile, Department, UserActivity
from .serializers import StudentProfileSerializer, AdminProfileSerializer, DepartmentSerializer
from apps.authentication.models import User
from apps.grievances.models import Grievance, GrievanceComment, Feedback
from apps.notifications.models import ReadNotification
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_activity(request):
    """Get user login activity"""
    activities = UserActivity.objects.filter(user=request.user).order_by('-login_time')[:10]
    
    return Response([
        {
            'login_time': activity.login_time,
            'ip_address': activity.ip_address,
            'user_agent': activity.user_agent,
            'is_successful': activity.is_successful,
        }
        for activity in activities
    ])


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
    
    context = {
        'student_profile': student_profile,
        'grievance': grievance,
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
        student_response = request.POST.get('student_response', '').strip()
        
        if not student_response:
            messages.error(request, 'Response cannot be empty.')
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            url = reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})
            return HttpResponseRedirect(f"{url}#message-form")
        
        # Create the student response comment
        comment = GrievanceComment.objects.create(
            grievance=grievance,
            user=request.user,
            message=student_response,
            comment_type='comment',
            is_internal=False  # Student responses are always public
        )
        
        # Redirect with fragment to maintain scroll position near message form
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})
        return HttpResponseRedirect(f"{url}#message-form")
        
    except Exception as e:
        messages.error(request, f'Error sending response: {str(e)}')
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('students:grievance_detail', kwargs={'grievance_id': grievance_id})
        return HttpResponseRedirect(f"{url}#message-form")


@login_required
def submit_feedback_view(request, grievance_id):
    """Submit feedback for resolved grievance"""
    if not request.user.is_student:
        messages.error(request, 'Access denied.')
        return redirect('students:dashboard')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('students:grievance_detail', grievance_id=grievance_id)
    
    try:
        student_profile = request.user.student_profile
        grievance = get_object_or_404(Grievance, id=grievance_id, student=student_profile)
        
        # Check if grievance is resolved
        if grievance.status != 'resolved':
            messages.error(request, 'Feedback can only be submitted for resolved grievances.')
            return redirect('students:grievance_detail', grievance_id=grievance_id)
        
        # Check if feedback already exists
        if hasattr(grievance, 'feedback'):
            messages.warning(request, 'Feedback has already been submitted for this grievance.')
            return redirect('students:grievance_detail', grievance_id=grievance_id)
        
        rating = request.POST.get('rating')
        comments = request.POST.get('comments', '').strip()
        is_satisfied = request.POST.get('is_satisfied') == 'true'
        improvement_suggestions = request.POST.get('improvement_suggestions', '').strip()
        
        # Validate rating
        if not rating or not rating.isdigit() or int(rating) not in range(1, 6):
            messages.error(request, 'Rating must be between 1 and 5.')
            return redirect('students:grievance_detail', grievance_id=grievance_id)
        
        # Create feedback
        feedback = Feedback.objects.create(
            grievance=grievance,
            rating=int(rating),
            comments=comments,
            is_satisfied=is_satisfied,
            improvement_suggestions=improvement_suggestions
        )
        
        messages.success(request, 'Thank you for your feedback! It helps us improve our services.')
        return redirect('students:grievance_detail', grievance_id=grievance_id)
        
    except Exception as e:
        messages.error(request, f'Error submitting feedback: {str(e)}')
        return redirect('students:grievance_detail', grievance_id=grievance_id)


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
            
        if grievance.is_appealed:
            messages.warning(request, 'This grievance has already been appealed.')
            return redirect('students:grievance_detail', grievance_id=grievance_id)
            
        # Create Appeal
        Appeal.objects.create(
            grievance=grievance,
            student=student_profile,
            reason="Appealed by student from dashboard"
        )
        
        # Update Grievance
        grievance.is_appealed = True
        grievance.status = 'pending' # Re-open the grievance
        grievance.save()
        
        messages.success(request, 'Your appeal has been submitted successfully and the grievance has been re-opened.')
        return redirect('students:grievance_detail', grievance_id=grievance_id)
        
    except Exception as e:
        messages.error(request, f'Error submitting appeal: {str(e)}')
        return redirect('students:grievance_detail', grievance_id=grievance_id)
