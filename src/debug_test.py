import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from apps.students.models import AdminProfile

print("=== DEBUG TEST ===")

# Check officer users
officers = User.objects.filter(role='officer')
print(f"Officers found: {officers.count()}")

for officer in officers:
    print(f"Officer: {officer.email}, Role: {officer.role}")
    print(f"  is_admin: {officer.is_admin}")
    print(f"  is_authenticated: {officer.is_authenticated}")
    print(f"  is_active: {officer.is_active}")
    
    try:
        admin_profile = AdminProfile.objects.get(user=officer)
        print(f"  Admin Profile: {admin_profile.role_level} in {admin_profile.department}")
    except AdminProfile.DoesNotExist:
        print(f"  No admin profile found!")
    print()

print("=== END DEBUG ===")
