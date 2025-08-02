from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
import json
import random
import string
from datetime import timedelta

from .models import User, EmailVerification, PasswordReset, TemporaryRegistration, AdminLoginOTP
from .serializers import UserRegistrationSerializer, UserLoginSerializer, PasswordResetSerializer
from .forms import StudentRegistrationForm
from apps.students.models import Department, School
from apps.admin_panel.audit_utils import log_login_action, log_logout_action


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def generate_token():
    """Generate a random token for password reset"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=50))


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate OTP for email verification
        otp = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)
        
        EmailVerification.objects.create(
            user=user,
            otp=otp,
            expires_at=expires_at
        )
        
        # Send OTP via email
        send_mail(
            'Verify Your Email - Student Grievance System',
            f'Your OTP for email verification is: {otp}. Valid for 10 minutes.',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Registration successful. Please check your email for OTP verification.',
            'user_id': user.id
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    """Verify user email with OTP"""
    user_id = request.data.get('user_id')
    otp = request.data.get('otp')
    
    try:
        user = User.objects.get(id=user_id)
        verification = EmailVerification.objects.filter(
            user=user,
            otp=otp,
            is_used=False
        ).first()
        
        if not verification:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        
        if verification.is_expired:
            return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as used and activate user
        verification.is_used = True
        verification.save()
        
        user.is_email_verified = True
        user.save()
        
        return Response({'message': 'Email verified successfully'}, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Login user and return token"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(username=email, password=password)
        
        if user:
            if not user.is_email_verified:
                return Response({'error': 'Please verify your email first'}, status=status.HTTP_400_BAD_REQUEST)
            
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'role': user.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            }, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def logout_user(request):
    """Logout user and delete token"""
    try:
        token = Token.objects.get(user=request.user)
        token.delete()
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
    except Token.DoesNotExist:
        return Response({'error': 'Token not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """Send password reset link"""
    email = request.data.get('email')
    
    try:
        user = User.objects.get(email=email)
        
        # Generate reset token
        token = generate_token()
        expires_at = timezone.now() + timedelta(hours=1)
        
        PasswordReset.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # Send reset email
        reset_link = f"http://localhost:8000/reset-password/{token}"
        send_mail(
            'Password Reset - Student Grievance System',
            f'Click the link to reset your password: {reset_link}. Valid for 1 hour.',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        
        return Response({'message': 'Password reset link sent to your email'}, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({'error': 'User with this email does not exist'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request, token):
    """Reset password with token"""
    try:
        reset_request = PasswordReset.objects.get(token=token, is_used=False)
        
        if reset_request.is_expired:
            return Response({'error': 'Reset token has expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']
            
            user = reset_request.user
            user.set_password(new_password)
            user.save()
            
            reset_request.is_used = True
            reset_request.save()
            
            return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except PasswordReset.DoesNotExist:
        return Response({'error': 'Invalid or expired reset token'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def profile(request):
    """Get user profile"""
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'role': user.role,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_email_verified': user.is_email_verified,
        'created_at': user.created_at,
    }, status=status.HTTP_200_OK)


# Web views for frontend
def login_view(request):
    """Login page with OTP verification for admins"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        otp_code = request.POST.get('otp')
        
        # Rate limiting for login attempts
        if not otp_code:  # Only for initial login, not OTP verification
            login_attempts_key = f'login_attempts_{email}'
            login_attempts = request.session.get(login_attempts_key, 0)
            last_login_attempt_time = request.session.get(f'last_login_attempt_{email}')
            
            # Reset attempts if more than 5 minutes have passed
            if last_login_attempt_time:
                try:
                    last_attempt = timezone.datetime.fromisoformat(last_login_attempt_time)
                    if timezone.now() - last_attempt > timedelta(minutes=5):
                        login_attempts = 0
                        request.session.pop(login_attempts_key, None)
                        request.session.pop(f'last_login_attempt_{email}', None)
                except:
                    # If there's any error parsing the time, reset the attempts
                    login_attempts = 0
                    request.session.pop(login_attempts_key, None)
                    request.session.pop(f'last_login_attempt_{email}', None)
            
            # Check if too many attempts
            if login_attempts >= 5:
                messages.error(request, 'Too many failed login attempts. Please wait 5 minutes before trying again.')
                return render(request, 'authentication/login.html')
        
        # First step: Email and password validation
        if not otp_code:
            user = authenticate(request, username=email, password=password)
            if user:
                # Check if user account is deactivated
                if not user.is_active:
                    reason = user.deactivation_reason or "Your account has been deactivated by the administrator."
                    messages.error(request, f'Account Deactivated: {reason}')
                    return render(request, 'authentication/login.html', {'deactivation_reason': reason})
                
                if not user.is_email_verified:
                    messages.error(request, 'Please verify your email first')
                    return render(request, 'authentication/login.html')
                
                # For admin and superadmin users, require OTP
                if user.role in ['admin', 'superadmin']:
                    # Clear successful login attempts
                    login_attempts_key = f'login_attempts_{email}'
                    request.session.pop(login_attempts_key, None)
                    request.session.pop(f'last_login_attempt_{email}', None)
                    
                    # Generate and send OTP
                    otp = generate_otp()
                    expires_at = timezone.now() + timedelta(minutes=5)
                    
                    # Store user ID in session for OTP verification
                    request.session['admin_login_user_id'] = user.id
                    request.session['admin_login_email'] = user.email
                    
                    # Create OTP record
                    AdminLoginOTP.objects.create(
                        user=user,
                        otp=otp,
                        expires_at=expires_at,
                        session_key=request.session.session_key
                    )
                    
                    # Send OTP via email
                    try:
                        send_mail(
                            'Admin Login Verification - OTP',
                            f'Your OTP for admin login is: {otp}. This code will expire in 5 minutes.\n\nIf you did not attempt to login, please contact the system administrator immediately.',
                            settings.EMAIL_HOST_USER,
                            [user.email],
                            fail_silently=False,
                        )
                        
                        # For development: print OTP to console
                        print(f"🔑 OTP FOR {user.email}: {otp}")
                        
                        messages.success(request, f'OTP has been sent to your email. Please enter it below to complete login. [DEV: Check console for OTP]')
                        return render(request, 'authentication/login.html', {
                            'show_otp_field': True,
                            'email': email
                        })
                    except Exception as e:
                        # For development: show OTP in error message if email fails
                        print(f"🔑 EMAIL FAILED - OTP FOR {user.email}: {otp}")
                        messages.info(request, f'Email failed. For development, your OTP is: {otp}')
                        return render(request, 'authentication/login.html', {
                            'show_otp_field': True,
                            'email': email
                        })
                
                # For students, login directly to student dashboard
                elif user.role == 'student':
                    # Clear successful login attempts
                    login_attempts_key = f'login_attempts_{email}'
                    request.session.pop(login_attempts_key, None)
                    request.session.pop(f'last_login_attempt_{email}', None)
                    
                    # Ensure student has a profile
                    try:
                        student_profile = user.student_profile
                        login(request, user)
                        log_login_action(user, request, success=True)
                        return redirect('students:dashboard')
                    except:
                        messages.error(request, 'Student profile not found. Please contact administrator.')
                        return render(request, 'authentication/login.html')
                
                # For officers, login directly to admin dashboard 
                elif user.role == 'officer':
                    # Clear successful login attempts
                    login_attempts_key = f'login_attempts_{email}'
                    request.session.pop(login_attempts_key, None)
                    request.session.pop(f'last_login_attempt_{email}', None)
                    
                    # Ensure officer has an admin profile
                    try:
                        admin_profile = user.admin_profile
                        login(request, user)
                        log_login_action(user, request, success=True)
                        return redirect('admin_panel:dashboard')
                    except:
                        messages.error(request, 'Officer profile not found. Please contact administrator.')
                        return render(request, 'authentication/login.html')
                    
                # For other roles, redirect appropriately 
                else:
                    # Clear successful login attempts
                    login_attempts_key = f'login_attempts_{email}'
                    request.session.pop(login_attempts_key, None)
                    request.session.pop(f'last_login_attempt_{email}', None)
                    
                    login(request, user)
                    log_login_action(user, request, success=True)
                    return redirect('admin_panel:dashboard')
            else:
                # Check if user exists but is inactive (Django's authenticate() returns None for inactive users)
                try:
                    inactive_user = User.objects.get(email=email, is_active=False)
                    # Verify the password manually for inactive users
                    if inactive_user.check_password(password):
                        reason = inactive_user.deactivation_reason or "Your account has been deactivated by the administrator."
                        messages.error(request, f'Account Deactivated: {reason}')
                        return render(request, 'authentication/login.html', {'deactivation_reason': reason})
                except User.DoesNotExist:
                    pass  # User doesn't exist or is active but password is wrong
                
                # Increment failed login attempts
                login_attempts_key = f'login_attempts_{email}'
                login_attempts = request.session.get(login_attempts_key, 0)
                request.session[login_attempts_key] = login_attempts + 1
                request.session[f'last_login_attempt_{email}'] = timezone.now().isoformat()
                
                messages.error(request, 'Invalid email or password')
        
        # Second step: OTP verification for admin users
        else:
            user_id = request.session.get('admin_login_user_id')
            if not user_id:
                messages.error(request, 'Session expired. Please login again.')
                return redirect('authentication:login_view')
            
            try:
                user = User.objects.get(id=user_id)
                
                # Check for too many failed attempts using session-based tracking
                failed_attempts_key = f'failed_otp_attempts_{user_id}'
                failed_attempts = request.session.get(failed_attempts_key, 0)
                last_attempt_time = request.session.get(f'last_failed_attempt_{user_id}')
                
                # Reset attempts if more than 5 minutes have passed
                if last_attempt_time:
                    try:
                        last_attempt = timezone.datetime.fromisoformat(last_attempt_time)
                        if timezone.now() - last_attempt > timedelta(minutes=5):
                            failed_attempts = 0
                            request.session.pop(failed_attempts_key, None)
                            request.session.pop(f'last_failed_attempt_{user_id}', None)
                    except:
                        # If there's any error parsing the time, reset the attempts
                        failed_attempts = 0
                        request.session.pop(failed_attempts_key, None)
                        request.session.pop(f'last_failed_attempt_{user_id}', None)
                
                if failed_attempts >= 3:
                    messages.error(request, 'Too many failed attempts. Please wait 5 minutes before trying again.')
                    # Clear session data
                    request.session.pop('admin_login_user_id', None)
                    request.session.pop('admin_login_email', None)
                    return redirect('authentication:login_view')
                
                otp_record = AdminLoginOTP.objects.filter(
                    user=user,
                    otp=otp_code,
                    is_used=False
                ).order_by('-created_at').first()
                
                if not otp_record:
                    # Increment failed attempts
                    request.session[failed_attempts_key] = failed_attempts + 1
                    request.session[f'last_failed_attempt_{user_id}'] = timezone.now().isoformat()
                    
                    messages.error(request, 'Invalid OTP. Please try again.')
                    return render(request, 'authentication/login.html', {
                        'show_otp_field': True,
                        'email': request.session.get('admin_login_email')
                    })
                
                if otp_record.is_expired:
                    messages.error(request, 'OTP has expired. Please login again.')
                    # Clear session data
                    request.session.pop('admin_login_user_id', None)
                    request.session.pop('admin_login_email', None)
                    # Clear failed attempts since this is an expiry, not a failure
                    request.session.pop(failed_attempts_key, None)
                    request.session.pop(f'last_failed_attempt_{user_id}', None)
                    return redirect('authentication:login_view')
                
                # OTP is valid, complete login
                otp_record.is_used = True
                otp_record.save()
                
                # Clear failed attempts on successful login
                request.session.pop(failed_attempts_key, None)
                request.session.pop(f'last_failed_attempt_{user_id}', None)
                
                # Clear all unused OTPs for this user
                AdminLoginOTP.objects.filter(
                    user=user,
                    is_used=False
                ).update(is_used=True)
                
                # Clear session data
                request.session.pop('admin_login_user_id', None)
                request.session.pop('admin_login_email', None)
                
                login(request, user)
                
                # Log successful admin login
                log_login_action(user, request, success=True)
                
                messages.success(request, 'Login successful!')
                return redirect('admin_panel:dashboard')
                
            except User.DoesNotExist:
                messages.error(request, 'Invalid session. Please login again.')
                return redirect('authentication:login_view')
    
    return render(request, 'authentication/login.html')


def resend_admin_otp(request):
    """Resend OTP for admin login"""
    if request.method == 'POST':
        user_id = request.session.get('admin_login_user_id')
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'Session expired. Please login again.'
            })
        
        try:
            user = User.objects.get(id=user_id)
            
            # Check if there's a recent OTP request (within last 1 minute)
            recent_otp = AdminLoginOTP.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timedelta(minutes=1),
                is_used=False
            ).first()
            
            if recent_otp:
                return JsonResponse({
                    'success': False,
                    'message': 'Please wait 1 minute before requesting a new OTP.'
                })
            
            # Generate new OTP
            otp = generate_otp()
            expires_at = timezone.now() + timedelta(minutes=5)
            
            # Invalidate previous unused OTPs
            AdminLoginOTP.objects.filter(
                user=user,
                is_used=False
            ).update(is_used=True)
            
            # Create new OTP record
            AdminLoginOTP.objects.create(
                user=user,
                otp=otp,
                expires_at=expires_at,
                session_key=request.session.session_key
            )
            
            # Send new OTP via email
            try:
                send_mail(
                    'Admin Login Verification - New OTP',
                    f'Your new OTP for admin login is: {otp}. This code will expire in 5 minutes.\n\nIf you did not attempt to login, please contact the system administrator immediately.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'New OTP has been sent to your email.'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': 'Failed to send OTP. Please try again.'
                })
                
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid session. Please login again.'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


def register_view(request):
    """Registration page"""
    if request.method == 'POST':
        # Handle registration form
        pass
    
    return render(request, 'authentication/register.html')


@login_required
def logout_view(request):
    """Logout user"""
    if request.user.is_authenticated:
        # Log admin logout before logging out
        log_logout_action(request.user, request)
        
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    return redirect('authentication:login_view')


def forgot_password_view(request):
    """Web view for forgot password form"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            # Check if there's already a recent reset request (within last 5 minutes)
            recent_reset = PasswordReset.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timedelta(minutes=5),
                is_used=False
            ).first()
            
            if recent_reset:
                messages.warning(request, 'A password reset link was already sent recently. Please check your email or wait 5 minutes before requesting again.')
                return render(request, 'authentication/forgot_password.html')
            
            # Generate reset token
            token = generate_token()
            expires_at = timezone.now() + timedelta(hours=1)
            
            PasswordReset.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # Send reset email
            try:
                from django.urls import reverse
                reset_url = reverse('authentication:reset_password_view', kwargs={'token': token})
                reset_link = f"http://127.0.0.1:8000{reset_url}"
                
                email_subject = 'Password Reset - Student Grievance System'
                email_message = f"""Hello {user.email},

You requested a password reset for your Student Grievance Management System account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, please ignore this email.

Best regards,
Student Grievance Management System Team"""
                
                send_mail(
                    email_subject,
                    email_message,
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
                
                messages.success(request, 'Password reset link has been sent to your email.')
                return redirect('authentication:forgot_password_view')
            except Exception as e:
                # Delete the reset token if email sending fails
                PasswordReset.objects.filter(token=token).delete()
                messages.error(request, 'Error sending reset email. Please try again.')
                return render(request, 'authentication/forgot_password.html')
            
        except User.DoesNotExist:
            messages.error(request, 'User with this email does not exist.')
        except Exception as e:
            messages.error(request, 'Error sending reset email. Please try again.')
    
    return render(request, 'authentication/forgot_password.html')


def reset_password_view(request, token):
    """Web view for password reset form"""
    try:
        reset_request = PasswordReset.objects.get(token=token, is_used=False)
        
        if reset_request.is_expired:
            messages.error(request, 'Reset token has expired. Please request a new one.')
            return redirect('authentication:forgot_password_view')
        
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not new_password or len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters long.')
            elif new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
            else:
                # Reset password
                user = reset_request.user
                user.set_password(new_password)
                user.save()
                
                reset_request.is_used = True
                reset_request.save()
                
                messages.success(request, 'Password reset successfully. You can now login with your new password.')
                return redirect('authentication:login')
        
        return render(request, 'authentication/reset_password.html', {'token': token})
        
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid or expired reset token.')
        return redirect('authentication:forgot_password_view')


def student_registration(request):
    """Student Registration View"""
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Save to temporary registration (not actual database)
                temp_registration = form.save()
                
                # Send OTP via email
                try:
                    send_mail(
                        'Verify Your Email - Student Grievance System',
                        f'Dear {temp_registration.name},\n\nYour OTP for email verification is: {temp_registration.otp}\n\nThis OTP is valid for 10 minutes.\n\nThank you!',
                        settings.EMAIL_HOST_USER,
                        [temp_registration.email],
                        fail_silently=False,
                    )
                    messages.success(request, f'Registration initiated! Please check your email ({temp_registration.email}) for verification OTP. Your Student ID is: {temp_registration.student_id}')
                except Exception as email_error:
                    messages.warning(request, f'Registration saved! However, we could not send the verification email. Your Student ID is: {temp_registration.student_id}. Please contact support.')
                
                # Redirect to email verification page
                return redirect('authentication:verify_email_view')
                    
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'authentication/student_registration.html', {'form': form})


def load_departments(request):
    """AJAX view to load departments based on selected school"""
    school_id = request.GET.get('school_id')
    
    try:
        if school_id:
            # Get the school object first to verify it exists
            try:
                school = School.objects.get(id=school_id)
            except School.DoesNotExist:
                return JsonResponse({'departments': [], 'error': 'School not found'})
            
            # Get departments for the school
            departments = Department.objects.filter(school=school_id).order_by('name')
            
            # Create response data
            department_data = [{'id': dept.id, 'name': dept.name} for dept in departments]
            
            return JsonResponse({
                'departments': department_data, 
                'school': {'id': school.id, 'name': school.name},
                'count': departments.count()
            })
        else:
            return JsonResponse({'departments': [], 'error': 'No school ID provided'})
            
    except Exception as e:
        return JsonResponse({'departments': [], 'error': 'Internal server error'}, status=500)


def verify_email_view(request):
    """Web view for email verification"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')  # Changed from registration_id to student_id
        otp = request.POST.get('otp')
        
        try:
            # Look for temporary registration by student_id instead of id
            temp_registration = TemporaryRegistration.objects.get(student_id=student_id, is_verified=False)
            
            if temp_registration.otp != otp:
                messages.error(request, 'Invalid OTP. Please check and try again.')
                return render(request, 'authentication/verify_email.html')
            
            if temp_registration.is_expired:
                messages.error(request, 'OTP has expired. Please register again.')
                temp_registration.delete()  # Clean up expired registration
                return render(request, 'authentication/verify_email.html')
            
            # Create actual user and student profile
            try:
                user, student_profile = temp_registration.create_actual_user()
                
                # Mark temp registration as verified and delete it
                temp_registration.is_verified = True
                temp_registration.delete()  # Clean up after successful verification
                
                messages.success(request, f'Email verified successfully! Welcome {student_profile.name}! You can now log in.')
                return redirect('authentication:login_view')
                
            except Exception as creation_error:
                messages.error(request, 'An error occurred while creating your account. Please try again.')
            
        except TemporaryRegistration.DoesNotExist:
            messages.error(request, 'Registration not found or already verified. Please check your Student ID.')
        except Exception as e:
            messages.error(request, 'An error occurred. Please try again.')
    
    return render(request, 'authentication/verify_email.html')


def verify_student_email_view(request):
    """View for students to verify their email using Student ID and OTP
    
    This view handles two scenarios:
    1. Students with temporary registration data (didn't verify after initial registration)
    2. Students with permanent accounts who need email verification
    """
    if request.method == 'POST':
        action = request.POST.get('action', 'verify')
        student_id = request.POST.get('student_id')
        email = request.POST.get('email')
        otp = request.POST.get('otp')
        
        if action == 'send_otp':
            # Step 1: Send OTP for students with temporary registration
            if not student_id or not email:
                messages.error(request, 'Please provide both Student ID and Email.')
                return render(request, 'authentication/verify_student_email.html')
            
            try:
                # First check if there's temporary registration data
                temp_registration = TemporaryRegistration.objects.get(
                    student_id=student_id, 
                    email=email, 
                    is_verified=False
                )
                
                # Generate new OTP and update expiry
                from datetime import timedelta
                from django.utils import timezone
                
                new_otp = generate_otp()
                temp_registration.otp = new_otp
                temp_registration.expires_at = timezone.now() + timedelta(minutes=30)
                temp_registration.save()
                
                # Send OTP via email
                try:
                    send_mail(
                        subject='Email Verification OTP - Student Grievance System',
                        message=f'''
Dear {temp_registration.name},

Here is your email verification OTP:

Student ID: {student_id}
OTP: {new_otp}

This OTP will expire in 30 minutes.

Please use this OTP to complete your account verification.

Best regards,
Student Grievance Management System
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False
                    )
                    messages.success(request, f'Verification OTP sent to {email}. Please check your email and enter the OTP below.')
                    # Store data in session for the next step
                    request.session['verification_student_id'] = student_id
                    request.session['verification_email'] = email
                    request.session['verification_type'] = 'temporary'
                    
                except Exception as email_error:
                    messages.error(request, 'Error sending email. Please try again later.')
                    
            except TemporaryRegistration.DoesNotExist:
                # Check if it's an existing permanent account
                try:
                    from apps.students.models import StudentProfile
                    student_profile = StudentProfile.objects.select_related('user').get(student_id=student_id)
                    
                    if student_profile.user.email != email:
                        messages.error(request, 'Student ID and email do not match our records.')
                        return render(request, 'authentication/verify_student_email.html')
                    
                    if student_profile.user.is_email_verified:
                        messages.info(request, 'Your email is already verified! You can log in.')
                        return redirect('authentication:login_view')
                    
                    # Generate OTP for existing user
                    from datetime import timedelta
                    from django.utils import timezone
                    
                    new_otp = generate_otp()
                    expires_at = timezone.now() + timedelta(minutes=30)
                    
                    # Mark old OTPs as used
                    EmailVerification.objects.filter(user=student_profile.user, is_used=False).update(is_used=True)
                    
                    # Create new verification
                    EmailVerification.objects.create(
                        user=student_profile.user,
                        otp=new_otp,
                        expires_at=expires_at
                    )
                    
                    # Send email
                    try:
                        send_mail(
                            subject='Email Verification OTP - Student Grievance System',
                            message=f'''
Dear {student_profile.name},

Here is your email verification OTP:

Student ID: {student_id}
OTP: {new_otp}

This OTP will expire in 30 minutes.

Best regards,
Student Grievance Management System
                            ''',
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False
                        )
                        messages.success(request, f'Verification OTP sent to {email}. Please check your email and enter the OTP below.')
                        # Store data in session for the next step
                        request.session['verification_student_id'] = student_id
                        request.session['verification_email'] = email
                        request.session['verification_type'] = 'permanent'
                        
                    except Exception as email_error:
                        messages.error(request, 'Error sending email. Please try again later.')
                        
                except StudentProfile.DoesNotExist:
                    messages.error(request, 'No registration found with this Student ID and email. Please check your details or register first.')
                    
            except Exception as e:
                messages.error(request, 'An error occurred. Please try again.')
                
        elif action == 'verify':
            # Step 2: Verify OTP and complete registration/verification
            if not otp:
                messages.error(request, 'Please provide the OTP.')
                return render(request, 'authentication/verify_student_email.html')
            
            # Get verification details from session
            session_student_id = request.session.get('verification_student_id')
            session_email = request.session.get('verification_email')
            verification_type = request.session.get('verification_type')
            
            if not session_student_id or not session_email:
                messages.error(request, 'Session expired. Please request a new OTP.')
                return render(request, 'authentication/verify_student_email.html')
            
            try:
                if verification_type == 'temporary':
                    # Handle temporary registration verification
                    temp_registration = TemporaryRegistration.objects.get(
                        student_id=session_student_id,
                        email=session_email,
                        is_verified=False
                    )
                    
                    if temp_registration.otp != otp:
                        messages.error(request, 'Invalid OTP. Please check and try again.')
                        return render(request, 'authentication/verify_student_email.html')
                    
                    if temp_registration.is_expired:
                        messages.error(request, 'OTP has expired. Please request a new OTP.')
                        return render(request, 'authentication/verify_student_email.html')
                    
                    # Create actual user and student profile
                    try:
                        user, student_profile = temp_registration.create_actual_user()
                        
                        # Mark temp registration as verified and delete it
                        temp_registration.is_verified = True
                        temp_registration.delete()  # Clean up after successful verification
                        
                        # Clear session data
                        request.session.pop('verification_student_id', None)
                        request.session.pop('verification_email', None)
                        request.session.pop('verification_type', None)
                        
                        messages.success(request, f'Account created successfully! Welcome {student_profile.name}! You can now log in.')
                        return redirect('authentication:login_view')
                        
                    except Exception as creation_error:
                        messages.error(request, 'An error occurred while creating your account. Please try again.')
                        
                elif verification_type == 'permanent':
                    # Handle existing user email verification
                    from apps.students.models import StudentProfile
                    student_profile = StudentProfile.objects.select_related('user').get(student_id=session_student_id)
                    user = student_profile.user
                    
                    # Find valid OTP
                    verification = EmailVerification.objects.filter(
                        user=user,
                        otp=otp,
                        is_used=False
                    ).order_by('-created_at').first()
                    
                    if not verification:
                        messages.error(request, 'Invalid OTP. Please check and try again.')
                        return render(request, 'authentication/verify_student_email.html')
                    
                    if verification.is_expired:
                        messages.error(request, 'OTP has expired. Please request a new OTP.')
                        return render(request, 'authentication/verify_student_email.html')
                    
                    # Mark OTP as used and verify email
                    verification.is_used = True
                    verification.save()
                    
                    user.is_email_verified = True
                    user.save()
                    
                    # Clear session data
                    request.session.pop('verification_student_id', None)
                    request.session.pop('verification_email', None)
                    request.session.pop('verification_type', None)
                    
                    messages.success(request, f'Email verified successfully! Welcome {student_profile.name}! You can now log in.')
                    return redirect('authentication:login_view')
                    
                else:
                    messages.error(request, 'Invalid verification type. Please start over.')
                    
            except (TemporaryRegistration.DoesNotExist, StudentProfile.DoesNotExist):
                messages.error(request, 'Registration not found. Please request a new OTP.')
            except Exception as e:
                messages.error(request, 'An error occurred. Please try again.')
    
    return render(request, 'authentication/verify_student_email.html')


def resend_verification_otp_view(request):
    """Resend verification OTP for a student"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        
        if not student_id:
            messages.error(request, 'Please provide Student ID.')
            return render(request, 'authentication/verify_student_email.html')
        
        try:
            from apps.students.models import StudentProfile
            from datetime import timedelta
            from django.utils import timezone
            from django.core.mail import send_mail
            from django.conf import settings
            
            student_profile = StudentProfile.objects.select_related('user').get(student_id=student_id)
            user = student_profile.user
            
            if user.is_email_verified:
                messages.info(request, 'Your email is already verified!')
                return redirect('authentication:login_view')
            
            # Generate new OTP
            otp = generate_otp()
            expires_at = timezone.now() + timedelta(minutes=30)
            
            # Mark old OTPs as used
            EmailVerification.objects.filter(user=user, is_used=False).update(is_used=True)
            
            # Create new verification
            EmailVerification.objects.create(
                user=user,
                otp=otp,
                expires_at=expires_at
            )
            
            # Send email
            try:
                send_mail(
                    subject='New Email Verification OTP - Student Grievance System',
                    message=f'''
Dear {student_profile.name},

Here is your new email verification OTP:

Student ID: {student_id}
New OTP: {otp}

This OTP will expire in 30 minutes.

Best regards,
Student Grievance Management System
                    ''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True
                )
                messages.success(request, f'New verification OTP sent to {user.email}')
            except Exception as e:
                messages.error(request, 'Error sending email. Please try again later.')
                
        except StudentProfile.DoesNotExist:
            messages.error(request, 'Student ID not found.')
        except Exception as e:
            messages.error(request, 'An error occurred. Please try again.')
    
    return render(request, 'authentication/verify_student_email.html')


def clear_verification_session(request):
    """Clear verification session data and redirect to verify student email page"""
    request.session.pop('verification_student_id', None)
    request.session.pop('verification_email', None)
    request.session.pop('verification_type', None)
    messages.info(request, 'Session cleared. You can start the verification process again.')
    return redirect('authentication:verify_student_email')
