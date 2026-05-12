# Student Grievance Management System

A production-ready Django web application for managing student grievances with role-based access control, automated assignment, OTP-based authentication, and real-time notifications.

> Deploy anywhere — Render, Railway, Fly.io, VPS, or any platform that supports Python/Django.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Setup](#1-environment-setup)
  - [Local Development](#2-local-development)
  - [Production Deployment](#3-production-deployment)
- [Environment Variables](#environment-variables)
- [System Workflows](#system-workflows)
- [API Endpoints](#api-endpoints)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Student Portal
- Secure registration with university email verification (OTP)
- Submit grievances with file attachments and category selection
- Real-time grievance status tracking with timeline
- Communication thread with administrators
- Resolution feedback and rating system
- Real-time in-app notifications
- Profile management

### Admin Panel
- Role-based access control — **Super Admin**, **Department Admin**, **Grievance Officer**
- Comprehensive dashboard with analytics and charts
- Automated grievance assignment based on department, category, and keywords
- User management — approve registrations, manage roles
- Department and category management with auto-assignment rules
- Complete audit logging for all administrative actions
- Reports and data export capabilities
- Email notification system

### System Highlights
- OTP-based login for students — no passwords stored in plain text
- Superadmin auto-provisioned from environment variables on deployment
- Django built-in /admin panel fully removed — custom admin panel only
- Production-ready with Gunicorn, WhiteNoise, and PostgreSQL
- Responsive design (Bootstrap 5)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 5.2, Django REST Framework |
| **Database** | PostgreSQL (Neon) — no SQLite |
| **Frontend** | HTML, CSS, JavaScript, Bootstrap 5 |
| **Static Files** | WhiteNoise |
| **Production Server** | Gunicorn |
| **Package Manager** | [uv](https://docs.astral.sh/uv/) |
| **Task Queue** | Celery + Redis (optional) |
| **Deployment** | Render |
| **Authentication** | Custom User model with OTP email verification |

---

## Project Structure

```
Student_Grievance_Management_System/
├── .env                    # Local environment variables (git-ignored)
├── .env.example            # Template for environment variables
├── build.sh                # Render build script (deps + migrate + superuser)
├── pyproject.toml          # Python dependencies and project metadata
├── uv.lock                 # Locked dependency versions
│
└── src/                    # Django project root
    ├── manage.py
    ├── config/             # Django project configuration
    │   ├── settings.py     # All settings (DB, email, security, etc.)
    │   ├── urls.py         # Root URL routing
    │   └── wsgi.py         # WSGI entry point for Gunicorn
    │
    ├── apps/
    │   ├── authentication/ # Custom User model, login, OTP, registration
    │   ├── students/       # StudentProfile, AdminProfile, School, Department
    │   ├── grievances/     # Grievance model, categories, comments, attachments
    │   ├── admin_panel/    # Admin dashboard, user management, reports, audit logs
    │   └── notifications/  # In-app and email notifications
    │
    ├── templates/          # Django HTML templates
    │   ├── authentication/ # Login, registration, OTP verification pages
    │   ├── students/       # Student dashboard and profile
    │   ├── grievances/     # Grievance forms, detail, and listing
    │   └── admin_panel/    # Admin interface (dashboard, users, settings)
    │
    ├── static/             # CSS, JavaScript, images
    │   ├── css/style.css
    │   └── js/main.js
    │
    └── staticfiles/        # Collected static files (auto-generated)
```

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — Modern Python package manager
- **PostgreSQL database** — [Neon](https://neon.tech) (free tier available)
- **Gmail account** with an [App Password](https://myaccount.google.com/apppasswords) for SMTP

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/Surventurer/Student_Grievance_Management_System.git
cd Student_Grievance_Management_System

# Install dependencies
uv sync

# Create your environment file
cp .env.example .env
```

Edit `.env` with your actual values. See the [Environment Variables](#environment-variables) section for details.

### 2. Local Development

```bash
# Apply database migrations
uv run src/manage.py migrate

# Create superadmin using your .env values
uv run src/manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.students.models import AdminProfile
from decouple import config

User = get_user_model()
email = config('DJANGO_SUPERUSER_EMAIL')
password = config('DJANGO_SUPERUSER_PASSWORD')
verified = config('DJANGO_SUPERUSER_EMAIL_VERIFIED', default='True') == 'True'

user, created = User.objects.get_or_create(
    email=email,
    defaults={'is_staff': True, 'is_superuser': True, 'role': 'superadmin', 'is_email_verified': verified}
)
if created:
    user.set_password(password)
    user.save()
    print(f'Superuser {email} created')
else:
    user.is_email_verified = verified
    user.save()
    print(f'Superuser {email} updated')

AdminProfile.objects.get_or_create(
    user=user,
    defaults={'role_level': 'superadmin', 'employee_id': 'SUPERADMIN-01', 'department': 'Administration'}
)
"

# Start the development server
uv run src/manage.py runserver 127.0.0.1:8000
```

Open **http://127.0.0.1:8000** in your browser.

> **Important:** Always use `http://` (not `https://`). The Django dev server does not support HTTPS.

#### Dev Mode Notes
- `DEBUG=True` in `.env` enables detailed error pages and serves static files automatically
- Django's built-in /admin panel is **disabled** — use the custom admin panel at /admin-panel/
- OTP codes are sent to the configured `EMAIL_HOST_USER` Gmail account
- The superadmin's email verification status is controlled by `DJANGO_SUPERUSER_EMAIL_VERIFIED` in `.env`

### 3. Production Deployment

This project can be deployed on **any platform** that supports Python/Django. Below are the general steps followed by platform-specific notes.

#### Step 1 — Get a PostgreSQL Database
You need a PostgreSQL database. Some options:
- [Neon](https://neon.tech) — Free serverless PostgreSQL
- [Railway](https://railway.app) — Built-in PostgreSQL add-on
- [Supabase](https://supabase.com) — Free tier PostgreSQL
- Self-hosted PostgreSQL on any VPS

#### Step 2 — Set Environment Variables

Set these environment variables on your hosting platform's dashboard:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your PostgreSQL connection string |
| `SECRET_KEY` | A long random string (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | Your production domain (e.g., `my-app.onrender.com` or `my-app.up.railway.app`) |
| `CSRF_TRUSTED_ORIGINS` | Your production URL with protocol (e.g., `https://my-app.onrender.com`) |
| `DJANGO_SUPERUSER_EMAIL` | Your admin email |
| `DJANGO_SUPERUSER_PASSWORD` | Your admin password |
| `DJANGO_SUPERUSER_EMAIL_VERIFIED` | `True` |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST_USER` | Your Gmail address |
| `EMAIL_HOST_PASSWORD` | Your Gmail App Password |
| `SECURE_SSL_REDIRECT` | `True` |
| `PYTHON_VERSION` | `3.12.11` |

#### Step 3 — Build and Start Commands

| Command | Value |
|---------|-------|
| **Build** | `./build.sh` |
| **Start** | `gunicorn --chdir src config.wsgi:application` |

The `build.sh` script automatically:
1. Installs dependencies via `uv sync --frozen`
2. Collects static files
3. Runs database migrations
4. Creates/updates the superadmin with verified email

#### Platform-Specific Notes

| Platform | Notes |
|----------|-------|
| **Render** | Set Build Command to `./build.sh`, Start Command to `gunicorn --chdir src config.wsgi:application`. Add env vars in the dashboard. |
| **Railway** | Connect your GitHub repo, set the same build/start commands. Add a PostgreSQL plugin or use an external DB. |
| **Fly.io** | Create a `fly.toml` config, set env vars with `fly secrets set`. Use `fly postgres create` for a database. |
| **VPS (Ubuntu)** | Install Python 3.12, uv, Nginx. Run `./build.sh` then use `gunicorn` with systemd + Nginx as reverse proxy. |

#### Production Security
- `DEBUG=False` — no error details exposed
- `SECURE_SSL_REDIRECT=True` — forces HTTPS
- HSTS headers enabled with 1-year max-age
- Django `/admin` panel is completely removed from URL routing
- CSRF trusted origins configured via `CSRF_TRUSTED_ORIGINS` env var
- Static files served via WhiteNoise with compression

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | insecure default | Django secret key — **must change in production** |
| `DEBUG` | Yes | `True` | `True` for dev, `False` for production |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated allowed hostnames |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `CSRF_TRUSTED_ORIGINS` | No | localhost URLs | Comma-separated production URLs with protocol |
| `EMAIL_BACKEND` | No | console backend | `django.core.mail.backends.smtp.EmailBackend` for real emails |
| `EMAIL_HOST_USER` | Yes | — | Gmail address for sending OTPs |
| `EMAIL_HOST_PASSWORD` | Yes | — | Gmail App Password (16 characters) |
| `DJANGO_SUPERUSER_EMAIL` | No | — | Auto-create superadmin with this email |
| `DJANGO_SUPERUSER_PASSWORD` | No | — | Password for auto-created superadmin |
| `DJANGO_SUPERUSER_EMAIL_VERIFIED` | No | `True` | Skip OTP for superadmin if `True` |
| `SECURE_SSL_REDIRECT` | No | `True` (prod) | Set `False` for local development |
| `PYTHON_VERSION` | No | — | Python version hint for hosting platforms |

---

## System Workflows

### Student Workflow
1. **Register** — Student signs up with university email
2. **Verify Email** — Receives OTP, verifies email address
3. **Submit Grievance** — Selects category, describes issue, attaches files
4. **Auto-Assignment** — System assigns to the appropriate department admin
5. **Track Progress** — Views timeline updates and communicates with admin
6. **Feedback** — Rates resolution after grievance is closed

### Admin Workflow
1. **Login** — Admins log in with OTP-verified credentials
2. **Dashboard** — View assigned grievances, statistics, and alerts
3. **Review** — Read grievance details, attachments, and student info
4. **Action** — Update status, add comments, escalate, or reassign
5. **Resolve** — Mark as resolved with solution details
6. **Reports** — Generate analytics and export data

### Auto-Assignment Logic
1. **Department Match** — Routes to admin of the student's department
2. **Category Rules** — Uses category-specific assignment configurations
3. **Keyword Analysis** — Scans grievance content for routing keywords
4. **Fallback** — Assigns to superadmin if no match is found

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/auth/login/` | Login page |
| `POST` | `/auth/login/` | Submit login credentials + OTP |
| `GET` | `/auth/student-registration/` | Registration page |
| `POST` | `/auth/student-registration/` | Submit registration |
| `GET` | `/auth/verify-student-email/` | Email OTP verification |
| `GET` | `/auth/logout/` | Logout |

### Student Panel
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/students/` | Student dashboard |
| `GET` | `/students/profile/` | Student profile |
| `GET` | `/students/api/notifications/` | Fetch notifications (JSON) |

### Grievances
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/grievances/` | List student's grievances |
| `POST` | `/grievances/submit/` | Submit new grievance |
| `GET` | `/grievances/<id>/` | Grievance detail |

### Admin Panel
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin-panel/dashboard/` | Admin dashboard |
| `GET` | `/admin-panel/profile/` | Admin profile |
| `GET` | `/admin-panel/grievances/` | Grievance management |
| `GET` | `/admin-panel/manage/` | Department management |
| `GET` | `/admin-panel/superadmin/users/` | User management (superadmin) |
| `GET` | `/admin-panel/superadmin/settings/` | System settings (superadmin) |

---

## Security

| Feature | Implementation |
|---------|---------------|
| **Authentication** | OTP-based email verification, no plain-text password login flow for students |
| **Authorization** | Role-based access control with `@role_required` decorator |
| **CSRF Protection** | Django CSRF middleware with trusted origins |
| **SQL Injection** | Django ORM parameterized queries |
| **XSS Prevention** | Django template auto-escaping |
| **HTTPS** | `SECURE_SSL_REDIRECT` + HSTS in production |
| **Audit Trail** | Complete logging of all admin actions |
| **File Uploads** | Size-limited (10MB), type-validated |
| **Admin Panel** | Django's built-in `/admin` is fully disabled |
| **Session Security** | Secure cookies in production |

---

## Testing

```bash
# Start dev server
uv run src/manage.py runserver 127.0.0.1:8000

# Test student flow
# 1. Register at /auth/student-registration/
# 2. Verify email with OTP
# 3. Submit a grievance

# Test admin flow
# 1. Login with superadmin credentials from .env
# 2. View dashboard, manage grievances, check profile
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'django'` | Run `uv sync` to install dependencies |
| HTTPS errors in dev server terminal | Use `http://` not `https://`. Clear Chrome HSTS at `chrome://net-internals/#hsts` |
| CSRF token errors | Clear browser cookies for localhost/127.0.0.1 |
| `DATABASE_URL` missing | Ensure `.env` file exists with a valid PostgreSQL connection string |
| OTP not received | Check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` (must be Gmail App Password) |
| Superadmin can't login | Verify `DJANGO_SUPERUSER_EMAIL_VERIFIED=True` in `.env` |
| Static files not loading in production | Run `uv run src/manage.py collectstatic --no-input` |
| Migration conflicts | Reset your DB: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` then redeploy |

---

**Built with Django — deploy anywhere**
