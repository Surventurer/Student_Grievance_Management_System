#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies using uv
uv sync --frozen

cd src
uv run manage.py collectstatic --no-input
uv run manage.py migrate

if [[ -n "${DJANGO_SUPERUSER_EMAIL}" ]] && [[ -n "${DJANGO_SUPERUSER_PASSWORD}" ]]; then
  echo "Creating superuser..."
  uv run manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.students.models import AdminProfile

User = get_user_model()
email = '${DJANGO_SUPERUSER_EMAIL}'
password = '${DJANGO_SUPERUSER_PASSWORD}'

if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(email=email, password=password)
    user.is_email_verified = True
    user.save()
    
    # Ensure AdminProfile exists
    AdminProfile.objects.get_or_create(
        user=user,
        defaults={
            'role_level': 'superadmin',
            'employee_id': 'SUPERADMIN-01',
            'department': 'Administration'
        }
    )
    print(f'Superuser {email} created successfully with verified email!')
else:
    print(f'Superuser {email} already exists.')
"
fi
