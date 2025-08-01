"""
Rate Limiting Debug View
This view helps debug and reset rate limiting issues.
"""

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
import json

@staff_member_required
def debug_rate_limiting(request):
    """Debug view to check rate limiting status"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'clear_all':
            # Clear all rate limiting sessions
            keys_to_remove = []
            for key in request.session.keys():
                if key.startswith('login_attempts_') or key.startswith('last_login_attempt_') or \
                   key.startswith('failed_otp_attempts_') or key.startswith('last_failed_attempt_'):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del request.session[key]
            
            return JsonResponse({'success': True, 'message': 'All rate limiting cleared'})
        
        elif action == 'clear_email':
            email = request.POST.get('email')
            if email:
                keys_to_remove = [
                    f'login_attempts_{email}',
                    f'last_login_attempt_{email}'
                ]
                for key in keys_to_remove:
                    request.session.pop(key, None)
                
                return JsonResponse({'success': True, 'message': f'Rate limiting cleared for {email}'})
    
    # Get current rate limiting status
    rate_limiting_data = {}
    for key, value in request.session.items():
        if key.startswith('login_attempts_') or key.startswith('last_login_attempt_') or \
           key.startswith('failed_otp_attempts_') or key.startswith('last_failed_attempt_'):
            rate_limiting_data[key] = value
    
    return render(request, 'authentication/debug_rate_limiting.html', {
        'rate_limiting_data': rate_limiting_data
    })
