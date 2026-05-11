from django.contrib import admin
from .models import ReadNotification, Notification


@admin.register(ReadNotification)
class ReadNotificationAdmin(admin.ModelAdmin):
    list_display = ['student', 'comment', 'read_at']
    list_filter = ['read_at', 'student__role']
    search_fields = ['student__email', 'comment__message']
    readonly_fields = ['read_at']
    raw_id_fields = ['student', 'comment']
    
    def has_add_permission(self, request):
        # Prevent manual creation through admin
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'comment')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for general Notification model"""
    list_display = ['recipient', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__email', 'title', 'message']
    readonly_fields = ['created_at']
