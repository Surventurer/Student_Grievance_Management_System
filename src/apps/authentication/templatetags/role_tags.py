"""
Template tags for role-based Student Grievance Management System
"""
from django import template
from apps.authentication.role_validator import RoleValidator

register = template.Library()


@register.simple_tag
def user_can_perform(user, action):
    """Template tag to check if user can perform an action"""
    return RoleValidator.can_user_perform_action(user, action)


@register.simple_tag
def user_has_role(user, role):
    """Template tag to check if user has a specific role"""
    if not user or not hasattr(user, 'role'):
        return False
    return user.role == role


@register.simple_tag
def user_has_any_role(user, roles):
    """Template tag to check if user has any of the specified roles"""
    if not user or not hasattr(user, 'role'):
        return False
    if isinstance(roles, str):
        roles = roles.split(',')
    return user.role in [role.strip() for role in roles]


@register.inclusion_tag('includes/role_badge.html')
def role_badge(user, size='sm'):
    """Template tag to display role badge"""
    if not user or not hasattr(user, 'role'):
        return {'role': None, 'size': size}
    
    role_colors = {
        'superadmin': 'danger',
        'admin': 'warning', 
        'officer': 'info',
        'student': 'success'
    }
    
    return {
        'role': user.role,
        'role_display': user.get_role_display() if hasattr(user, 'get_role_display') else user.role.title(),
        'color': role_colors.get(user.role, 'secondary'),
        'size': size
    }


@register.filter
def role_icon(role):
    """Template filter to get icon for a role"""
    icons = {
        'superadmin': 'fas fa-crown',
        'admin': 'fas fa-user-shield', 
        'officer': 'fas fa-clipboard-check',
        'student': 'fas fa-user-graduate'
    }
    return icons.get(role, 'fas fa-user')


@register.filter
def role_color(role):
    """Template filter to get color class for a role"""
    colors = {
        'superadmin': 'text-danger',
        'admin': 'text-warning',
        'officer': 'text-info', 
        'student': 'text-success'
    }
    return colors.get(role, 'text-secondary')


@register.simple_tag
def get_accessible_departments(user):
    """Get departments accessible to a user"""
    return RoleValidator.get_accessible_departments(user)


@register.simple_tag
def format_role_access(user):
    """Format role access description for UI"""
    if not user or not hasattr(user, 'role'):
        return "No access"
    
    access_map = {
        'superadmin': "Full system access - All departments, users, and settings",
        'admin': f"Department access - Manage {getattr(user.admin_profile, 'department', 'assigned')} department",
        'officer': f"Limited access - Handle assigned grievances in {getattr(user.admin_profile, 'department', 'assigned')} department", 
        'student': "Student access - Submit and track own grievances"
    }
    
    return access_map.get(user.role, "Limited access")
