from django.urls import path
from . import views
from . import superadmin_views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    
    # Grievance Management
    path('grievances/', views.grievance_list_advanced, name='grievance_list'),
    path('grievances/api/', views.manage_grievances, name='manage_grievances'),
    path('grievances/<uuid:grievance_id>/', views.grievance_detail_view, name='grievance_detail'),
    path('grievances/<uuid:grievance_id>/update-status/', views.update_grievance_status, name='update_grievance_status'),
    path('grievances/<uuid:grievance_id>/add-response/', views.add_admin_response, name='add_admin_response'),
    path('api/grievance-stats/', views.grievance_stats_api, name='grievance_stats_api'),
    path('api/bulk-delete-grievances/', views.bulk_delete_grievances, name='bulk_delete_grievances'),
    
    # Student Management
    path('students/', views.student_list, name='student_list'),
    path('students/api/', views.manage_students, name='manage_students'),
    path('students/<int:student_id>/', views.student_detail_view, name='student_detail'),
    path('api/student-stats/', views.student_stats_api, name='student_stats_api'),
    path('api/student-actions/', views.student_actions_api, name='student_actions_api'),
    path('api/departments/', views.departments_api, name='departments_api'),
    path('api/add-student/', views.add_student_api, name='add_student_api'),
    
    # Category Management
    path('categories/', views.manage_categories_view, name='manage_categories'),
    path('categories/<int:category_id>/toggle/', views.toggle_category_status, name='toggle_category'),
    
    # Reports and Analytics
    path('reports/', views.reports, name='reports'),
    path('reports/api/', views.reports_api, name='reports_api'),
    path('reports/dashboard/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/download/grievances/', views.download_grievances_csv, name='download_grievances_csv'),
    path('reports/download/monthly/', views.download_monthly_stats_csv, name='download_monthly_stats_csv'),
    path('reports/download/categories/', views.download_category_stats_csv, name='download_category_stats_csv'),
    
    # Audit Logs
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('audit-logs/api/', views.audit_logs, name='audit_logs_api'),
    
    # Auto-Assignment Management
    path('auto-assign/', views.auto_assign_management, name='auto_assign_management'),
    path('auto-assign/category/<uuid:category_id>/', views.category_assignment_detail, name='category_assignment_detail'),
    path('auto-assign/create/', views.create_category_assignment, name='create_category_assignment'),
    path('auto-assign/update/<uuid:assignment_id>/', views.update_category_assignment, name='update_category_assignment'),
    path('auto-assign/delete/<uuid:assignment_id>/', views.delete_category_assignment, name='delete_category_assignment'),
    path('auto-assign/test/', views.test_auto_assignment, name='test_auto_assignment'),
    
    # CRUD Management
    path('manage/', views.crud_management, name='crud_management'),
    
    # Category CRUD
    path('manage/categories/', views.category_management, name='category_management'),
    path('manage/categories/create/', views.category_create, name='category_create'),
    path('manage/categories/<uuid:category_id>/edit/', views.category_edit, name='category_edit'),
    path('manage/categories/<uuid:category_id>/delete/', views.category_delete, name='category_delete'),
    
    # School CRUD
    path('manage/schools/', views.school_management, name='school_management'),
    path('manage/schools/create/', views.school_create, name='school_create'),
    path('manage/schools/<int:school_id>/edit/', views.school_edit, name='school_edit'),
    path('manage/schools/<int:school_id>/delete/', views.school_delete, name='school_delete'),
    
    # Department CRUD
    path('manage/departments/', views.department_management, name='department_management'),
    path('manage/departments/create/', views.department_create, name='department_create'),
    path('manage/departments/<int:department_id>/edit/', views.department_edit, name='department_edit'),
    path('manage/departments/<int:department_id>/delete/', views.department_delete, name='department_delete'),
    
    # ============================================================================
    # SUPERADMIN-ONLY URLS - Require highest level permissions
    # ============================================================================
    
    # User Management (Superadmin Only)
    path('superadmin/users/', superadmin_views.user_management, name='user_management'),
    path('superadmin/users/<int:user_id>/update-role/', superadmin_views.update_user_role, name='update_user_role'),
    path('superadmin/users/<int:user_id>/toggle-status/', superadmin_views.toggle_user_status, name='toggle_user_status'),
    path('superadmin/users/create/', superadmin_views.create_user, name='create_user'),
    path('superadmin/users/create-admin/', superadmin_views.create_admin_user, name='create_admin_user'),  # Legacy redirect
    path('superadmin/users/bulk-delete/', superadmin_views.bulk_delete_users, name='bulk_delete_users'),
    path('superadmin/users/bulk-deactivate/', superadmin_views.bulk_deactivate_users, name='bulk_deactivate_users'),
    
    # Temporary Registration Management (Superadmin Only)
    path('superadmin/temp-registrations/<int:temp_id>/approve/', superadmin_views.approve_temporary_registration, name='approve_temp_registration'),
    path('superadmin/temp-registrations/<int:temp_id>/delete/', superadmin_views.delete_temporary_registration, name='delete_temp_registration'),
    path('superadmin/temp-registrations/<int:temp_id>/details/', superadmin_views.get_temporary_registration_details, name='temp_registration_details'),
    
    # System Settings (Superadmin Only)
    path('superadmin/settings/', superadmin_views.system_settings, name='system_settings'),
    path('superadmin/audit-logs/', superadmin_views.audit_logs_view, name='superadmin_audit_logs'),
    path('superadmin/permissions/', superadmin_views.role_permissions_matrix, name='role_permissions'),
]
