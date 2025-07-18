from django.contrib import admin
from .models import Category, Grievance, GrievanceOTPVerification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model"""
    
    list_display = ['name', 'category_type', 'is_active', 'created_at']
    list_filter = ['category_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'keywords']
    list_editable = ['is_active']
    ordering = ['category_type', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category_type', 'is_active')
        }),
        ('Assignment', {
            'fields': ('default_admin', 'keywords'),
            'description': 'Keywords help with auto-assignment (comma-separated)'
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('default_admin')


@admin.register(Grievance)
class GrievanceAdmin(admin.ModelAdmin):
    """Admin interface for Grievance model"""
    
    list_display = ['title', 'student', 'category', 'status', 'priority', 'submitted_at']
    list_filter = ['status', 'priority', 'category__category_type', 'submitted_at']
    search_fields = ['title', 'description', 'student__user__email']
    readonly_fields = ['id', 'submitted_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'title', 'description', 'category', 'department')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'assigned_admin')
        }),
        ('Additional Info', {
            'fields': ('is_anonymous', 'supporting_docs'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__user', 'category', 'assigned_admin'
        )


@admin.register(GrievanceOTPVerification)
class GrievanceOTPVerificationAdmin(admin.ModelAdmin):
    """Admin interface for GrievanceOTPVerification model"""
    
    list_display = ['email', 'otp', 'is_verified', 'created_at', 'is_expired']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['email', 'otp']
    readonly_fields = ['created_at', 'is_expired']
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
