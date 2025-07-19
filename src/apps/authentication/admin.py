from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerification, PasswordReset, AdminLoginOTP


class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model - showing only schema fields"""
    
    # Display only the fields from your schema: email, password, role, created_at
    list_display = ['email', 'role', 'is_email_verified', 'is_active', 'created_at']
    list_filter = ['role', 'is_email_verified', 'is_active', 'created_at']
    search_fields = ['email']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Schema Fields', {'fields': ('email', 'password', 'role', 'created_at')}),
        ('System Fields', {'fields': ('is_active', 'is_email_verified', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    
    readonly_fields = ['created_at']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )
    
    # Remove username-related functionality since we don't have username field
    filter_horizontal = ('groups', 'user_permissions',)


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Admin configuration for EmailVerification model"""
    
    list_display = ['user', 'otp', 'is_used', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'otp']
    readonly_fields = ['created_at', 'expires_at']


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    """Admin configuration for PasswordReset model"""
    
    list_display = ['user', 'token', 'is_used', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['created_at', 'expires_at']


@admin.register(AdminLoginOTP)
class AdminLoginOTPAdmin(admin.ModelAdmin):
    """Admin configuration for AdminLoginOTP model"""
    
    list_display = ['user', 'otp', 'is_used', 'created_at', 'expires_at', 'session_key']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'otp', 'session_key']
    readonly_fields = ['created_at', 'expires_at']
    
    def has_change_permission(self, request, obj=None):
        # Prevent editing OTP records for security
        return False
    
    def has_add_permission(self, request):
        # Prevent manual creation of OTP records
        return False


admin.site.register(User, UserAdmin)
