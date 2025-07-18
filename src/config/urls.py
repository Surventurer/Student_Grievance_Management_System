from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def home_redirect(request):
    """Redirect root URL to login page"""
    return redirect('authentication:login_view')

urlpatterns = [
    path('', home_redirect, name='home'),  # Root URL redirect
    path('admin/', admin.site.urls),
    path('api/auth/', include(('apps.authentication.urls', 'authentication'), namespace='auth_api')),
    path('api/students/', include(('apps.students.urls', 'students'), namespace='students_api')),
    path('api/grievances/', include('apps.grievances.urls')),
    path('api/admin-panel/', include(('apps.admin_panel.urls', 'admin_panel'), namespace='admin_api')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('auth/', include('apps.authentication.urls')),  # For web views
    path('students/', include('apps.students.urls')),  # For student web views
    path('admin-panel/', include('apps.admin_panel.urls')),  # For admin web views
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
