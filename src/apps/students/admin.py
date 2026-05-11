from django.contrib import admin
from .models import StudentProfile, AdminProfile, Department, UserActivity, School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    """Admin configuration for School"""
    
    list_display = ['id', 'name', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin configuration for StudentProfile"""
    
    list_display = ['student_id', 'name', 'user', 'department', 'created_at']
    list_filter = ['department', 'created_at']
    search_fields = ['student_id', 'name', 'user__email', 'department']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'name')
        }),
        ('Academic Information', {
            'fields': ('student_id', 'department', 'school')
        }),
        ('Contact Information', {
            'fields': ('contact_no',)
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
    
    list_display = ['id', 'name', 'school', 'created_at']
    list_filter = ['school', 'created_at']
    search_fields = ['name', 'school__name']
    ordering = ['name']
    
    fieldsets = (
        ('Department Information', {
            'fields': ('name', 'school')
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
