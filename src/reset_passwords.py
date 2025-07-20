import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from django.contrib.auth.hashers import make_password

print("=== RESETTING OFFICER PASSWORDS ===")

# Reset password for both officer accounts
officers = ['officer@university.edu', 'cs_officer@university.edu']

for email in officers:
    try:
        user = User.objects.get(email=email)
        user.set_password('officer123')
        user.save()
        print(f"✅ Password reset for {email}")
        
        # Test authentication
        from django.contrib.auth import authenticate
        test_user = authenticate(username=email, password='officer123')
        if test_user:
            print(f"✅ Authentication test PASSED for {email}")
        else:
            print(f"❌ Authentication test FAILED for {email}")
            
    except User.DoesNotExist:
        print(f"❌ User {email} not found")

print("=== COMPLETE ===")
