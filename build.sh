#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies using uv
uv sync --frozen

cd src
uv run manage.py collectstatic --no-input
uv run manage.py migrate

# Automatically create superuser if variables are provided in Render environment
if [[ -n "${DJANGO_SUPERUSER_EMAIL}" ]] && [[ -n "${DJANGO_SUPERUSER_PASSWORD}" ]]; then
  echo "Creating superuser..."
  uv run manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL}" || true
fi
