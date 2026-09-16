from apps.notifications.models import Notification

def general_notifications(request):
    """Context processor to add general notifications to all templates"""
    if request.user.is_authenticated:
        # Get up to 25 unread notifications for the scrolling notification tray
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:25]
        
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return {
            'general_notifications': notifications,
            'general_notifications_count': unread_count
        }
    return {
        'general_notifications': [],
        'general_notifications_count': 0
    }
