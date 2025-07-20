from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def superadmin_required(view_func):
    """Decorator to require superadmin role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if not request.user.is_superadmin:
            messages.error(request, 'Access denied - Super Admin privileges required')
            return redirect('authentication:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """Decorator to require admin role (includes superadmin)"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if not request.user.is_admin:
            messages.error(request, 'Access denied - Admin privileges required')
            return redirect('authentication:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def dept_admin_required(view_func):
    """Decorator to require department admin role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if not (request.user.role == 'admin' or request.user.is_superadmin):  # Use direct role check
            messages.error(request, 'Access denied - Department Admin privileges required')
            return redirect('authentication:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def officer_required(view_func):
    """Decorator to require officer role (includes higher roles)"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if not request.user.is_admin:  # admin includes superadmin, admin, officer
            messages.error(request, 'Access denied - Officer privileges required')
            return redirect('authentication:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def student_required(view_func):
    """Decorator to require student role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        if not request.user.is_student:
            messages.error(request, 'Access denied - Student account required')
            return redirect('authentication:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def permission_required(permission):
    """Decorator to check specific permissions"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('authentication:login')
            
            if not request.user.has_permission(permission):
                messages.error(request, f'Access denied - {permission} permission required')
                return redirect('authentication:login')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# API decorators for JSON responses
def api_superadmin_required(view_func):
    """API decorator to require superadmin role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        if not request.user.is_superadmin:
            return JsonResponse({'error': 'Super Admin privileges required'}, status=403)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def api_admin_required(view_func):
    """API decorator to require admin role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        if not request.user.is_admin:
            return JsonResponse({'error': 'Admin privileges required'}, status=403)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def api_permission_required(permission):
    """API decorator to check specific permissions"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            if not request.user.has_permission(permission):
                return JsonResponse({'error': f'{permission} permission required'}, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
