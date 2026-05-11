#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies (if using pip)
# pip install -r requirements.txt
# (Since you are using uv/pyproject.toml, you might use `uv pip install -e .` or similar depending on your render setup)

cd src
python manage.py collectstatic --no-input
python manage.py migrate

# Automatically create superuser if variables are provided in Render environment
if [[ -n "${DJANGO_SUPERUSER_EMAIL}" ]] && [[ -n "${DJANGO_SUPERUSER_PASSWORD}" ]]; then
  echo "Creating superuser..."
  python manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL}" || true
fi
