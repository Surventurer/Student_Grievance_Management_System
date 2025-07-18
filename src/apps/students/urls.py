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
]
