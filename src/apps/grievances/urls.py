from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

app_name = 'grievances'

# DRF Router setup
router = DefaultRouter()
router.register(r'grievances', api_views.GrievanceViewSet, basename='api-grievance')
router.register(r'categories', api_views.CategoryViewSet, basename='api-category')

urlpatterns = [
    # DRF API endpoints
    path('api/v1/', include(router.urls)),

    # Web views
    path('submit/', views.submit_grievance_view, name='submit_grievance'),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    
    # Legacy API endpoints / view logic
    path('', views.grievance_list, name='grievance_list'),
    path('api/submit/', views.submit_grievance, name='submit_grievance_api'),
    path('api/track-view/', views.track_grievance_view, name='track_grievance_view'),
    path('<uuid:grievance_id>/', views.grievance_detail, name='grievance_detail'),
    path('<uuid:grievance_id>/comments/', views.grievance_comments, name='grievance_comments'),
    path('categories/', views.category_list, name='category_list'),
    path('api/categories/', views.category_list_api, name='category_list_api'),
]
