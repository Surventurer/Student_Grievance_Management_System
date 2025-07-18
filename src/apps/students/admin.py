from django.contrib import admin
from .models import StudentProfile, AdminProfile, Department, UserActivity


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin configuration for StudentProfile"""
    
    list_display = ['student_id', 'user', 'department', 'year_of_study', 'created_at']
    list_filter = ['department', 'year_of_study', 'created_at']
    search_fields = ['student_id', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Academic Information', {
            'fields': ('student_id', 'department', 'year_of_study', 'course')
        }),
        ('Contact Information', {
            'fields': ('contact_no', 'emergency_contact', 'address')
        }),
    )


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    """Admin configuration for AdminProfile"""
    
    list_display = ['employee_id', 'user', 'role_level', 'department', 'created_at']
    list_filter = ['role_level', 'department', 'created_at']
    search_fields = ['employee_id', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Role Information', {
            'fields': ('role_level', 'department', 'employee_id')
        }),
        ('Contact Information', {
            'fields': ('phone', 'office_location')
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin configuration for Department"""
    
    list_display = ['name', 'head_of_department', 'contact_email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    fieldsets = (
        ('Department Information', {
            'fields': ('name', 'description', 'head_of_department')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
    )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin configuration for UserActivity"""
    
    list_display = ['user', 'login_time', 'ip_address', 'is_successful']
    list_filter = ['is_successful', 'login_time']
    search_fields = ['user__email', 'ip_address']
    ordering = ['-login_time']
    readonly_fields = ['user', 'login_time', 'ip_address', 'user_agent', 'is_successful']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
