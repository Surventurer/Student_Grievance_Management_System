from django.test import TestCase
from apps.authentication.models import User
from apps.authentication.views import hash_staff_otp, verify_staff_otp
from apps.authentication.security_utils import (
    get_user_failed_attempts, get_user_last_failed_login,
    record_failed_login, clear_user_failed_attempts
)
from apps.grievances.models import AuditLog


class SecurityUtilsTests(TestCase):
    """Unit tests for staff 2FA HMAC-SHA256 and brute force lockout security utils"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='officer_sec@university.edu',
            password='Password123!',
            role='officer'
        )

    def test_hmac_staff_otp_verification(self):
        otp = "654321"
        otp_hash = hash_staff_otp(self.user.id, otp)

        # Successful verification
        self.assertTrue(verify_staff_otp(self.user.id, otp, otp_hash))

        # Incorrect OTP rejected
        self.assertFalse(verify_staff_otp(self.user.id, "111111", otp_hash))

        # Incorrect User ID rejected
        self.assertFalse(verify_staff_otp(self.user.id + 99, otp, otp_hash))

        # Empty inputs rejected
        self.assertFalse(verify_staff_otp(self.user.id, "", otp_hash))
        self.assertFalse(verify_staff_otp(self.user.id, otp, ""))

    def test_record_and_get_failed_login_attempts(self):
        self.assertEqual(get_user_failed_attempts(self.user), 0)

        record_failed_login(self.user, reason="Bad password attempt 1")
        self.assertEqual(get_user_failed_attempts(self.user), 1)

        record_failed_login(self.user, reason="Bad password attempt 2")
        self.assertEqual(get_user_failed_attempts(self.user), 2)

        # AuditLog record created
        audit_records = AuditLog.objects.filter(user=self.user, action='login_failed')
        self.assertEqual(audit_records.count(), 2)

        # Last failed login string formatted
        last_fail_str = get_user_last_failed_login(self.user)
        self.assertIsNotNone(last_fail_str)

    def test_clear_user_failed_attempts(self):
        record_failed_login(self.user, reason="Invalid OTP")
        record_failed_login(self.user, reason="Invalid OTP")
        self.assertGreaterEqual(get_user_failed_attempts(self.user), 2)

        clear_user_failed_attempts(self.user)
        self.assertEqual(get_user_failed_attempts(self.user), 0)
