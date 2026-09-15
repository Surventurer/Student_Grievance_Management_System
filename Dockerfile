# Use modern Python 3.12 slim image
FROM python:3.12-slim-bookworm

# Set environment variables for Python and uv performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=1

# Install uv (The high-performance Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set work directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies using pre-compiled wheels
RUN uv pip install --no-cache .

# Create media and static directories
RUN mkdir -p /app/src/media /app/src/staticfiles

# Run collectstatic so WhiteNoise serves static assets
RUN cd src && \
    SECRET_KEY=dummy-build-key DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput --clear

# Expose Daphne ASGI port
EXPOSE 8000

# Default entrypoint: Apply database migrations and start Daphne ASGI server (HTTP + WebSockets)
CMD ["sh", "-c", "cd src && python manage.py migrate && daphne -b 0.0.0.0 -p 8000 config.asgi:application"]
