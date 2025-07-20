#!/bin/bash
set -e

# Wait for database (if using PostgreSQL)
if [ "$DATABASE_URL" != "sqlite:///db.sqlite3" ]; then
    echo "Waiting for database..."
    sleep 5
fi

# Run migrations
echo "Running migrations..."
cd src
uv run python manage.py migrate

# Setup initial data if database is empty
echo "Setting up initial data..."
uv run python manage.py setup_initial_data || echo "Initial data already exists"

# Execute the main command
exec "$@"
