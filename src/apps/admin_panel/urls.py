from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('grievances/', views.grievance_list, name='grievance_list'),
    path('grievances/api/', views.manage_grievances, name='manage_grievances'),
    path('grievances/<uuid:grievance_id>/', views.grievance_detail, name='grievance_detail'),
    path('students/', views.student_list, name='student_list'),
    path('students/api/', views.manage_students, name='manage_students'),
    path('categories/', views.manage_categories, name='manage_categories'),
    path('reports/', views.reports, name='reports'),
    path('reports/api/', views.reports_api, name='reports_api'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
]
