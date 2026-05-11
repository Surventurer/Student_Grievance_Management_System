# Student Grievance Management System

A comprehensive Django-based web application for managing student grievances with role-based access control, automated assignment, and notification system.

## 🚀 Quick Start

1. **Clone and setup the project:**
   ```bash
   cd Student_Grievance_Management_System
   uv sync  # Install dependencies
   ```

2. **Setup the database:**
   ```bash
   uv run python src/manage.py migrate
   uv run python src/manage.py setup_initial_data
   ```

3. **Start the server:**
   ```bash
   uv run python src/manage.py runserver
   ```

4. **Access the system:**
   - Open your browser and go to: `http://localhost:8000`
   - Use the login credentials provided below

## 🔐 Default Login Credentials

After running the setup command, you can log in with these accounts:

### Admin Accounts
- **Superuser:** admin@example.com / admin123
- **CS Department Admin:** cs.admin@university.edu / admin123
- **Business Department Admin:** ba.admin@university.edu / admin123

### Student Accounts  
- **Student 1:** student1@university.edu / student123
- **Student 2:** student2@university.edu / student123

## ✨ Features

### Student Panel
- ✅ Secure registration and login with email verification
- ✅ Submit grievances with file attachments
- ✅ Track grievance status and timeline
- ✅ Communication thread with admins
- ✅ Resolution feedback system
- ✅ Profile management
- ✅ Real-time notifications

### Admin Panel
- ✅ Role-based access control (Super Admin, Department Admin, Grievance Officer)
- ✅ Comprehensive dashboard with analytics
- ✅ Automated grievance assignment based on categories and keywords
- ✅ Manual assignment for complex cases
- ✅ Student and department management
- ✅ Category management with auto-assignment rules
- ✅ Reports and analytics with data visualization
- ✅ Complete audit logging system
- ✅ Email notifications
- ✅ CRUD operations for all entities

### System Features
- ✅ Automated grievance categorization and assignment
- ✅ Multi-level approval workflows
- ✅ File upload and attachment management
- ✅ Timeline tracking for all grievances
- ✅ Advanced search and filtering
- ✅ Data export capabilities
- ✅ Security audit trails

## 🏗️ Technology Stack

- **Backend:** Django 4.2+
- **Database:** SQLite (default) / PostgreSQL (production)
- **Package Manager:** UV (modern Python package manager)
- **Frontend:** HTML, CSS, JavaScript (Bootstrap 5)
- **Task Queue:** Celery with Redis
- **Authentication:** Django Auth with custom user model
- **API:** Django REST Framework

## 📁 Project Structure

```
src/
├── config/                 # Django project settings
│   ├── settings.py         # Main configuration
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI application
├── apps/
│   ├── authentication/    # User authentication & authorization
│   │   ├── models.py      # User model and auth-related models
│   │   ├── views.py       # Login, registration, password reset
│   │   ├── forms.py       # Authentication forms
│   │   └── urls.py        # Auth URL patterns
│   ├── students/          # Student and admin profiles
│   │   ├── models.py      # StudentProfile, AdminProfile, School, Department
│   │   ├── views.py       # Profile management, dashboards
│   │   └── context_processors.py # Global context data
│   ├── grievances/        # Core grievance management
│   │   ├── models.py      # Grievance, Category, Comments, Attachments
│   │   ├── views.py       # Grievance CRUD, submission, tracking
│   │   └── urls.py        # Grievance-related URLs
│   ├── admin_panel/       # Administrative functionality
│   │   ├── views.py       # Admin dashboard, user management, reports
│   │   ├── audit_utils.py # Audit logging utilities
│   │   └── urls.py        # Admin panel URLs
│   └── notifications/     # Notification system
│       ├── models.py      # Email notifications, read status
│       └── views.py       # Notification management
├── templates/             # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── authentication/   # Login, registration templates
│   ├── students/         # Student dashboard and profile
│   ├── grievances/       # Grievance forms and details
│   └── admin_panel/      # Admin interface templates
└── static/               # CSS, JavaScript, images
    ├── css/style.css     # Custom styling
    └── js/main.js        # Interactive functionality
```

## 🎯 System Workflows

### Student Workflow
1. **Registration:** Student registers with university email
2. **Email Verification:** Verifies email with OTP
3. **Submit Grievance:** Fills form with category selection
4. **Auto Assignment:** System automatically assigns to appropriate admin
5. **Tracking:** Student tracks progress and communicates with admin
6. **Resolution:** Student provides feedback on resolution

### Admin Workflow
1. **Login:** Admin logs in to dedicated panel
2. **Dashboard:** Views assigned grievances and statistics
3. **Review:** Reviews grievance details and attachments
4. **Action:** Updates status, adds comments, requests more info
5. **Resolution:** Marks as resolved with solution details
6. **Analytics:** Generates reports and tracks performance

### Auto-Assignment Logic
1. **Department Matching:** Matches student's department with admin
2. **Category Assignment:** Uses category-specific assignments
3. **Keyword Analysis:** Analyzes grievance content for keywords
4. **Priority Rules:** Applies priority-based assignment rules
5. **Fallback Logic:** Uses default admins when no match found

## 📊 Key Features Detail

### Dashboard Analytics
- Real-time grievance statistics
- Category-wise distribution charts
- Resolution time analytics
- Department performance metrics
- Trend analysis with historical data

### Security Features
- Complete audit trail for all actions
- Role-based access control
- Session management
- File upload security
- SQL injection protection
- XSS prevention

### Notification System
- Email notifications for new grievances
- Status update notifications
- Real-time in-app notifications
- Admin assignment notifications
- Escalation alerts

## 🔧 Advanced Configuration

### Environment Variables (.env)
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite default)
DATABASE_URL=sqlite:///db.sqlite3

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis for Celery (optional)
REDIS_URL=redis://localhost:6379/0
```

### Database Migration
```bash
# Create new migrations
uv run python src/manage.py makemigrations

# Apply migrations  
uv run python src/manage.py migrate

# Reset database (if needed)
rm src/db.sqlite3
uv run python src/manage.py migrate
uv run python src/manage.py setup_initial_data
```

### Custom Management Commands
```bash
# Setup initial data
uv run python src/manage.py setup_initial_data

# Populate sample categories
uv run python src/manage.py populate_categories

# Create superuser manually
uv run python src/manage.py createsuperuser
```

## 🚀 Deployment

### Development
```bash
uv run python src/manage.py runserver 0.0.0.0:8000
```

### Production (with Gunicorn)
```bash
pip install gunicorn
gunicorn --chdir src config.wsgi:application
```

## 📝 API Endpoints

The system provides RESTful API endpoints:

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/verify-email/` - Email verification

### Grievances
- `GET /api/grievances/` - List grievances
- `POST /api/grievances/` - Submit new grievance
- `GET /api/grievances/{id}/` - Get grievance details
- `PUT /api/grievances/{id}/` - Update grievance
- `POST /api/grievances/{id}/comments/` - Add comment

### Admin Operations
- `GET /api/admin-panel/dashboard/` - Admin dashboard data
- `GET /api/admin-panel/users/` - User management
- `GET /api/admin-panel/reports/` - Generate reports
- `POST /api/admin-panel/assign/` - Manual assignment

## 🧪 Testing

### Manual Testing
1. Start the server: `uv run python src/manage.py runserver`
2. Open browser and navigate to `http://localhost:8000`
3. Test with provided demo accounts
4. Submit test grievances as students
5. Process grievances as admin

### Test Data
The system comes with pre-configured:
- 2 Schools (Engineering, Business)  
- 2 Departments (Computer Science, Business Admin)
- 2 Admin users (department-specific)
- 2 Student users
- 5 Grievance categories with auto-assignment rules

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🆘 Support

If you encounter any issues:

1. Check the Django logs in the terminal
2. Verify all migrations are applied
3. Ensure sample data is loaded
4. Check file permissions
5. Verify environment variables

For additional help, please create an issue in the repository.

---

**🎉 Congratulations! Your Student Grievance Management System is now ready to use!**
