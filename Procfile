web: cd src && uv run daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
worker: cd src && uv run celery -A config worker --loglevel=info
beat: cd src && uv run celery -A config beat --loglevel=info
