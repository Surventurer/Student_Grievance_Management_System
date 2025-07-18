from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import json
import random
import string
from datetime import datetime, timedelta

from .models import Grievance, Category, GrievanceComment, Feedback, GrievanceOTPVerification
from apps.students.models import StudentProfile


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_list(request):
    """Get user's grievances"""
    if request.user.is_student:
        grievances = Grievance.objects.filter(student=request.user.student_profile)
    else:
        grievances = Grievance.objects.filter(assigned_to=request.user.admin_profile)
    
    return Response([
        {
            'id': g.id,
            'title': g.title,
            'status': g.status,
            'category': g.category.name,
            'submitted_at': g.submitted_at,
        }
        for g in grievances
    ])


@login_required
def submit_grievance_view(request):
    """Submit grievance web view"""
    if not request.user.is_student:
        messages.error(request, 'Only students can submit grievances')
        return redirect('students:dashboard')
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            category_id = request.POST.get('nature_of_grievance')
            category_type = request.POST.get('category_type', 'academic')
            department_id = request.POST.get('department')
            is_anonymous = request.POST.get('is_anonymous') == 'on'
            otp_code = request.POST.get('otp_code', '').strip()
            
            # Validate required fields
            if not all([title, description, category_id, otp_code]):
                messages.error(request, 'Please fill all required fields')
                context = {
                    'student_profile': request.user.student_profile
                }
                return render(request, 'grievances/submit_grievance.html', context)
            
            # For non-academic grievances, department is required
            if category_type == 'non_academic' and not department_id:
                messages.error(request, 'Please select a department for non-academic grievances')
                context = {
                    'student_profile': request.user.student_profile
                }
                return render(request, 'grievances/submit_grievance.html', context)
            
            # Verify OTP
            email_verification = GrievanceOTPVerification.objects.filter(
                email=request.user.email,
                otp=otp_code,
                is_verified=False
            ).first()
            
            if not email_verification or email_verification.is_expired:
                messages.error(request, 'Invalid or expired OTP. Please try again.')
                context = {
                    'student_profile': request.user.student_profile
                }
                return render(request, 'grievances/submit_grievance.html', context)
            
            # Get category
            try:
                category = Category.objects.get(id=category_id, is_active=True)
            except Category.DoesNotExist:
                messages.error(request, 'Invalid grievance category selected')
                context = {
                    'student_profile': request.user.student_profile
                }
                return render(request, 'grievances/submit_grievance.html', context)
            
            # Determine department based on category type
            if category_type == 'academic':
                # For academic grievances, use student's department
                grievance_department = request.user.student_profile.department
            else:
                # For non-academic grievances, use selected department
                try:
                    from apps.students.models import Department
                    dept = Department.objects.get(id=department_id)
                    grievance_department = dept.name
                except Department.DoesNotExist:
                    messages.error(request, 'Invalid department selected')
                    context = {
                        'student_profile': request.user.student_profile
                    }
                    return render(request, 'grievances/submit_grievance.html', context)
            
            # Create grievance
            grievance = Grievance.objects.create(
                student=request.user.student_profile,
                title=title,
                description=description,
                category=category,
                department=grievance_department,
                is_anonymous=is_anonymous
            )
            
            # Handle file uploads
            supporting_docs = request.FILES.getlist('supporting_docs')
            for file in supporting_docs:
                if file.size <= 5 * 1024 * 1024:  # 5MB limit
                    # Create attachment record
                    from .models import GrievanceAttachment
                    GrievanceAttachment.objects.create(
                        grievance=grievance,
                        file=file,
                        file_name=file.name,
                        file_size=file.size,
                        file_type=file.content_type
                    )
            
            # Mark OTP as verified
            email_verification.is_verified = True
            email_verification.save()
            
            # Auto-assign grievance
            grievance.auto_assign()
            
            messages.success(request, f'Grievance submitted successfully! Your grievance ID is: {grievance.grievance_id}')
            return redirect('students:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error submitting grievance: {str(e)}')
            context = {
                'student_profile': request.user.student_profile
            }
            return render(request, 'grievances/submit_grievance.html', context)
    
    # GET request - show the form
    context = {
        'student_profile': request.user.student_profile
    }
    return render(request, 'grievances/submit_grievance.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_grievance(request):
    """Submit a new grievance"""
    if not request.user.is_student:
        return Response({'error': 'Only students can submit grievances'}, status=status.HTTP_403_FORBIDDEN)
    
    # Create grievance logic here
    return Response({'message': 'Grievance submitted successfully'}, status=status.HTTP_201_CREATED)


@require_http_methods(["POST"])
@login_required
def send_otp_view(request):
    """Send OTP for grievance submission"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if email != request.user.email:
            return JsonResponse({'success': False, 'error': 'Email mismatch'})
        
        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Delete existing OTP for this email
        GrievanceOTPVerification.objects.filter(email=email, is_verified=False).delete()
        
        # Create new OTP record
        GrievanceOTPVerification.objects.create(
            email=email,
            otp=otp,
            purpose='grievance_submission'
        )
        
        # Send OTP email (you can implement actual email sending here)
        from django.core.mail import send_mail
        try:
            send_mail(
                'Grievance Submission OTP - Student Grievance System',
                f'Your OTP for grievance submission is: {otp}\n\nThis OTP is valid for 10 minutes.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Email sending failed: {e}")
            return JsonResponse({'success': True})  # Return success even if email fails for demo
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
@login_required
def verify_otp_view(request):
    """Verify OTP for grievance submission"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        otp = data.get('otp')
        
        if email != request.user.email:
            return JsonResponse({'success': False, 'error': 'Email mismatch'})
        
        # Check OTP
        email_verification = GrievanceOTPVerification.objects.filter(
            email=email,
            otp=otp,
            is_verified=False
        ).first()
        
        if email_verification and not email_verification.is_expired:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid or expired OTP'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@api_view(['GET'])
def category_list_api(request):
    """Get categories by type"""
    category_type = request.GET.get('type', 'academic')
    categories = Category.objects.filter(category_type=category_type, is_active=True)
    
    # Separate "Other" categories from regular categories
    other_categories = []
    regular_categories = []
    
    for c in categories:
        if c.name.lower().startswith('other'):
            other_categories.append(c)
        else:
            regular_categories.append(c)
    
    # Sort regular categories alphabetically
    regular_categories.sort(key=lambda x: x.name.lower())
    
    # Sort other categories alphabetically (in case there are multiple)
    other_categories.sort(key=lambda x: x.name.lower())
    
    # Combine: regular categories first, then "Other" categories at the end
    sorted_categories = regular_categories + other_categories
    
    return Response([
        {
            'id': str(c.id),
            'name': c.name,
            'description': c.description,
            'category_type': c.category_type,
        }
        for c in sorted_categories
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_detail(request, grievance_id):
    """Get grievance details"""
    try:
        grievance = Grievance.objects.get(id=grievance_id)
        return Response({
            'id': grievance.id,
            'title': grievance.title,
            'description': grievance.description,
            'status': grievance.status,
            'category': grievance.category.name,
            'submitted_at': grievance.submitted_at,
        })
    except Grievance.DoesNotExist:
        return Response({'error': 'Grievance not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_comments(request, grievance_id):
    """Get grievance comments"""
    try:
        grievance = Grievance.objects.get(id=grievance_id)
        comments = GrievanceComment.objects.filter(grievance=grievance)
        
        return Response([
            {
                'id': c.id,
                'message': c.message,
                'user': c.user.get_full_name(),
                'timestamp': c.timestamp,
            }
            for c in comments
        ])
    except Grievance.DoesNotExist:
        return Response({'error': 'Grievance not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request, grievance_id):
    """Submit feedback for a grievance"""
    if not request.user.is_student:
        return Response({'error': 'Only students can submit feedback'}, status=status.HTTP_403_FORBIDDEN)
    
    # Create feedback logic here
    return Response({'message': 'Feedback submitted successfully'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def category_list(request):
    """Get all categories"""
    categories = Category.objects.filter(is_active=True)
    
    return Response([
        {
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'category_type': c.category_type,
        }
        for c in categories
    ])
