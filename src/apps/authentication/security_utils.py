from datetime import datetime
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def get_user_failed_attempts(user):
    """
    Get the running failed login attempts count for a user.
    Uses security cache with fallback to AuditLog query.
    """
    if not user or not user.pk:
        return 0
    try:
        from apps.authentication.views import security_cache_get, security_cache_set
        
        key_count = f'user_failed_attempts_{user.id}'
        cached_count = security_cache_get(key_count, None)
        if cached_count is not None:
            try:
                return int(cached_count)
            except (ValueError, TypeError):
                pass

        # Fallback to AuditLog query if not in cache
        from apps.grievances.models import AuditLog
        from django.db.models import Q
        
        reset_time_iso = security_cache_get(f'user_failed_attempts_reset_{user.id}', None)
        cutoff = user.last_login
        if reset_time_iso:
            reset_dt = parse_datetime(reset_time_iso)
            if reset_dt:
                if cutoff is None or reset_dt > cutoff:
                    cutoff = reset_dt

        query = Q(target_model='User', target_id=str(user.id)) & (
            Q(action='login_failed') | Q(description__icontains='login failed')
        )
        if cutoff:
            query &= Q(timestamp__gt=cutoff)

        count = AuditLog.objects.filter(query).count()
        # Cache the count for 30 days
        security_cache_set(key_count, count, timeout=86400 * 30)
        return count
    except Exception as e:
        print(f"Error getting failed login attempts for user {getattr(user, 'id', None)}: {e}")
        return 0


def get_user_last_failed_login(user):
    """
    Get the timestamp of the last failed login attempt for a user.
    """
    if not user or not user.pk:
        return None
    try:
        from apps.authentication.views import security_cache_get, security_cache_set
        
        key_last = f'user_last_failed_login_{user.id}'
        last_str = security_cache_get(key_last, None)
        if last_str:
            return last_str

        # Fallback to latest AuditLog
        from apps.grievances.models import AuditLog
        from django.db.models import Q

        reset_time_iso = security_cache_get(f'user_failed_attempts_reset_{user.id}', None)
        cutoff = user.last_login
        if reset_time_iso:
            reset_dt = parse_datetime(reset_time_iso)
            if reset_dt:
                if cutoff is None or reset_dt > cutoff:
                    cutoff = reset_dt

        query = Q(target_model='User', target_id=str(user.id)) & (
            Q(action='login_failed') | Q(description__icontains='login failed')
        )
        if cutoff:
            query &= Q(timestamp__gt=cutoff)

        latest_fail = AuditLog.objects.filter(query).order_by('-timestamp').first()
        if latest_fail and latest_fail.timestamp:
            formatted = latest_fail.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            security_cache_set(key_last, formatted, timeout=86400 * 30)
            return formatted
    except Exception as e:
        print(f"Error getting last failed login for user {getattr(user, 'id', None)}: {e}")
    return None


def record_failed_login(user, request=None, reason="Invalid credentials"):
    """
    Record a failed login attempt for a user:
    1. Increments running counter in security cache
    2. Records last failed login timestamp
    3. Records client IP for rate-limit clearing
    4. Writes AuditLog record for audit and persistence
    """
    if not user or not user.pk:
        return
    try:
        from apps.authentication.views import security_cache_set
        from apps.admin_panel.audit_utils import get_client_ip
        from apps.grievances.models import AuditLog
        
        now = timezone.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Update running counter in cache
        key_count = f'user_failed_attempts_{user.id}'
        key_last = f'user_last_failed_login_{user.id}'
        key_ip = f'user_last_fail_ip_{user.id}'
        
        current_count = get_user_failed_attempts(user)
        new_count = current_count + 1
        security_cache_set(key_count, new_count, timeout=86400 * 30)
        security_cache_set(key_last, now_str, timeout=86400 * 30)
        
        client_ip = '127.0.0.1'
        user_agent = ''
        if request:
            client_ip = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
            security_cache_set(key_ip, client_ip, timeout=86400 * 30)
            
        # 2. Permanent audit log record
        role_name = user.get_role_display() if hasattr(user, 'get_role_display') else getattr(user, 'role', 'User')
        AuditLog.objects.create(
            user=user,
            action='login_failed',
            target_model='User',
            target_id=str(user.id),
            description=f"{role_name} login failed: {reason}",
            ip_address=client_ip,
            user_agent=user_agent
        )
    except Exception as e:
        print(f"Error recording failed login for user {getattr(user, 'id', None)}: {e}")


def clear_user_failed_attempts(user, request=None):
    """
    Clear running failed login attempts for a user (on successful login or superadmin reset):
    1. Resets security cache counter to 0
    2. Clears last failed timestamp
    3. Sets reset cutoff timestamp
    4. Clears security rate-limit lockout keys for this user/email
    5. Cleans active AdminLoginOTP records for staff users
    """
    if not user or not user.pk:
        return
    try:
        from apps.authentication.views import security_cache_set, security_cache_delete, security_cache_get
        from apps.admin_panel.audit_utils import get_client_ip
        from apps.authentication.models import AdminLoginOTP
        from django.core.cache import cache
        
        now = timezone.now()
        key_count = f'user_failed_attempts_{user.id}'
        key_last = f'user_last_failed_login_{user.id}'
        key_reset = f'user_failed_attempts_reset_{user.id}'
        key_ip = f'user_last_fail_ip_{user.id}'
        
        security_cache_set(key_count, 0, timeout=86400 * 30)
        security_cache_delete(key_last)
        security_cache_set(key_reset, now.isoformat(), timeout=86400 * 30)
        
        # Clear rate-limit lockout keys
        email_clean = user.email.lower().strip() if user.email else ''
        
        # Clear for request IP if provided
        if request:
            curr_ip = get_client_ip(request)
            if email_clean:
                security_cache_delete(f'rl_login_{curr_ip}_{email_clean}')
            security_cache_delete(f'rl_otp_{curr_ip}_{user.id}')
            
        # Clear for recorded last failed IP
        last_ip = security_cache_get(key_ip, None)
        if last_ip:
            if email_clean:
                security_cache_delete(f'rl_login_{last_ip}_{email_clean}')
            security_cache_delete(f'rl_otp_{last_ip}_{user.id}')
            security_cache_delete(key_ip)

        # Clear staff OTP verification hash
        security_cache_delete(f'staff_otp_hash_{user.id}')
        
        # Also attempt pattern delete on cache backend if supported (e.g. redis-py)
        try:
            if hasattr(cache, 'delete_pattern'):
                if email_clean:
                    cache.delete_pattern(f'*rl_login*{email_clean}*')
                cache.delete_pattern(f'*rl_otp*{user.id}*')
        except Exception:
            pass

        # Clear AdminLoginOTP records
        AdminLoginOTP.objects.filter(user=user).delete()
    except Exception as e:
        print(f"Error clearing failed login attempts for user {getattr(user, 'id', None)}: {e}")

