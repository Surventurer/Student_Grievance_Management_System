from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_notification(request):
    """Send notification API"""
    return Response({'message': 'Notification sent'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """Get notification list API"""
    return Response({'notifications': []}, status=status.HTTP_200_OK)
