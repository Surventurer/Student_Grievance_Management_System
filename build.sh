#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies using uv
uv sync --frozen

cd src
uv run manage.py collectstatic --no-input
uv run manage.py migrate

if [[ -n "${DJANGO_SUPERUSER_EMAIL}" ]] && [[ -n "${DJANGO_SUPERUSER_PASSWORD}" ]]; then
  echo "Creating/updating superuser..."
  uv run manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.students.models import AdminProfile
import os

User = get_user_model()
email = '${DJANGO_SUPERUSER_EMAIL}'
password = '${DJANGO_SUPERUSER_PASSWORD}'
email_verified = '${DJANGO_SUPERUSER_EMAIL_VERIFIED}' == 'True'

user, created = User.objects.get_or_create(
    email=email,
    defaults={
        'is_staff': True,
        'is_superuser': True,
        'role': 'superadmin',
        'is_email_verified': email_verified,
    }
)

if created:
    user.set_password(password)
    user.save()
    print(f'Superuser {email} created (email_verified={email_verified})')
else:
    user.is_email_verified = email_verified
    user.save()
    print(f'Superuser {email} updated (email_verified={email_verified})')

# Ensure AdminProfile exists
AdminProfile.objects.get_or_create(
    user=user,
    defaults={
        'role_level': 'superadmin',
        'employee_id': 'SUPERADMIN-01',
        'department': 'Administration'
    }
)
"
fi
