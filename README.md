# Student Grievance Management System

A comprehensive Django-based web application for managing student grievances with role-based access control, automated assignment, and notification system.

## Features

### Student Panel
- Secure registration and login with OTP verification
- Submit grievances with file attachments
- Track grievance status and timeline
- Communication thread with admins
- Resolution feedback system
- Profile management

### Admin Panel
- Role-based access control (Super Admin, Department Admin, Grievance Officer)
- Dashboard with analytics
- Automated grievance assignment
- Manual assignment for "other" category
- Student and category management
- Reports and analytics
- Audit logging
- Email notifications

## Technology Stack

- **Backend**: Django 4.2+
- **Package Manager**: UV
- **Database**: PostgreSQL (configurable)
- **Task Queue**: Celery with Redis
- **Authentication**: Django Auth with custom user model
- **API**: Django REST Framework

## Installation

1. Clone the repository
2. Install UV if not already installed:
   ```bash
   pip install uv
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   ```

5. Run migrations:
   ```bash
   uv run python manage.py migrate
   ```

6. Create superuser:
   ```bash
   uv run python manage.py createsuperuser
   ```

7. Run the development server:
   ```bash
   uv run python manage.py runserver
   ```

## Project Structure

```
src/
├── config/                 # Django settings
├── apps/
│   ├── authentication/     # Custom user model and auth
│   ├── students/           # Student and admin profiles
│   ├── grievances/         # Grievance management
│   ├── admin_panel/        # Admin functionality
│   └── notifications/      # Email/notification system
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
└── media/                  # User uploads
```

## Usage

### For Students
1. Register with student ID and email
2. Verify email with OTP
3. Submit grievances with category selection
4. Track progress and communicate with admins
5. Provide feedback on resolution

### For Admins
1. Login with admin credentials
2. View dashboard with grievance statistics
3. Manage assigned grievances
4. Communicate with students
5. Generate reports and analytics

## API Endpoints

The system provides RESTful API endpoints for:
- Authentication and user management
- Grievance CRUD operations
- Comments and communication
- Reports and analytics
- Admin operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
