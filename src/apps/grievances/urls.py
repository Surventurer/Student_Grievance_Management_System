from django.urls import path
from . import views

app_name = 'grievances'

urlpatterns = [
    # Web views
    path('submit/', views.submit_grievance_view, name='submit_grievance'),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    
    # API endpoints
    path('', views.grievance_list, name='grievance_list'),
    path('api/submit/', views.submit_grievance, name='submit_grievance_api'),
    path('api/track-view/', views.track_grievance_view, name='track_grievance_view'),
    path('<uuid:grievance_id>/', views.grievance_detail, name='grievance_detail'),
    path('<uuid:grievance_id>/comments/', views.grievance_comments, name='grievance_comments'),
    path('<uuid:grievance_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('categories/', views.category_list, name='category_list'),
    path('api/categories/', views.category_list_api, name='category_list_api'),
]
