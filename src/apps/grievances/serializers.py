from rest_framework import serializers
from .models import Category, Grievance, GrievanceComment, GrievanceAttachment

class CategorySerializer(serializers.ModelSerializer):
    category_type_display = serializers.CharField(source='get_category_type_display', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'category_type', 'category_type_display', 'is_active', 'sla_hours']

class GrievanceAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GrievanceAttachment
        fields = ['id', 'file', 'file_name', 'file_size', 'file_type', 'file_url', 'uploaded_at']
        
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

class GrievanceCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = GrievanceComment
        fields = ['id', 'grievance', 'comment_type', 'message', 'is_internal', 'timestamp', 'user_name', 'user_email']
        read_only_fields = ['id', 'grievance', 'user_name', 'user_email', 'timestamp']
        
    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return "System"
        
    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return None

class GrievanceSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    student_name = serializers.SerializerMethodField()
    attachments = GrievanceAttachmentSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    
    class Meta:
        model = Grievance
        fields = [
            'id', 'title', 'description', 'category', 'category_detail', 'department',
            'status', 'status_display', 'priority', 'priority_display', 'is_anonymous',
            'is_hosteler', 'hostel_name', 'hostel_room_no', 'is_escalated', 'is_appealed',
            'expected_resolution_date', 'actual_resolution_date', 'submitted_at', 'updated_at',
            'student_name', 'attachments', 'comments'
        ]
        read_only_fields = [
            'id', 'status', 'status_display', 'priority', 'priority_display', 'is_escalated', 
            'is_appealed', 'expected_resolution_date', 'actual_resolution_date', 'submitted_at', 
            'updated_at', 'student_name', 'attachments', 'comments'
        ]
        
    def get_student_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.student.name or obj.student.user.email
        
    def get_comments(self, obj):
        # Exclude internal notes if the user is a student
        request = self.context.get('request')
        comments = obj.comments.all()
        if request and request.user.is_authenticated and hasattr(request.user, 'is_student') and request.user.is_student:
            comments = comments.filter(is_internal=False)
        return GrievanceCommentSerializer(comments, many=True, context=self.context).data
