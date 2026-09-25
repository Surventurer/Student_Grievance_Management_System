from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Grievance, Category, GrievanceComment
from .serializers import GrievanceSerializer, CategorySerializer, GrievanceCommentSerializer
from apps.students.models import StudentProfile

class IsStudentOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow students to view their own grievances,
    but allow admins/officers to view assigned/department grievances.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if hasattr(request.user, 'is_superadmin') and request.user.is_superadmin:
            return True
            
        if hasattr(request.user, 'is_student') and request.user.is_student:
            student_profile = getattr(request.user, 'student_profile', None)
            return student_profile and obj.student == student_profile
            
        if hasattr(request.user, 'is_officer') and request.user.is_officer:
            admin_profile = getattr(request.user, 'admin_profile', None)
            return admin_profile and obj.assigned_to == admin_profile
            
        if hasattr(request.user, 'is_admin') and request.user.is_admin:
            admin_profile = getattr(request.user, 'admin_profile', None)
            if not admin_profile:
                return False
            # Check if grievance belongs to admin's department
            return obj.department == admin_profile.department
            
        return False

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows categories to be viewed.
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class GrievanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows grievances to be viewed or edited.
    """
    serializer_class = GrievanceSerializer
    permission_classes = [IsStudentOrAdmin]
    
    def get_queryset(self):
        user = self.request.user
        
        if hasattr(user, 'is_superadmin') and user.is_superadmin:
            return Grievance.objects.all().order_by('-submitted_at')
            
        if hasattr(user, 'is_student') and user.is_student:
            student_profile = getattr(user, 'student_profile', None)
            if student_profile:
                return Grievance.objects.filter(student=student_profile).order_by('-submitted_at')
            return Grievance.objects.none()
            
        if hasattr(user, 'is_officer') and user.is_officer:
            admin_profile = getattr(user, 'admin_profile', None)
            if admin_profile:
                return Grievance.objects.filter(assigned_to=admin_profile).order_by('-submitted_at')
                
        if hasattr(user, 'is_admin') and user.is_admin:
            admin_profile = getattr(user, 'admin_profile', None)
            if admin_profile and admin_profile.department:
                return Grievance.objects.filter(department=admin_profile.department).order_by('-submitted_at')
                
        return Grievance.objects.none()
        
    def create(self, request, *args, **kwargs):
        user = request.user
        if not (hasattr(user, 'is_student') and user.is_student):
            return Response({"error": "Only students can submit grievances."}, status=status.HTTP_403_FORBIDDEN)
            
        otp_code = request.data.get('otp_code')
        if not otp_code:
            return Response({"error": "otp_code is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        from .models import GrievanceOTPVerification
        email_verification = GrievanceOTPVerification.objects.filter(
            email=user.email,
            otp=otp_code,
            is_verified=False
        ).first()
        
        if not email_verification or email_verification.is_expired:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Call standard create
        response = super().create(request, *args, **kwargs)
        
        # If successfully created, mark OTP as verified
        if response.status_code == status.HTTP_201_CREATED:
            email_verification.is_verified = True
            email_verification.save()
            
            # Auto-assign
            try:
                grievance_id = response.data.get('id')
                grievance = Grievance.objects.get(id=grievance_id)
                grievance.auto_assign()
            except Exception:
                pass
                
        return response

    def perform_create(self, serializer):
        user = self.request.user
        student_profile = get_object_or_404(StudentProfile, user=user)
        serializer.save(student=student_profile)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        grievance = self.get_object()
        message = request.data.get('message')
        
        if not message:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        if grievance.status in ['resolved', 'rejected']:
            return Response({"error": f"This grievance is {grievance.status}. Communication is closed until an appeal or reopen occurs."}, status=status.HTTP_400_BAD_REQUEST)
            
        is_internal = request.data.get('is_internal', False)
        
        # Students cannot create internal notes
        if hasattr(request.user, 'is_student') and request.user.is_student:
            is_internal = False
            
        comment = GrievanceComment.objects.create(
            grievance=grievance,
            user=request.user,
            message=message,
            is_internal=is_internal
        )
        
        serializer = GrievanceCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
