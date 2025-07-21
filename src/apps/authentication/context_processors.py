"""
Context processors for role-based Student Grievance Management System
"""

def role_context(request):
    """Context processor to add role-based information to all templates"""
    context = {
        'user_role': None,
        'user_role_display': None,
        'user_department': None,
        'user_profile': None,
        'can_access_admin': False,
        'can_access_superadmin': False,
        'role_permissions': []
    }
    
    if request.user.is_authenticated:
        user = request.user
        context.update({
            'user_role': user.role,
            'user_role_display': user.get_role_display(),
            'can_access_admin': user.is_admin,
            'can_access_superadmin': user.is_superadmin,
        })
        
        # Add profile and department information
        try:
            if user.role == 'student' and hasattr(user, 'student_profile'):
                context.update({
                    'user_profile': user.student_profile,
                    'user_department': user.student_profile.department,
                })
            elif user.role in ['admin', 'officer', 'superadmin'] and hasattr(user, 'admin_profile'):
                context.update({
                    'user_profile': user.admin_profile,
                    'user_department': user.admin_profile.department,
                })
        except Exception as e:
            # Handle cases where profile doesn't exist
            context['profile_error'] = str(e)
        
        # Add role permissions if available
        if hasattr(user, 'has_permission'):
            from apps.authentication.role_validator import RoleValidator
            context['role_permissions'] = RoleValidator.get_role_permissions(user.role)
    
    return context


def student_notifications(request):
    """Context processor to add student notifications to all templates"""
    if request.user.is_authenticated and request.user.is_student:
        try:
            from .views import get_student_notifications
            notifications = get_student_notifications(request.user)
            return {
                'student_notifications': notifications,
                'notifications_count': len(notifications)
            }
        except Exception:
            pass
    
    return {
        'student_notifications': [],
        'notifications_count': 0
    }
