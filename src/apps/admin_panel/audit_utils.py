"""
Audit logging decorators and utilities for tracking admin actions
"""
import json
import functools
from django.utils import timezone
from apps.grievances.models import AuditLog


def log_admin_action(action_type, target_model=None, description_template=None):
    """
    Decorator to automatically log admin actions
    
    Args:
        action_type: Type of action (create, update, delete, etc.)
        target_model: Model being affected (optional)
        description_template: Template for description (optional)
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Execute the original view
            response = view_func(request, *args, **kwargs)
            
            # Only log if user is admin and action was successful
            if (request.user.role in ['admin', 'superadmin'] and 
                hasattr(response, 'status_code') and 200 <= response.status_code < 400):
                
                try:
                    # Extract target ID from URL parameters if available
                    target_id = None
                    if 'grievance_id' in kwargs:
                        target_id = str(kwargs['grievance_id'])
                    elif 'student_id' in kwargs:
                        target_id = str(kwargs['student_id'])
                    elif 'category_id' in kwargs:
                        target_id = str(kwargs['category_id'])
                    
                    # Generate description
                    description = description_template or f"{action_type.title()} action performed"
                    if target_model and target_id:
                        description = f"{description} on {target_model} (ID: {target_id})"
                    
                    # Create audit log
                    AuditLog.objects.create(
                        user=request.user,
                        action=action_type,
                        target_model=target_model or 'Unknown',
                        target_id=target_id or 'N/A',
                        description=description,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                    )
                except Exception as e:
                    # Don't break the view if logging fails
                    print(f"Audit logging failed: {e}")
            
            return response
        return wrapper
    return decorator


def get_client_ip(request):
    """Get the real IP address of the client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_login_action(user, request, success=True):
    """Log login/logout actions"""
    try:
        if user.role in ['admin', 'superadmin']:
            AuditLog.objects.create(
                user=user,
                action='login' if success else 'login_failed',
                target_model='User',
                target_id=str(user.id),
                description=f"Admin {'login successful' if success else 'login failed'}",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
    except Exception as e:
        print(f"Login audit logging failed: {e}")


def log_logout_action(user, request):
    """Log logout actions"""
    try:
        if user.role in ['admin', 'superadmin']:
            AuditLog.objects.create(
                user=user,
                action='logout',
                target_model='User',
                target_id=str(user.id),
                description="Admin logout",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
    except Exception as e:
        print(f"Logout audit logging failed: {e}")


def log_custom_action(user, action, target_model, target_id, description, request):
    """Log custom admin actions manually"""
    try:
        if user.role in ['admin', 'superadmin']:
            AuditLog.objects.create(
                user=user,
                action=action,
                target_model=target_model,
                target_id=str(target_id),
                description=description,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
    except Exception as e:
        print(f"Custom audit logging failed: {e}")


class AuditLogger:
    """Context manager for audit logging"""
    
    def __init__(self, user, action, target_model, target_id, description, request):
        self.user = user
        self.action = action
        self.target_model = target_model
        self.target_id = target_id
        self.description = description
        self.request = request
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Only log if no exception occurred
        if exc_type is None:
            log_custom_action(
                self.user, self.action, self.target_model, 
                self.target_id, self.description, self.request
            )
