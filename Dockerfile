# Use python slim image
FROM python:3.12-slim-bookworm

# Set environment variables for Python and uv
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies required for psycopg2, pillow, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (The ultra-fast python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set work directory
WORKDIR /app

# Copy the entire application
COPY . .

# Install dependencies using uv
RUN uv pip install .

# Run collectstatic so Whitenoise can serve the minified files
RUN cd src && \
    SECRET_KEY=dummy-build-key DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput --clear

# Expose the Daphne port
EXPOSE 8000

# Default command (uses standard python since we installed into system env)
CMD ["sh", "-c", "cd src && python manage.py migrate && daphne -b 0.0.0.0 -p 8000 config.asgi:application"]
