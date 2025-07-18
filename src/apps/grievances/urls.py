from django.urls import path
from . import views

app_name = 'grievances'

urlpatterns = [
    path('', views.grievance_list, name='grievance_list'),
    path('submit/', views.submit_grievance, name='submit_grievance'),
    path('<uuid:grievance_id>/', views.grievance_detail, name='grievance_detail'),
    path('<uuid:grievance_id>/comments/', views.grievance_comments, name='grievance_comments'),
    path('<uuid:grievance_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('categories/', views.category_list, name='category_list'),
]
