from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_notification(request):
    """Send notification API"""
    return Response({'message': 'Notification sent'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """Get unread notifications for the current user"""
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')

    return Response({
        'notifications': [
            {
                'id': str(notification.id),
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'related_link': notification.related_link,
                'created_at': notification.created_at,
            }
            for notification in notifications
        ],
        'count': notifications.count(),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return Response({'success': True}, status=status.HTTP_200_OK)


@login_required
def notification_list_view(request):
    """Web view to display all notifications for the current user"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'unread_count': notifications.filter(is_read=False).count(),
        'total_count': notifications.count(),
    }
    
    return render(request, 'notifications/notification_list.html', context)
