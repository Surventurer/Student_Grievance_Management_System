from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('send/', views.send_notification, name='send_notification'),
    path('list/', views.notification_list, name='notification_list'),
]
