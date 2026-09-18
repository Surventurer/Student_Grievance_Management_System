from datetime import datetime, timedelta
from django.utils import timezone
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
                    # Don't delete the message directly so user knows they were logged out
                else:
                    request.session['last_activity'] = now
            except Exception:
                pass
                
        response = self.get_response(request)
        return response
