# 🎓 Student Grievance Management System (SGMS)

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-0C4B33.svg?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Channels](https://img.shields.io/badge/Channels-4.2-orange.svg?logo=websocket&logoColor=white)](https://channels.readthedocs.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon_Cloud-336791.svg?logo=postgresql&logoColor=white)](https://neon.tech/)
[![Redis](https://img.shields.io/badge/Redis-Cache_%26_Broker-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-SLA_Escalation-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Production_Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)

A comprehensive, institutional-grade **Student Grievance Management System (SGMS)** built with Python, Django ASGI (Daphne), WebSockets, Celery, and PostgreSQL. Designed to comply with statutory university grievance guidelines (such as UGC, AICTE, and ISO 10002 quality management standards).

---

## 📑 Table of Contents

- [Key Capabilities](#-key-capabilities)
- [System Architecture](#-system-architecture)
- [Role-Based Access Control (RBAC)](#-role-based-access-control-rbac)
- [Institutional Standards Compliance](#-institutional-standards-compliance)
- [Tech Stack](#-tech-stack)
- [Directory Structure](#-directory-structure)
- [Environment Configuration](#-environment-configuration)
- [Local Development Guide](#-local-development-guide)
- [Production Deployment Guide](#-production-deployment-guide)
- [Default Seed Accounts](#-default-seed-accounts)
- [Security & Hardening](#-security--hardening)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Key Capabilities

### 👨‍🎓 Student Portal
* **Verified Registration**: Self-registration with email OTP verification before account activation.
* **Grievance Lodging**: Structured lodging with category classification (Academic vs. Non-Academic), file attachments, and email OTP verification.
* **Whistleblower Anonymous Mode**: Students can submit grievances anonymously; personal identifiers are strictly masked across all UI views and exports.
* **Real-time Live Chat**: Interactive WebSocket communication thread directly with assigned grievance officers.
* **Student Right of Appeal**: Option to lodge formal appeals on unsatisfactory or rejected resolutions with additional grounds and supporting files.
* **Resolution Feedback**: Post-resolution 5-star rating and qualitative feedback.

### 🏛️ Admin & Grievance Officer Portal
* **Granular Role Hierarchy**: Strict boundaries between **Superadmin**, **Department Admin**, and **Grievance Officer**.
* **Department Data Isolation**: Department admins and officers only access grievances belonging to their assigned department.
* **Automated Assignment Engine**: Smart grievance routing based on category rules, keywords, and officer workload.
* **Dynamic Priority-Weighted SLA**:
  * Urgent: 25% of baseline SLA hours
  * High: 50% of baseline SLA hours
  * Medium: 100% of baseline SLA hours
  * Low: 150% of baseline SLA hours
* **SLA Pause Capability**: Automatically pauses SLA clock when a grievance status transitions to `pending_student` (Awaiting Student Input).
* **Multi-Tier Escalation Engine**: Automated Celery task escalates unresolved grievances:
  * **Level 0**: Assigned Officer
  * **Level 1**: Department Admin / Head of Department (HOD)
  * **Level 2**: Superadmin / Appellate Authority
* **Bulk Administrative Actions**: Bulk status updates and bulk reassignments strictly validated within department boundaries.
* **Auditing & Reporting**: Immutable audit logging for all status changes, reassignments, and administrative actions; CSV / Excel export capabilities.

---

## 🏗️ System Architecture

```
                                  +-----------------------+
                                  |     Browser Client    |
                                  +-----------+-----------+
                                              |
                          HTTP / HTTPS        |       WebSockets (WSS)
                                              |
                                              v
                              +---------------+---------------+
                              |     Daphne ASGI Server        |
                              |        (Port 8000)            |
                              +---------------+---------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
                     v                                                 v
        +------------+------------+                      +-------------+-------------+
        |   Django Core App       |                      |   Django Channels Layer   |
        |   (Views, Auth, ORM)    |                      |   (Real-time Chat Socket) |
        +------------+------------+                      +-------------+-------------+
                     |                                                 |
                     +------------------------+------------------------+
                                              |
                     +------------------------+------------------------+
                     |                        |                        |
                     v                        v                        v
        +------------+------------+ +---------+---------+ +------------+------------+
        |  PostgreSQL Database    | |   Redis Cache     | |   Celery Background     |
        |  (Neon Cloud / SSL)     | |   & Channel Layer | |   Worker & Celery Beat  |
        +-------------------------+ +-------------------+ +-------------------------+
```

---

## 👥 Role-Based Access Control (RBAC)

| Role | Scope | Permitted Actions |
| :--- | :--- | :--- |
| **Student** | Self | Submit grievances, track progress, chat via WebSockets, file appeals, submit ratings. |
| **Grievance Officer** | Assigned Tickets | Review assigned tickets, add public comments / internal notes, update ticket statuses. |
| **Department Admin** | Department-wide | View all department grievances, assign/reassign within department, review initial appeals, manage department officers. |
| **Superadmin** | Institution-wide | Manage schools & departments, manage categories & SLAs, adjudicate Level-2 appeals, view audit logs, assign HODs. |

---

## 🛡️ Institutional Standards Compliance

1. **UGC / AICTE Grievance Guidelines**: Multi-tiered escalation pathway with supervisory appeals.
2. **ISO 10002 Quality Standards**: Systematic tracking of customer feedback, root cause notes, and resolution timeliness.
3. **Whistleblower Protection**: Anonymity flag masks student identity across all UI panels and data exports.
4. **Account Soft-Deletion**: User accounts are soft-deleted with audit preservation to maintain full accountability.

---

## 💻 Tech Stack

* **Web Framework**: Django 5.2 & Django REST Framework
* **ASGI Server**: Daphne 4.1 (Unified HTTP + WebSockets)
* **Real-time Engine**: Django Channels 4.2 + channels-redis 4.2
* **Database**: PostgreSQL (Neon Serverless PostgreSQL recommended)
* **Cache & Message Broker**: Redis 7+
* **Task Queue & Scheduler**: Celery 5.3+ & django-celery-beat 2.5+
* **Package Management**: [uv](https://docs.astral.sh/uv/) (Astral)
* **Static Assets**: WhiteNoise with compression
* **Styling**: Bootstrap 5 + Bootstrap Icons

---

## 📂 Directory Structure

```
Student_Grievance_Management_System/
├── .env                         # Local development environment variables
├── proud.env                    # Production environment configuration
├── prod.env                     # Production environment alias
├── .env.example                 # Environment template with instructions
├── .gitignore                   # Comprehensive ignore rules
├── .dockerignore                # Excludes secrets & virtual environments
├── Dockerfile                   # Multi-stage production container image
├── docker-compose.yml           # Complete orchestration (Web, Redis, Celery, Beat)
├── pyproject.toml               # Modern Python dependencies (uv / pip)
├── uv.lock                      # Deterministic lockfile
├── src/
│   ├── manage.py
│   ├── config/                  # Project configuration (settings, asgi, urls, celery)
│   ├── apps/
│   │   ├── authentication/      # Custom User model, HMAC-SHA256 2FA, OTP flows
│   │   ├── students/            # StudentProfile, AdminProfile, School, Department
│   │   ├── grievances/          # Grievance models, SLA tasks, WebSocket consumers
│   │   ├── admin_panel/         # RBAC views, analytics, department management
│   │   └── notifications/       # Multi-channel notification delivery
│   ├── templates/               # Responsive HTML templates
│   └── static/                  # Stylesheets, JavaScript, icons
```

---

## ⚙️ Environment Configuration

The application requires environment variables to run. Three pre-configured files are provided:

* `.env` — For local development (debug enabled, console email OTPs).
* `proud.env` / `prod.env` — For production deployments (debug disabled, SMTP enabled, secure cache).
* `.env.example` — Documented reference template.

### Key Environment Variables

| Variable | Dev Default | Production Example | Description |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | Development Key | `django-insecure-...` | Cryptographic signing key |
| `DEBUG` | `True` | `False` | Toggle developer debug mode |
| `ALLOWED_HOSTS` | `*` | `sgms.university.edu,127.0.0.1` | Allowed HTTP Host headers |
| `DATABASE_URL` | Neon connection string | `postgresql://...` | PostgreSQL connection URL |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | `redis://redis:6379/0` | Redis broker and cache URL |
| `EMAIL_BACKEND` | `...console.EmailBackend` | `...smtp.EmailBackend` | Email delivery driver |
| `EMAIL_HOST_USER` | — | `notifications@university.edu` | SMTP username / Gmail address |
| `EMAIL_HOST_PASSWORD`| — | `16-char-app-password` | SMTP password / App Password |
| `CSRF_TRUSTED_ORIGINS`| `http://localhost:8000` | `https://sgms.university.edu` | CSRF allowed origin URLs |
| `SECURE_SSL_REDIRECT` | `False` | `False` (behind proxy) / `True` | Enforce HTTPS redirects |

---

## 🛠️ Local Development Guide

### Option 1: Native Run with `uv` (Recommended)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Surventurer/Student_Grievance_Management_System.git
   cd Student_Grievance_Management_System
   ```

2. **Install Dependencies**:
   ```bash
   # Install uv if not already present
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install all packages
   uv sync
   ```

3. **Verify Environment**:
   Ensure `.env` exists in the project root:
   ```bash
   cp .env.example .env
   ```

4. **Apply Database Migrations**:
   ```bash
   uv run src/manage.py migrate
   ```

5. **Seed Initial Department & Test Accounts**:
   ```bash
   uv run src/manage.py setup_initial_data
   ```

6. **Start the ASGI Server (Daphne)**:
   ```bash
   uv run daphne -b 127.0.0.1 -p 8000 --root-path=src config.asgi:application
   ```
   *Alternatively, standard Django dev server:*
   ```bash
   uv run src/manage.py runserver 127.0.0.1:8000
   ```

7. **Start Celery Worker & Beat (Optional for local testing)**:
   ```bash
   # Terminal 2 - Celery Worker
   uv run celery -A config --workdir src worker --loglevel=info

   # Terminal 3 - Celery Beat (SLA Scheduler)
   uv run celery -A config --workdir src beat --loglevel=info
   ```

---

## 🐳 Production Deployment Guide

### Deploying with Docker Compose (Recommended)

The system includes a production-ready `docker-compose.yml` that orchestrates:
1. **Daphne Web App**: Serves HTTP and WebSocket connections.
2. **Celery Worker**: Asynchronous email delivery and grievance assignments.
3. **Celery Beat**: Periodic SLA monitoring and auto-escalations.
4. **Redis 7**: Cache, session store, channel layer, and message broker.

1. **Prepare Production Environment**:
   Ensure your production values are in `proud.env` (or `prod.env`):
   ```bash
   cp .env.example proud.env
   # Edit proud.env with your real credentials
   ```

2. **Launch with Docker Compose**:
   ```bash
   # Start all services using proud.env
   ENV_FILE=proud.env docker compose up -d --build
   ```

3. **Verify Service Health**:
   ```bash
   docker compose ps
   ```

4. **Seed Production Baseline Data (First Run Only)**:
   ```bash
   docker compose exec web python manage.py setup_initial_data
   ```

5. **View Logs**:
   ```bash
   docker compose logs -f web
   ```

---

## 🔑 Default Seed Accounts

Running `python manage.py setup_initial_data` creates the following test accounts:

| Role | Email | Password | Department |
| :--- | :--- | :--- | :--- |
| **Superadmin** | `admin@example.com` | `admin123` | Institutional Administration |
| **Department Admin** | `cs.admin@university.edu` | `admin123` | Computer Science |
| **Department Admin** | `ba.admin@university.edu` | `admin123` | Business Administration |
| **Student 1** | `student1@university.edu` | `student123` | Computer Science |
| **Student 2** | `student2@university.edu` | `student123` | Business Administration |

> ⚠️ **IMPORTANT**: Change all default passwords immediately after deploying to production!

---

## 🔒 Security & Hardening

* **Fail-Closed Security Cache**: Rate limiting and Staff 2FA state are backed by a strict fail-closed Redis layer (`security_cache_get`). In production, an outage in the caching tier will safely reject authentication requests rather than permitting an unauthenticated bypass.
* **HMAC-SHA256 Staff 2FA**: Staff one-time passcodes are verified using constant-time digest comparisons against a secret-keyed HMAC token (`hash_staff_otp`).
* **Strict IDOR Mitigation**: All administrative endpoints (`bulk_delete_grievances`, `update_grievance_status`, `bulk_reassign_grievances`) validate target records against `request.user.get_accessible_grievances()`.
* **Privilege Escalation Prevention**: Non-superadmin staff cannot modify or grant the `superadmin` role via any API or web endpoint.
* **MIME-Type & Extension Upload Validation**: Uploaded documents are verified against whitelisted MIME types and file extensions (PDF, DOC, DOCX, JPG, PNG, TXT) with a hard 10MB ceiling.
* **Protected Media Serving**: Grievance attachments are protected and streamed via authenticated views or secure fallback handlers.

---

## ❓ Troubleshooting

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `Redis ConnectionError` | Redis server not running | Start Redis locally via `redis-server` or use Docker Compose (`docker compose up -d redis`). |
| `CSRF verification failed` | Missing origin in `CSRF_TRUSTED_ORIGINS` | Add your exact protocol and domain to `CSRF_TRUSTED_ORIGINS` in `.env` or `proud.env`. |
| `WebSocket connection failed` | Running via Gunicorn/WSGI instead of Daphne | Run with Daphne: `daphne -b 0.0.0.0 -p 8000 config.asgi:application`. |
| Emails / OTPs not arriving | SMTP credentials not set | In development, check terminal console output for OTPs (`EMAIL_BACKEND=console`). In production, verify your Gmail App Password. |
| Permission Denied on Grievance | Cross-department access attempt | Ensure the logged-in staff account matches the department of the grievance. |

---

## 📄 License

This project is licensed under the MIT License. Developed for institutional excellence in student welfare.
