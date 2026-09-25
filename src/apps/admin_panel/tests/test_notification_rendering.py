from django.test import TestCase, RequestFactory
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.contrib.messages import success, error
from apps.admin_panel.models import SystemSettings

User = get_user_model()

class MessageRenderingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superadmin = User.objects.create_superuser(
            email='superadmin@univ.edu',
            password='Password123!',
            role='superadmin'
        )
        self.settings, _ = SystemSettings.objects.get_or_create()

    def test_system_settings_message_renders_once(self):
        request = self.factory.get('/admin-panel/superadmin/settings/')
        request.user = self.superadmin
        # Set up messages storage
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Add success message
        success(request, 'System settings updated successfully!')
        
        context = {
            'request': request,
            'user': self.superadmin,
            'settings': self.settings,
            'messages': get_messages(request),
            'system_settings': self.settings,
        }
        
        rendered = render_to_string('admin_panel/superadmin/system_settings.html', context, request=request)
        self.assertEqual(
            rendered.count('System settings updated successfully!'),
            1,
            "Success message must appear exactly once in system settings page"
        )

    def test_login_message_renders_once(self):
        request = self.factory.get('/auth/login/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        error(request, 'Invalid email or password.')
        
        context = {
            'request': request,
            'user': request.user,
            'messages': get_messages(request),
            'system_settings': self.settings,
        }
        
        rendered = render_to_string('authentication/login.html', context, request=request)
        self.assertEqual(
            rendered.count('Invalid email or password.'),
            1,
            "Error message must appear exactly once on login page"
        )

    def test_forgot_password_message_renders_once(self):
        request = self.factory.get('/auth/forgot-password/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        success(request, 'Password reset link has been sent.')
        
        context = {
            'request': request,
            'user': request.user,
            'messages': get_messages(request),
            'system_settings': self.settings,
        }
        
        rendered = render_to_string('authentication/forgot_password.html', context, request=request)
        self.assertEqual(
            rendered.count('Password reset link has been sent.'),
            1,
            "Message must appear exactly once on forgot password page"
        )

    def test_create_user_message_renders_once(self):
        request = self.factory.get('/admin-panel/superadmin/users/create/')
        request.user = self.superadmin
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        error(request, 'Please correct the errors in the form.')
        
        context = {
            'request': request,
            'user': self.superadmin,
            'departments': [],
            'schools': [],
            'role_choices': [('student', 'Student'), ('admin', 'Department Admin')],
            'messages': get_messages(request),
            'system_settings': self.settings,
        }
        
        rendered = render_to_string('admin_panel/superadmin/create_user.html', context, request=request)
        self.assertEqual(
            rendered.count('Please correct the errors in the form.'),
            1,
            "Error message must appear exactly once on create user page"
        )

    def test_student_registration_message_renders_once(self):
        request = self.factory.get('/auth/student/register/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        error(request, 'Registration failed: Invalid email domain.')
        
        from apps.authentication.forms import StudentRegistrationForm
        context = {
            'request': request,
            'user': request.user,
            'form': StudentRegistrationForm(),
            'messages': get_messages(request),
            'system_settings': self.settings,
        }
        
        rendered = render_to_string('authentication/student_registration.html', context, request=request)
        self.assertEqual(
            rendered.count('Registration failed: Invalid email domain.'),
            1,
            "Message must appear exactly once on student registration page"
        )

    def test_verify_student_email_message_renders_once(self):
        request = self.factory.get('/auth/verify-student-email/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        success(request, 'OTP sent successfully.')
        
        context = {
            'request': request,
            'user': request.user,
            'messages': get_messages(request),
            'system_settings': self.settings,
        }
        
        rendered = render_to_string('authentication/verify_student_email.html', context, request=request)
        self.assertEqual(
            rendered.count('OTP sent successfully.'),
            1,
            "Message must appear exactly once on verify student email page"
        )
