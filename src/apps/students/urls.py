from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # API endpoints
    path('api/dashboard/', views.student_dashboard, name='dashboard_api'),
    path('api/profile/', views.student_profile, name='profile_api'),
    path('api/admin/dashboard/', views.admin_dashboard, name='admin_dashboard_api'),
    path('api/admin/profile/', views.admin_profile, name='admin_profile_api'),
    path('api/admin/students/', views.manage_students, name='manage_students_api'),
    path('api/departments/', views.departments, name='departments_api'),
    path('api/activity/', views.user_activity, name='user_activity_api'),
    
    # Web views
    path('', views.student_dashboard_view, name='dashboard'),
    path('profile/', views.student_profile_view, name='profile'),
    path('profile/update-contact/', views.update_contact_view, name='update_contact'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('grievances/', views.student_grievances_view, name='grievances'),
    path('grievances/<uuid:grievance_id>/', views.student_grievance_detail_view, name='grievance_detail'),
    path('grievances/<uuid:grievance_id>/add-response/', views.add_student_response, name='add_student_response'),
    path('grievances/<uuid:grievance_id>/submit-feedback/', views.submit_feedback_view, name='submit_feedback'),
    path('api/notifications/', views.get_notifications_api, name='notifications_api'),
    path('api/notifications/mark-read/<uuid:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
]
