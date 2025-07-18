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

from .models import User, EmailVerification, PasswordReset
from .serializers import UserRegistrationSerializer, UserLoginSerializer, PasswordResetSerializer


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
    """Login page"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user:
            if not user.is_email_verified:
                messages.error(request, 'Please verify your email first')
                return render(request, 'authentication/login.html')
            
            login(request, user)
            if user.is_student:
                return redirect('students:dashboard')
            else:
                return redirect('admin_panel:dashboard')
        
        messages.error(request, 'Invalid credentials')
    
    return render(request, 'authentication/login.html')


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
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    return redirect('authentication:login_view')
