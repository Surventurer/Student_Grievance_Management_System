from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class DepartmentAssignmentMiddleware(MiddlewareMixin):
    """
    Middleware to handle department assignment changes for HODs/admins
    """
    
    def process_request(self, request):
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            return None
            
        # Skip for superadmin users (they can access everything)
        if request.user.is_superadmin:
            return None
            
        # Skip for non-admin/officer users
        if request.user.role not in ['admin', 'officer']:
            return None
            
        # Skip for certain URLs that don't require department access
        skip_urls = [
            '/admin-panel/logout/',
            '/admin-panel/profile/',
            '/auth/',  # Skip all authentication URLs including logout
            '/authentication/',
            '/static/',
            '/media/',
            '/admin/',  # Skip Django admin
        ]
        
        if any(request.path.startswith(url) for url in skip_urls):
            return None
            
        # Check if user has a department assignment
        if not request.user.assigned_department:
            # User is admin/officer but has no department assigned
            # Allow them to logout or access basic auth pages, but redirect other pages to dashboard
            if (request.path != reverse('admin_panel:dashboard') and 
                not request.path.startswith('/auth/') and 
                not request.path.startswith('/authentication/')):
                messages.warning(
                    request, 
                    'You are not assigned to any department. Contact the Super Admin for department assignment.'
                )
                return redirect('admin_panel:dashboard')
        
        # Store current department in session to detect changes
        current_dept_id = request.user.assigned_department.id if request.user.assigned_department else None
        session_dept_id = request.session.get('user_department_id')
        
        if session_dept_id != current_dept_id:
            # Department assignment has changed
            request.session['user_department_id'] = current_dept_id
            
            if current_dept_id:
                department_name = request.user.assigned_department.name
                messages.info(
                    request,
                    f'Your department assignment has been updated. You can now access data for {department_name}.'
                )
            else:
                messages.warning(
                    request,
                    'Your department assignment has been removed. Contact the Super Admin for reassignment.'
                )
            
            # Redirect to dashboard to refresh data
            if request.path != reverse('admin_panel:dashboard'):
                return redirect('admin_panel:dashboard')
        
        return None
