from .views import get_student_notifications


def student_notifications(request):
    """Context processor to add student notifications to all templates"""
    if request.user.is_authenticated and request.user.is_student:
        notifications = get_student_notifications(request.user)
        return {
            'student_notifications': notifications,
            'notifications_count': len(notifications)
        }
    return {
        'student_notifications': [],
        'notifications_count': 0
    }
