from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Grievance, Category, GrievanceComment, Feedback


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_list(request):
    """Get user's grievances"""
    if request.user.is_student:
        grievances = Grievance.objects.filter(student=request.user.student_profile)
    else:
        grievances = Grievance.objects.filter(assigned_to=request.user.admin_profile)
    
    return Response([
        {
            'id': g.id,
            'title': g.title,
            'status': g.status,
            'category': g.category.name,
            'submitted_at': g.submitted_at,
        }
        for g in grievances
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_grievance(request):
    """Submit a new grievance"""
    if not request.user.is_student:
        return Response({'error': 'Only students can submit grievances'}, status=status.HTTP_403_FORBIDDEN)
    
    # Create grievance logic here
    return Response({'message': 'Grievance submitted successfully'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_detail(request, grievance_id):
    """Get grievance details"""
    try:
        grievance = Grievance.objects.get(id=grievance_id)
        return Response({
            'id': grievance.id,
            'title': grievance.title,
            'description': grievance.description,
            'status': grievance.status,
            'category': grievance.category.name,
            'submitted_at': grievance.submitted_at,
        })
    except Grievance.DoesNotExist:
        return Response({'error': 'Grievance not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_comments(request, grievance_id):
    """Get grievance comments"""
    try:
        grievance = Grievance.objects.get(id=grievance_id)
        comments = GrievanceComment.objects.filter(grievance=grievance)
        
        return Response([
            {
                'id': c.id,
                'message': c.message,
                'user': c.user.get_full_name(),
                'timestamp': c.timestamp,
            }
            for c in comments
        ])
    except Grievance.DoesNotExist:
        return Response({'error': 'Grievance not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request, grievance_id):
    """Submit feedback for a grievance"""
    if not request.user.is_student:
        return Response({'error': 'Only students can submit feedback'}, status=status.HTTP_403_FORBIDDEN)
    
    # Create feedback logic here
    return Response({'message': 'Feedback submitted successfully'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def category_list(request):
    """Get all categories"""
    categories = Category.objects.filter(is_active=True)
    
    return Response([
        {
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'category_type': c.category_type,
        }
        for c in categories
    ])
