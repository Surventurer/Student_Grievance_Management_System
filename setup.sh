#!/bin/bash

# Student Grievance Management System - Quick Setup Script
# This script automates the setup process for the application

echo "🎓 Student Grievance Management System - Setup Script"
echo "===================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    print_error "UV is not installed. Please install it first:"
    echo "  pip install uv"
    exit 1
fi

print_success "UV is installed ✅"

# Step 1: Install dependencies
print_status "Installing dependencies..."
if uv sync; then
    print_success "Dependencies installed ✅"
else
    print_error "Failed to install dependencies ❌"
    exit 1
fi

# Step 2: Check if .env exists, create from example if not
if [ ! -f .env ]; then
    print_status "Creating .env file from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success ".env file created ✅"
        print_warning "Please review and update .env file with your settings"
    else
        print_warning ".env.example not found, creating basic .env file..."
        cat > .env << EOL
SECRET_KEY=django-insecure-development-key-$(date +%s)
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
REDIS_URL=redis://localhost:6379/0
EOL
        print_success "Basic .env file created ✅"
    fi
else
    print_success ".env file already exists ✅"
fi

# Step 3: Run database migrations
print_status "Running database migrations..."
cd src
if uv run python manage.py migrate; then
    print_success "Database migrations completed ✅"
else
    print_error "Database migration failed ❌"
    exit 1
fi

# Step 4: Setup initial data
print_status "Setting up initial data..."
if uv run python manage.py setup_initial_data; then
    print_success "Initial data setup completed ✅"
else
    print_warning "Initial data setup failed, but continuing..."
fi

# Step 5: Collect static files (if needed)
print_status "Collecting static files..."
if uv run python manage.py collectstatic --noinput; then
    print_success "Static files collected ✅"
else
    print_warning "Static files collection failed, but continuing..."
fi

cd ..

echo ""
echo "🎉 Setup completed successfully!"
echo "=================================="
echo ""
echo "📝 Default Login Credentials:"
echo "  Superuser: admin@example.com / admin123"
echo "  CS Admin: cs.admin@university.edu / admin123"  
echo "  BA Admin: ba.admin@university.edu / admin123"
echo "  Student 1: student1@university.edu / student123"
echo "  Student 2: student2@university.edu / student123"
echo ""
echo "🚀 To start the development server:"
echo "  cd $(pwd)"
echo "  uv run python src/manage.py runserver"
echo ""
echo "🌐 Then open your browser and go to:"
echo "  http://localhost:8000"
echo ""
echo "📚 For more information, check the README.md file"
echo ""
print_success "Happy coding! 🎓✨"
