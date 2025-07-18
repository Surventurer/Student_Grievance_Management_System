#!/usr/bin/env python
"""
Check contact number storage in database
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.students.models import StudentProfile

print("=== CONTACT NUMBER STORAGE VERIFICATION ===\n")

print("📱 StudentProfile Model Fields:")
for field in StudentProfile._meta.fields:
    if field.name == 'contact_no':
        print(f"  ✅ {field.name}: {field.__class__.__name__}")
        print(f"     - Max Length: {field.max_length}")
        print(f"     - Nullable: {field.null}")
        print(f"     - Blank: {field.blank}")
        print()

print("📊 Current Student Profiles with Contact Numbers:")
profiles = StudentProfile.objects.all()
if profiles.exists():
    for profile in profiles:
        print(f"  • {profile.name} ({profile.student_id})")
        print(f"    Email: {profile.user.email}")
        print(f"    Contact: {profile.contact_no or 'Not set'}")
        print()
else:
    print("  No student profiles found in database")

print(f"Total Student Profiles: {StudentProfile.objects.count()}")

if __name__ == "__main__":
    pass
