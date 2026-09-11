from rest_framework import serializers
from .models import StudentProfile, AdminProfile, Department
from apps.authentication.models import User


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for student profile"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    
    class Meta:
        model = StudentProfile
        fields = [
            'id', 'student_id', 'department', 'contact_no', 'year_of_study',
            'course', 'emergency_contact', 'address', 'user_email', 'user_name',
            'first_name', 'last_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'student_id', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        
        # Update user fields
        if user_data:
            user = instance.user
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.save()
        
        # Update profile fields
        return super().update(instance, validated_data)


class AdminProfileSerializer(serializers.ModelSerializer):
    """Serializer for admin profile"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    
    class Meta:
        model = AdminProfile
        fields = [
            'id', 'role_level', 'department', 'employee_id', 'phone',
            'office_location', 'user_email', 'user_name', 'first_name',
            'last_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employee_id', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        
        # Update user fields
        if user_data:
            user = instance.user
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.save()
        
        # Update profile fields
        return super().update(instance, validated_data)


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for department"""
    
    school_name = serializers.CharField(source='school.name', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'school_name', 'display_name', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_display_name(self, obj):
        """Return department name with school for display"""
        if obj.school:
            return f"{obj.name} - {obj.school.name}"
        return obj.name


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer for user management by admin"""
    
    student_profile = StudentProfileSerializer(read_only=True)
    admin_profile = AdminProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'role', 'is_active', 'is_email_verified', 'created_at',
            'student_profile', 'admin_profile'
        ]
        read_only_fields = ['id', 'created_at', 'student_profile', 'admin_profile']
