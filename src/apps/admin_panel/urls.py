from django.urls import path
from . import views
from . import superadmin_views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    
    # Grievance Management (All Grievances)
    path('grievances/', views.grievance_list_advanced, name='grievance_list'),
    path('grievances/api/', views.manage_grievances, name='manage_grievances'),
    path('grievances/<uuid:grievance_id>/', views.grievance_detail_view, name='grievance_detail'),
    path('grievances/<uuid:grievance_id>/update-status/', views.update_grievance_status, name='update_grievance_status'),
    path('grievances/<uuid:grievance_id>/add-response/', views.add_admin_response, name='add_admin_response'),
    path('api/grievance-stats/', views.grievance_stats_api, name='grievance_stats_api'),
    path('api/bulk-delete-grievances/', views.bulk_delete_grievances, name='bulk_delete_grievances'),
    
    # Audit Logs
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('audit-logs/api/', views.audit_logs, name='audit_logs_api'),
    
    # CRUD Management
    path('manage/', views.crud_management, name='crud_management'),
    
    # Category CRUD
    path('manage/categories/', views.category_management, name='category_management'),
    path('manage/categories/create/', views.category_create, name='category_create'),
    path('manage/categories/<uuid:category_id>/edit/', views.category_edit, name='category_edit'),
    path('manage/categories/<uuid:category_id>/delete/', views.category_delete, name='category_delete'),
    path('manage/categories/bulk-delete/', views.bulk_delete_categories, name='bulk_delete_categories'),
    path('manage/categories/bulk-update-status/', views.bulk_update_category_status, name='bulk_update_category_status'),
    
    # School CRUD
    path('manage/schools/', views.school_management, name='school_management'),
    path('manage/schools/create/', views.school_create, name='school_create'),
    path('manage/schools/<int:school_id>/edit/', views.school_edit, name='school_edit'),
    path('manage/schools/<int:school_id>/delete/', views.school_delete, name='school_delete'),
    path('manage/schools/bulk-activate/', views.bulk_activate_schools, name='bulk_activate_schools'),
    path('manage/schools/bulk-deactivate/', views.bulk_deactivate_schools, name='bulk_deactivate_schools'),
    path('manage/schools/bulk-delete/', views.bulk_delete_schools, name='bulk_delete_schools'),
    
    # Department CRUD
    path('manage/departments/', views.department_management, name='department_management'),
    path('manage/departments/create/', views.department_create, name='department_create'),
    path('manage/departments/<int:department_id>/edit/', views.department_edit, name='department_edit'),
    path('manage/departments/<int:department_id>/delete/', views.department_delete, name='department_delete'),
    
    # ============================================================================
    # SUPERADMIN-ONLY URLS - Core functionalities only
    # ============================================================================
    
    # User Management (Superadmin Only) - All Users Tab
    path('superadmin/users/', superadmin_views.user_management, name='user_management'),
    path('superadmin/users/<int:user_id>/update-role/', superadmin_views.update_user_role, name='update_user_role'),
    path('superadmin/users/<int:user_id>/toggle-status/', superadmin_views.toggle_user_status, name='toggle_user_status'),
    path('superadmin/users/<int:user_id>/update-deactivation-reason/', superadmin_views.update_deactivation_reason, name='update_deactivation_reason'),
    path('superadmin/users/<int:user_id>/details/', superadmin_views.get_user_details, name='get_user_details'),
    path('superadmin/users/<int:user_id>/edit/', superadmin_views.edit_user, name='edit_user'),
    path('superadmin/users/schools-departments/', superadmin_views.get_schools_departments, name='get_schools_departments'),
    path('superadmin/users/create/', superadmin_views.create_user, name='create_user'),
    path('superadmin/users/bulk-delete/', superadmin_views.bulk_delete_users, name='bulk_delete_users'),
    path('superadmin/users/bulk-deactivate/', superadmin_views.bulk_deactivate_users, name='bulk_deactivate_users'),
    path('superadmin/users/bulk-activate/', superadmin_views.bulk_activate_users, name='bulk_activate_users'),
    
    # Temporary Registration Management (Part of User Management)
    path('superadmin/temp-registrations/<int:temp_id>/approve/', superadmin_views.approve_temporary_registration, name='approve_temp_registration'),
    path('superadmin/temp-registrations/<int:temp_id>/delete/', superadmin_views.delete_temporary_registration, name='delete_temp_registration'),
    path('superadmin/temp-registrations/<int:temp_id>/details/', superadmin_views.get_temporary_registration_details, name='temp_registration_details'),
    
    # System Settings (Superadmin Only)
    path('superadmin/settings/', superadmin_views.system_settings, name='system_settings'),
    
    # Audit Logs (Superadmin Only)
    path('superadmin/audit-logs/', superadmin_views.audit_logs_view, name='superadmin_audit_logs'),
]
