# Student Grievance Management System - Architecture & System Blueprint

**Document Version:** 2.0.0  
**Updated Date:** September 2026  
**Repository:** `Student_Grievance_Management_System`  
**Git Branch:** `beta`  
**Framework:** Django 5.2+ (Python 3.12+) / Daphne ASGI / Channels 4.2+ / PostgreSQL (Neon) / Redis / Celery / Bootstrap 5  

---

## 1. Executive Summary

The **Student Grievance Management System (SGMS)** is an institutional-grade academic compliance and dispute resolution platform designed for universities, colleges, and higher education institutes. The platform enables students to lodge formal grievances across academic, hostel, administrative, and disciplinary domains, while providing role-segregated resolution workflows for Department Heads (HODs), Grievance Officers, Chief Wardens, Wardens, and Superadministrators.

### Core Architectural Capabilities
- **Multi-Tenant Academic Hierarchy:** School → Department → Program structure with self-healing HOD auto-assignment (`Department.auto_assign_hod_if_needed`).
- **5-Tier Deterministic Auto-Assignment Engine:** Intelligently routes grievances based on (1) Department Category Assignments, (2) Title/Description Keywords, (3) Officer Load Balancing, (4) Department HOD Fallback, and (5) Central Cell Superadmin Fallback.
- **Interactive Resolution & Real-Time WebSocket Chat:** Daphne ASGI-powered bi-directional chat threads with file attachment validations, live status badge synchronization, and audit logging.
- **Dynamic SLA & Pause Clock:** Priority multipliers (Urgent: 25%, High: 50%, Medium: 100%, Low: 150%); automatic SLA pausing when status is `pending_student` and resumption upon student response.
- **Student Right of Appeal:** Formal appeal lodging on resolved/rejected grievances up to `max_reopen_count` times, with supervisory re-examination.
- **Support Hours Governance:** Configurable operational schedules (e.g. `Mon-Fri, 9:00 AM - 5:00 PM`, `24/7`, overnight schedules) strictly gating new submissions and student replies.
- **Permanent Dual-Factor OTP Verification:** Mandatory email OTP verification for student self-registration (`TemporaryRegistration`) and grievance lodgment (`GrievanceOTPVerification`).
- **Strict Role-Based Access Control (RBAC) & Security:** HMAC-SHA256 server-secret staff 2FA, brute-force lockout tracking, idle session termination, and department data scoping.

---

## 2. High-Level System Architecture (C4 Component Diagram)

```mermaid
C4Context
    title Student Grievance Management System - System Context Diagram

    Person(student, "Student", "Files grievances, tracks SLA status, appeals decisions, and chats in real time.")
    Person(officer, "Grievance Officer / HOD / Warden", "Investigates, updates status, requests student input, and resolves complaints.")
    Person(admin, "Superadmin", "Configures system settings, support hours, academic hierarchy, roles, and audits.")

    Enterprise_Boundary(sgms_boundary, "Student Grievance Management System") {
        System(daphne_asgi, "Daphne ASGI Server (Port 8000)", "Handles HTTP requests and WebSocket connections (ws:// / wss://).")
        System(django_app, "Django Core Application", "MVC/MVT views, REST API endpoints, RBAC middleware, and business logic.")
        System(channels_layer, "Django Channels Layer", "Real-time chat socket multiplexing (Redis / InMemory fallback).")
        SystemDb(postgres_db, "PostgreSQL Database (Neon)", "Stores users, profiles, grievances, appeals, history, and audit logs.")
        SystemQueue(redis_broker, "Redis Cache & Broker", "Session caching, rate limiting counters, and Celery task broker.")
        System(celery_workers, "Celery Workers", "Background tasks: Email OTP dispatch, SLA escalation monitors, session cleanup.")
        System(celery_beat, "Celery Beat Scheduler", "Periodic cron: Automated SLA breach checks, auto-resolve triggers.")
    }

    System_Ext(smtp_server, "SMTP / Email Relay", "Google SMTP / University relay for OTP delivery and grievance alerts.")
    System_Ext(storage_service, "Media File Storage", "Encrypted file storage for grievance evidence and attachments.")

    Rel(student, daphne_asgi, "HTTPS & WebSockets (WSS)", "Browser Client")
    Rel(officer, daphne_asgi, "HTTPS & WebSockets (WSS)", "Admin & Officer UI")
    Rel(admin, daphne_asgi, "HTTPS & WebSockets (WSS)", "Superadmin Portal")

    Rel(daphne_asgi, django_app, "Dispatches HTTP requests", "ASGI Internal")
    Rel(daphne_asgi, channels_layer, "Dispatches WebSocket frames", "ASGI Channels")

    Rel(django_app, postgres_db, "Reads / Writes ORM Entities", "SQL / Port 5432")
    Rel(django_app, redis_broker, "Caches data, rate limits, queues async tasks", "RESP / Port 6379")
    Rel(channels_layer, redis_broker, "Pub/Sub channel groups", "RESP")
    Rel(celery_workers, redis_broker, "Consumes queued jobs", "RESP")
    Rel(celery_workers, postgres_db, "Updates grievance SLA / escalations", "SQL")
    Rel(celery_workers, smtp_server, "Sends emails (OTP, status notifications)", "SMTP / Port 587")
    Rel(celery_beat, redis_broker, "Schedules SLA breach tasks", "RESP")
    Rel(django_app, storage_service, "Stores attachments & appeal files", "File I/O")
```

---

## 3. Entity-Relationship Model (True Schema)

```mermaid
erDiagram
    USER ||--o| STUDENT_PROFILE : "has student profile"
    USER ||--o| ADMIN_PROFILE : "has admin profile"
    USER ||--o{ GRIEVANCE_COMMENT : "authors"
    USER ||--o{ NOTIFICATION : "receives"
    USER ||--o{ AUDIT_LOG : "triggers"
    USER ||--o{ ADMIN_LOGIN_OTP : "authenticates 2FA"
    USER ||--o{ EMAIL_VERIFICATION : "verifies email"
    USER ||--o{ PASSWORD_RESET : "resets password"
    
    SCHOOL ||--o{ DEPARTMENT : "contains"
    DEPARTMENT ||--o{ CATEGORY_ASSIGNMENT : "routes"
    
    CATEGORY ||--o{ GRIEVANCE : "categorizes"
    CATEGORY ||--o{ CATEGORY_ASSIGNMENT : "rules"
    
    STUDENT_PROFILE ||--o{ GRIEVANCE : "lodges"
    STUDENT_PROFILE ||--o{ APPEAL : "files"
    ADMIN_PROFILE ||--o{ GRIEVANCE : "assigned to"
    ADMIN_PROFILE ||--o{ APPEAL : "reviews"
    
    GRIEVANCE ||--o{ GRIEVANCE_ATTACHMENT : "evidence"
    GRIEVANCE ||--o{ GRIEVANCE_COMMENT : "discussion thread"
    GRIEVANCE ||--o{ GRIEVANCE_STATUS_HISTORY : "status audit"
    GRIEVANCE ||--o{ GRIEVANCE_ASSIGNMENT_HISTORY : "assignment audit"
    GRIEVANCE ||--o{ ESCALATION_LOG : "SLA escalation audit"
    GRIEVANCE ||--o{ APPEAL : "has appeals"

    USER {
        int id PK
        string email UK
        string role "student, admin, superadmin, officer"
        boolean is_active
        boolean is_staff
        boolean is_email_verified
        text deactivation_reason
        datetime created_at
    }

    STUDENT_PROFILE {
        int id PK
        int user_id FK
        string name
        string student_id UK "10-digit System ID"
        string school
        string department
        string contact_no
        datetime created_at
    }

    ADMIN_PROFILE {
        uuid id PK
        int user_id FK
        string name
        string role_level "superadmin, admin, officer"
        string department
        string employee_id UK
        string phone
        string office_location
        datetime created_at
    }

    SCHOOL {
        int id PK
        string name UK
        string code UK
        text description
        boolean is_active
        datetime created_at
    }

    DEPARTMENT {
        int id PK
        string name
        int school_id FK
        int head_of_department_id FK
        boolean is_active
        datetime created_at
    }

    CATEGORY {
        uuid id PK
        string name
        string category_type "academic, non_academic"
        uuid default_admin_id FK
        text keywords
        boolean is_active
        boolean auto_assign_enabled
        int sla_hours "default 48"
    }

    CATEGORY_ASSIGNMENT {
        uuid id PK
        uuid category_id FK
        uuid assigned_admin_id FK
        string department
        string school
        int priority_level
        boolean is_active
        text auto_assign_keywords
    }

    GRIEVANCE {
        uuid id PK
        int student_id FK
        string title
        text description
        uuid category_id FK
        string department
        string status "pending, in_progress, pending_student, resolved, rejected"
        string priority "low, medium, high, urgent"
        uuid assigned_to_id FK
        boolean is_anonymous
        boolean is_hosteler
        string hostel_name
        string hostel_room_no
        boolean is_escalated
        int escalation_level "0, 1, 2"
        boolean is_appealed
        boolean is_archived
        datetime sla_pause_time
        int accumulated_sla_pause_minutes
        datetime expected_resolution_date
        datetime actual_resolution_date
        datetime submitted_at
        datetime updated_at
    }

    GRIEVANCE_ATTACHMENT {
        uuid id PK
        uuid grievance_id FK
        string file
        string file_name
        int file_size
        string file_type
        datetime uploaded_at
    }

    GRIEVANCE_COMMENT {
        uuid id PK
        uuid grievance_id FK
        int user_id FK
        string comment_type "comment, status_update, internal_note"
        text message
        boolean is_internal
        datetime timestamp
    }

    APPEAL {
        uuid id PK
        uuid grievance_id FK
        int student_id FK
        text reason
        string status "pending, accepted, rejected"
        uuid reviewed_by_id FK
        text review_notes
        datetime created_at
    }

    SYSTEM_SETTINGS {
        int id PK "1 (Singleton)"
        string system_name
        string contact_email
        int max_file_size "MB"
        boolean email_notifications
        boolean auto_assignment
        boolean allow_student_registration
        string allowed_email_domains
        int session_timeout "minutes"
        int password_min_length
        string default_priority
        int auto_resolve_days
        int escalation_threshold
        boolean allow_anonymous
        int max_reopen_count
        string sla_breach_action
        boolean require_closure_remark
        boolean allow_attachments_in_replies
        string support_hours "Mon-Fri, 9:00 AM - 5:00 PM"
    }

    TEMPORARY_REGISTRATION {
        int id PK
        string name
        string student_id UK
        string email UK
        string password
        string contact_no
        string school
        string department
        string otp
        boolean is_verified
        datetime created_at
        datetime expires_at
    }

    GRIEVANCE_OTP_VERIFICATION {
        int id PK
        string email
        string otp
        string purpose "grievance_submission"
        boolean is_verified
        datetime created_at
    }

    ADMIN_LOGIN_OTP {
        int id PK
        int user_id FK
        string otp
        boolean is_used
        datetime created_at
        datetime expires_at
    }
```

---

## 4. Role-Based Access Control (RBAC) & Boundary Matrix

| Feature / Resource | Student | Grievance Officer | Department Admin / HOD | Superadmin |
| :--- | :---: | :---: | :---: | :---: |
| **Self-Registration (OTP)** | ✅ Full | ❌ (Admin-provisioned) | ❌ (Admin-provisioned) | ❌ (Admin-provisioned) |
| **2FA Staff Login (HMAC)** | ❌ (Direct) | ✅ Required | ✅ Required | ✅ Required |
| **Lodge Grievance** | ✅ Full (Subject to Support Hours) | ❌ | ❌ | ❌ |
| **Anonymous Grievance Lodgment** | ✅ (If enabled in settings) | ❌ | ❌ | ❌ |
| **View Own Grievances** | ✅ Full | ❌ | ❌ | ❌ |
| **View Assigned Grievances** | ❌ | ✅ Assigned Only | ✅ Department Scoped | ✅ University-wide |
| **Update Grievance Status** | ❌ | ✅ Assigned Only | ✅ Department Scoped | ✅ University-wide |
| **Mandatory Closure Remarks** | ❌ | ✅ Enforced | ✅ Enforced | ✅ Enforced |
| **Internal Staff Notes** | ❌ Hidden | ✅ Visible/Writable | ✅ Visible/Writable | ✅ Visible/Writable |
| **Reassign Grievances** | ❌ | ❌ | ✅ Within Department | ✅ Global |
| **Lodge Appeal** | ✅ Up to `max_reopen_count` | ❌ | ❌ | ❌ |
| **Review & Process Appeal** | ❌ | ❌ | ✅ Level 1 Review | ✅ Level 2 Review |
| **Academic Hierarchy CRUD** | ❌ | ❌ | ❌ | ✅ Full CRUD |
| **Manage Department Users** | ❌ | ❌ | ✅ Dept Students & Officers | ✅ Full CRUD |
| **System Settings & Support Hours**| ❌ | ❌ | ❌ | ✅ Full Configuration |
| **Audit Log Inspection** | ❌ | ❌ | ❌ | ✅ Full Audit Trail |
| **CSV Data Export** | ❌ | ✅ Scoped CSV | ✅ Scoped CSV | ✅ Full University CSV |

---

## 5. Grievance Lifecycle & Auto-Assignment Engine

```mermaid
flowchart TD
    Start([Student Opens Grievance Form]) --> CheckHours{Within Active Support Hours?}
    CheckHours -- No --> ShowHoursError[Reject: Submissions Closed Outside Operating Hours]
    CheckHours -- Yes --> FillForm[Enter Grievance Details & Attachments]
    
    FillForm --> ReqOTP[Request Submission OTP via Email]
    ReqOTP --> EnterOTP[Enter 6-Digit OTP]
    EnterOTP --> VerifyOTP{Is OTP Valid & Unexpired?}
    VerifyOTP -- No --> OTPError[Display OTP Verification Error]
    VerifyOTP -- Yes --> SaveGrievance[Create Grievance Record<br/>Status: PENDING]

    SaveGrievance --> AutoAssign{Is Auto-Assignment Enabled?}
    AutoAssign -- No --> UnassignedPool[Retain in Unassigned Queue for Manual Triage]
    AutoAssign -- Yes --> Tier1{Tier 1: Category Assignment for Department?}

    Tier1 -- Matched --> AssignDeptRule[Assign to Designated Admin]
    Tier1 -- No Match --> Tier2{Tier 2: Keyword Matches in Assignment Rules?}

    Tier2 -- Matched --> AssignKeyword[Assign to Keyword-Matched Admin]
    Tier2 -- No Match --> Tier3{Tier 3: Active Officer in Department?}

    Tier3 -- Found --> AssignOfficer[Load-Balanced Officer in Department]
    Tier3 -- Not Found --> Tier4{Tier 4: Active Department HOD / Admin?}

    Tier4 -- Found --> AssignHOD[Assign to Department HOD]
    Tier4 -- Not Found --> Tier5[Tier 5: Central Cell Superadmin Fallback]

    AssignDeptRule --> Notify[Notify Assignee via In-App & Email]
    AssignKeyword --> Notify
    AssignOfficer --> Notify
    AssignHOD --> Notify
    AssignDefault --> Notify

    Notify --> Investigation[Staff Begins Inquiry]
    Investigation --> NeedInfo{Need Student Information?}

    NeedInfo -- Yes --> StatusPendingStudent[Status: PENDING_STUDENT<br/>SLA Clock Paused]
    StatusPendingStudent --> StudentReply[Student Replies via Chat]
    StudentReply --> UnpauseSLA[Compute Accumulated Pause Minutes<br/>Status returns to PENDING]
    UnpauseSLA --> Investigation

    NeedInfo -- No --> Decision{Staff Resolution Decision}
    Decision -- Resolve --> EnterClosure[Enter Mandatory Resolution Remark<br/>Status: RESOLVED<br/>actual_resolution_date Recorded]
    Decision -- Reject --> EnterRejection[Enter Mandatory Rejection Reason<br/>Status: REJECTED<br/>actual_resolution_date Recorded]

    EnterClosure --> StudentSatisfied{Student Satisfied?}
    EnterRejection --> StudentSatisfied

    StudentSatisfied -- Yes --> Completed([Grievance Closed])
    StudentSatisfied -- No --> AppealCheck{Appeals < max_reopen_count?}

    AppealCheck -- No --> MaxReached[Appeal Limit Reached: Case Stays Closed]
    AppealCheck -- Yes --> FileAppeal[Student Files Appeal with New Grounds/Evidence]

    FileAppeal --> EscalateSupervisory[Auto-Escalate to Supervisory Authority<br/>is_appealed: True, Status: PENDING]
    EscalateSupervisory --> SupervisorReview{Supervisory Decision}

    SupervisorReview -- Accept & Reopen --> ReopenCase[Status: IN_PROGRESS<br/>actual_resolution_date Cleared<br/>Reopened for Inquiry]
    ReopenCase --> Investigation

    SupervisorReview -- Reject & Uphold --> UpholdCase[Status: RESOLVED<br/>Prior Decision Stands]
    UpholdCase --> Completed
```

---

## 6. Real-Time Communication & SLA Management Engine

### Real-Time Chat Engine (Daphne / Django Channels)
1. **Zero-Latency Streaming:** When a student or officer submits a message or file attachment, the event is persisted to the database and broadcasted via the Django Channels layer (`f'chat_{grievance.id}'`).
2. **Dynamic Live Badges:** State transitions triggered by staff automatically broadcast updated status badges, updating student browsers without page refreshes.
3. **Internal Note Security:** Comments flagged as `is_internal=True` are restricted to staff and stripped from student payloads.

### SLA Calculation & Background Processing
1. **Priority-Weighted SLA Calculation:**
   $$\text{Effective SLA Hours} = \max\left(\text{Category Base SLA} \times \text{Multiplier}, 6\right)$$
   where $\text{Urgent}=0.25$, $\text{High}=0.50$, $\text{Medium}=1.00$, and $\text{Low}=1.50$.
2. **Business Hours Weekend Shift:** When breach deadlines fall on a weekend (Saturday/Sunday), the breach deadline is automatically shifted forward to Monday morning.
3. **Background Cron (`process_slas`):** Executed regularly by Celery Beat to auto-resolve stale cases (`auto_resolve_days`) and escalate breached Level 0 / Level 1 grievances.

---

## 7. Modular Codebase Structure

```
Student_Grievance_Management_System/
├── ARCHITECTURE.md                  # Comprehensive architectural blueprint
├── README.md                        # Project documentation and quickstart
├── pyproject.toml / uv.lock         # Dependency management
├── manage.py
├── src/
│   ├── config/                      # Django & Daphne core configuration
│   │   ├── asgi.py                  # Daphne ASGI router (HTTP + Channels WebSocket)
│   │   ├── wsgi.py                  # WSGI fallback application
│   │   ├── settings.py              # Dynamic configuration & test cache isolation
│   │   ├── urls.py                  # Top-level routing
│   │   └── celery.py                # Celery async worker & Beat setup
│   ├── apps/
│   │   ├── authentication/          # User auth, 2FA, OTP verification, security utils
│   │   │   ├── models.py            # User, TemporaryRegistration, AdminLoginOTP
│   │   │   ├── security_utils.py    # Failed login tracking, HMAC OTP verification
│   │   │   ├── middleware.py        # SessionTimeoutMiddleware
│   │   │   ├── views.py             # Login, registration, OTP verify
│   │   │   └── tests/               # Authentication test suite
│   │   ├── students/                # Academic hierarchy & student experience
│   │   │   ├── models.py            # School, Department (auto-HOD), StudentProfile, AdminProfile
│   │   │   ├── views.py             # Student dashboard, profile, grievances, appeals
│   │   │   └── tests/               # Students test suite
│   │   ├── grievances/              # Core grievance domain, routing & SLA
│   │   │   ├── models.py            # Grievance, Category, Assignment, Comments, Appeal
│   │   │   ├── tasks.py             # Celery SLA escalation worker
│   │   │   ├── consumers.py         # WebSocket live chat consumer
│   │   │   ├── api_views.py         # DRF GrievanceViewSet & CategoryViewSet
│   │   │   ├── views.py             # Submit grievance, OTP verify, track view
│   │   │   ├── management/commands/
│   │   │   │   └── process_slas.py  # SLA check & auto-resolution cron command
│   │   │   └── tests/               # Grievance domain test suite
│   │   ├── admin_panel/             # Domain-segregated administrative views
│   │   │   ├── models.py            # SystemSettings singleton
│   │   │   ├── support_hours.py     # Operating hours parser & validator
│   │   │   ├── superadmin_views.py  # Superadmin settings, all-users CRUD, audit logs
│   │   │   ├── views/               # Decomposed controller suite
│   │   │   │   ├── dashboard_views.py
│   │   │   │   ├── grievance_views.py
│   │   │   │   ├── user_views.py
│   │   │   │   ├── export_views.py
│   │   │   │   └── crud_views...
│   │   │   └── tests/               # Admin panel test suite
│   │   └── notifications/           # In-app and async email notifications
│   │       ├── models.py            # Notification, ReadNotification
│   │       ├── tasks.py             # Celery email workers
│   │       └── tests/               # Notifications test suite
│   ├── static/                      # CSS, JavaScript & theme assets
│   └── templates/                   # Clean HTML templates
```
