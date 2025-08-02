from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse
from apps.authentication.models import User


class Command(BaseCommand):
    help = 'Test deactivated user login functionality'

    def handle(self, *args, **options):
        """Test login attempt with deactivated user"""
        
        self.stdout.write("🧪 Testing Deactivated User Login Functionality")
        self.stdout.write("=" * 50)
        
        # Get the deactivated test user
        try:
            user = User.objects.get(email='test@example.com', is_active=False)
            self.stdout.write(f"✅ Found deactivated user: {user.email}")
            self.stdout.write(f"📝 Deactivation reason: '{user.deactivation_reason}'")
        except User.DoesNotExist:
            self.stdout.write("❌ Test user not found. Please create it first.")
            return
        
        # Create a test client
        client = Client()
        
        # Get the login page first
        self.stdout.write("\n🔍 Getting login page...")
        login_url = reverse('authentication:login_view')
        response = client.get(login_url)
        
        if response.status_code != 200:
            self.stdout.write(f"❌ Failed to get login page. Status: {response.status_code}")
            return
        
        self.stdout.write("✅ Login page loaded successfully")
        
        # Attempt login with deactivated user
        self.stdout.write("\n🔐 Attempting login with deactivated user...")
        
        # First, let's test authentication directly
        from django.contrib.auth import authenticate
        auth_user = authenticate(username='test@example.com', password='testpass123')
        
        if auth_user:
            self.stdout.write(f"✅ Authentication successful for user: {auth_user.email}")
            self.stdout.write(f"📝 User is_active: {auth_user.is_active}")
        else:
            self.stdout.write("❌ Authentication failed - this is expected for inactive users in Django")
            self.stdout.write("🔍 Let's check if Django automatically rejects inactive users...")
        
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = client.post(login_url, login_data, follow=False)  # Don't follow redirects
        
        self.stdout.write(f"📊 Response status: {response.status_code}")
        
        # Check if login was rejected (should not redirect)
        if response.status_code == 200:
            self.stdout.write("✅ Login correctly rejected (no redirect)")
        else:
            self.stdout.write(f"❌ Unexpected status code: {response.status_code}")
            return
        
        # Check response content for deactivation message
        response_content = response.content.decode('utf-8')
        
        # Look for deactivation reason in template context
        deactivation_reason_found = False
        if hasattr(response, 'context') and response.context:
            deactivation_reason = response.context.get('deactivation_reason')
            if deactivation_reason:
                self.stdout.write(f"✅ Found deactivation_reason in context: '{deactivation_reason}'")
                deactivation_reason_found = True
            
            # Check Django messages
            messages = list(response.context.get('messages', []))
            if messages:
                self.stdout.write("📬 Found Django messages:")
                for message in messages:
                    self.stdout.write(f"  - {message.tags}: {message}")
                    if 'Account Deactivated' in str(message):
                        self.stdout.write("✅ Found deactivation message in Django messages")
                        deactivation_reason_found = True
            else:
                self.stdout.write("❌ No Django messages found")
        
        # Check HTML content for deactivation message
        if 'Account Deactivated' in response_content or 'account has been deactivated' in response_content.lower():
            self.stdout.write("✅ Account deactivation message found in HTML")
            deactivation_reason_found = True
            
            # Check for specific reason in HTML
            if user.deactivation_reason in response_content:
                self.stdout.write("✅ Specific deactivation reason found in HTML")
            else:
                self.stdout.write("❌ Specific deactivation reason not found in HTML")
        
        if deactivation_reason_found:
            self.stdout.write("🎉 DEACTIVATION REASON DISPLAY IS WORKING!")
        else:
            self.stdout.write("❌ Deactivation reason display not working properly")
            self.stdout.write("🔍 Let's check what's in the response...")
            
            # Look for any error messages
            if 'error' in response_content.lower() or 'invalid' in response_content.lower():
                self.stdout.write("⚠️  Found error-related content in response")
            
            # Check for failed login messages
            if 'failed' in response_content.lower() or 'incorrect' in response_content.lower():
                self.stdout.write("⚠️  Found failed login messages in response")
        
        self.stdout.write("\n🏁 Test completed")
