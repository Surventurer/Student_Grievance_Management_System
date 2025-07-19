from django.urls import path
from . import views

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
    
    # Audit Logs
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('audit-logs/api/', views.audit_logs, name='audit_logs_api'),
]
