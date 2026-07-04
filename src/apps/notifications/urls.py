from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('send/', views.send_notification, name='send_notification'),
    path('list/', views.notification_list, name='notification_list'),
    path('mark-read/<uuid:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('all/', views.notification_list_view, name='notification_list_view'),
]
