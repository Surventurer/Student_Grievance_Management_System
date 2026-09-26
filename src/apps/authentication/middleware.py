from datetime import datetime
from django.contrib import messages
from django.shortcuts import redirect
from apps.admin_panel.models import SystemSettings
from django.contrib.auth import logout


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                settings = SystemSettings.load()
                timeout = settings.session_timeout * 60  # convert to seconds
                
                last_activity = request.session.get('last_activity')
                now = datetime.now().timestamp()
                
                if last_activity and (now - last_activity) > timeout:
                    logout(request)
                    messages.warning(request, 'Your session has expired due to inactivity. Please log in again.')
                    return redirect('authentication:login_view')
                else:
                    request.session['last_activity'] = now
                    # Synchronize cookie & database expire_date with sliding inactivity timeout
                    request.session.set_expiry(timeout)
            except Exception:
                pass
                
        response = self.get_response(request)
        return response
