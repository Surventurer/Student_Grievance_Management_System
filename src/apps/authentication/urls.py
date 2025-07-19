from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # API endpoints
    path('api/register/', views.register, name='api_register'),
    path('api/verify-email/', views.verify_email, name='api_verify_email'),
    path('api/login/', views.login_user, name='api_login'),
    path('api/logout/', views.logout_user, name='api_logout'),
    path('api/profile/', views.profile, name='api_profile'),
    path('api/forgot-password/', views.forgot_password, name='api_forgot_password'),
    path('api/reset-password/<str:token>/', views.reset_password, name='api_reset_password'),
    
    # Web views
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('verify-email/', views.verify_email_view, name='verify_email_view'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password_view'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password_view'),
    path('resend-admin-otp/', views.resend_admin_otp, name='resend_admin_otp'),
    
    # Student Registration Only (No admin/staff registration)
    path('student-registration/', views.student_registration, name='student_registration'),
    path('load-departments/', views.load_departments, name='load_departments'),
]
