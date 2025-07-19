# Admin OTP Login System

## Overview
The Student Grievance Management System now includes **Two-Factor Authentication (2FA)** for admin users only. This adds an extra layer of security to protect administrative access.

## How It Works

### For Admin Users:
1. **Step 1**: Enter email and password as usual
2. **Step 2**: If credentials are valid, an OTP is sent to their email
3. **Step 3**: Enter the 6-digit OTP to complete login
4. **Success**: Redirected to admin dashboard

### For Non-Admin Users (Students, Officers):
- Normal login process (email + password only)
- No OTP required

## Security Features

### OTP Security:
- **6-digit numeric code**
- **5-minute expiration**
- **Single-use only**
- **Automatically invalidated** after successful login

### Brute Force Protection:
- **Maximum 3 failed OTP attempts** in 5 minutes
- **Account lockout** for 5 minutes after exceeding limit
- **Automatic cleanup** of expired OTPs

### Session Security:
- **Session-based tracking** of login attempts
- **Automatic session cleanup** after login completion
- **Invalid session detection** and redirect to login

## Features

### 1. Email Verification
```
Subject: Admin Login Verification - OTP
Content: Your OTP for admin login is: 123456. This code will expire in 5 minutes.
Security Note: If you did not attempt to login, please contact the system administrator immediately.
```

### 2. Resend OTP
- **Resend button** available on OTP verification page
- **1-minute cooldown** between resend requests
- **Automatic invalidation** of previous OTPs when new one is sent

### 3. User Interface
- **Dynamic form** that switches between login and OTP verification
- **Auto-submit** when 6 digits are entered
- **Countdown timer** for resend functionality
- **Clear error messages** for invalid/expired OTPs

### 4. Admin Panel Integration
- **AdminLoginOTP model** available in Django admin
- **Read-only access** to OTP records for security auditing
- **Automatic cleanup** command for expired OTPs

## Configuration

### Email Settings (.env file):
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Management Commands:
```bash
# Clean up expired admin OTPs
python manage.py cleanup_admin_otps

# Clean up expired registration tokens
python manage.py cleanup_expired_registrations
```

## Testing

### Admin Login Test:
1. Go to `/auth/login/`
2. Use any admin account:
   - Email: `admin@grievance.com`
   - Password: `admin123`
3. Check email for OTP (or console if using console backend)
4. Enter OTP to complete login

### Student Login Test:
1. Use any student account - no OTP required
2. Direct login to student dashboard

## Database Schema

### AdminLoginOTP Model:
```python
class AdminLoginOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    session_key = models.CharField(max_length=100, null=True, blank=True)
```

## Security Considerations

### Production Recommendations:
1. **Use secure email provider** (not console backend)
2. **Enable HTTPS** for all login pages
3. **Set up proper session security** in Django settings
4. **Monitor failed login attempts** in logs
5. **Regular cleanup** of expired OTP records

### Monitoring:
- **Admin panel** shows all OTP attempts
- **Failed attempts** are logged with timestamps
- **Session tracking** for security auditing

## Troubleshooting

### Common Issues:
1. **OTP not received**: Check email configuration in `.env`
2. **OTP expired**: Regenerate new OTP (5-minute window)
3. **Too many attempts**: Wait 5 minutes for lockout to clear
4. **Session expired**: Start login process again

### Support:
- Check Django admin panel for OTP records
- Use management commands for cleanup
- Monitor email backend for delivery issues
