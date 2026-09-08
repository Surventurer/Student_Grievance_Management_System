# Student Grievance Management System - Architecture & System Audit

**Document Version:** 1.0.0  
**Generated Date:** September 2026  
**Repository:** `Student_Grievance_Management_System`  
**Framework:** Django (Python 3.12+) / PostgreSQL / Celery / Redis / Bootstrap 5 / Tailwind  

---

## 1. Executive Summary

The **Student Grievance Management System (SGMS)** is an enterprise-grade academic compliance and grievance resolution platform designed for universities and higher education institutions. The platform enables students to register grievances across academic, hostel, administrative, and disciplinary domains, while offering role-segregated resolution workflows for Department Heads (HODs), Grievance Officers, Chief Wardens, Wardens, and Superadministrators.

### Core Architectural Capabilities
- **Multi-Tenant Academic Hierarchy:** School → Department → Program structure supporting scoped data access.
- **Rule-Based & AI-Assisted Auto Assignment:** Deterministic routing of grievances based on category rules, department scoping, and role hierarchy.
- **Interactive Resolution & Real-Time Chat:** Student-to-Officer bidirectional communication with file attachments and audit-trailed state transitions.
- **Asynchronous Processing Pipeline:** Celery task workers with Redis broker for email OTP dispatch, SLA escalation monitors, and notification broadcasting.
- **Strict Role-Based Access Control (RBAC):** Tiered permissions enforced at both middleware/decorator and view/queryset levels.

---

## 2. High-Level System Architecture (C4 Component Diagram)

```mermaid
C4Context
    title Student Grievance Management System - System Context Diagram

    Person(student, "Student", "Files grievances, tracks SLA status, and chats with officers.")
    Person(officer, "Grievance Officer / HOD / Warden", "Investigates, updates status, and resolves complaints.")
    Person(admin, "Superadmin / Admin", "Manages system settings, academic hierarchy, roles, and audits.")

    Enterprise_Boundary(sgms_boundary, "Student Grievance Management System") {
        System(web_app, "Django Web Application", "Monolithic MVC/MVT with Gunicorn / WSGI, handling auth, business logic, and API endpoints.")
        SystemDb(postgres_db, "PostgreSQL Database", "Stores persistent entities: Users, Profiles, Grievances, Audit Logs, Settings.")
        SystemQueue(redis_queue, "Redis In-Memory Broker & Cache", "Session storage, cache layer, and Celery task broker.")
        System(celery_workers, "Celery Worker Service", "Executes background tasks: Email dispatch, SLA escalations, CSV exports.")
        System(celery_beat, "Celery Beat Scheduler", "Periodic tasks (SLA auto-escalations, overdue alerts).")
    }

    System_Ext(smtp_server, "SMTP / Email Service", "Google SMTP / SendGrid for OTP verification and grievance updates.")
    System_Ext(storage_service, "Media File Storage", "Local file storage / Cloud S3 for attachments and identity documents.")

    Rel(student, web_app, "Interacts via HTTPS / Web UI", "Browser / Mobile")
    Rel(officer, web_app, "Resolves complaints, communicates", "HTTPS / Admin & Officer UI")
    Rel(admin, web_app, "Configures policies, audits", "HTTPS / Superadmin UI")

    Rel(web_app, postgres_db, "Reads / Writes Entities (ORM)", "SQL / Port 5432")
    Rel(web_app, redis_queue, "Dispatches async jobs & caches data", "RESP / Port 6379")
    Rel(celery_workers, redis_queue, "Consumes jobs", "RESP")
    Rel(celery_workers, postgres_db, "Updates grievance SLA / escalations", "SQL")
    Rel(celery_workers, smtp_server, "Sends emails (OTP, status notifications)", "SMTP / Port 587")
    Rel(celery_beat, redis_queue, "Schedules recurring SLA checks", "RESP")
    Rel(web_app, storage_service, "Stores grievance attachments", "File I/O")
```

---

## 3. Entity-Relationship Model (ERD)

The database schema is divided into 5 core domains: **Authentication**, **Academic Hierarchy**, **Grievances & Escalations**, **Notifications**, and **Administration**.

```mermaid
erDiagram
    USER ||--o| STUDENT_PROFILE : "has profile"
    USER ||--o| ADMIN_PROFILE : "has administrative profile"
    USER ||--o{ GRIEVANCE : "submits (as student)"
    USER ||--o{ GRIEVANCE : "assigned to (as officer/HOD)"
    USER ||--o{ NOTIFICATION : "receives"
    USER ||--o{ AUDIT_LOG : "triggers actions"
    USER ||--o{ ADMIN_LOGIN_OTP : "authenticates via OTP"
    USER ||--o{ GRIEVANCE_COMMENT : "posts messages"

    SCHOOL ||--o{ DEPARTMENT : "contains"
    DEPARTMENT ||--o{ STUDENT_PROFILE : "enrolls"
    DEPARTMENT ||--o{ ADMIN_PROFILE : "manages/assigned"
    DEPARTMENT ||--o{ CATEGORY_ASSIGNMENT : "scoped to"

    CATEGORY ||--o{ GRIEVANCE : "categorizes"
    CATEGORY ||--o{ CATEGORY_ASSIGNMENT : "routing rules"
    
    GRIEVANCE ||--o{ GRIEVANCE_ATTACHMENT : "contains files"
    GRIEVANCE ||--o{ GRIEVANCE_COMMENT : "discussion thread"
    GRIEVANCE ||--o{ GRIEVANCE_STATUS_HISTORY : "tracks timeline"
    GRIEVANCE ||--o{ GRIEVANCE_ASSIGNMENT_HISTORY : "reassignment log"
    GRIEVANCE ||--o{ ESCALATION_LOG : "records SLA breaches"
    GRIEVANCE ||--o{ APPEAL : "has appeals"

    USER {
        int id PK
        string email UK
        string username
        string role "student, admin, superadmin, officer"
        boolean is_active
        boolean is_staff
        datetime date_joined
    }

    STUDENT_PROFILE {
        int id PK
        int user_id FK
        string roll_number UK
        string phone_number
        int department_id FK
        string semester
        string academic_year
        boolean is_verified
    }

    ADMIN_PROFILE {
        int id PK
        int user_id FK
        string staff_id UK
        string designation "HOD, Dean, Warden, Chief Warden, Officer"
        int department_id FK
        string phone_number
        boolean is_available_for_assignment
    }

    SCHOOL {
        int id PK
        string name UK
        string code UK
        string description
        boolean is_active
    }

    DEPARTMENT {
        int id PK
        int school_id FK
        string name UK
        string code UK
        int hod_user_id FK
        boolean is_active
    }

    CATEGORY {
        int id PK
        string name UK
        string slug UK
        string description
        int default_sla_days
        string priority "LOW, MEDIUM, HIGH, URGENT"
        boolean is_active
    }

    CATEGORY_ASSIGNMENT {
        int id PK
        int category_id FK
        int department_id FK
        int assigned_user_id FK
        int escalation_user_id FK
        int sla_days
        boolean is_active
    }

    GRIEVANCE {
        int id PK
        string tracking_id UK
        int student_id FK
        int category_id FK
        int department_id FK
        string title
        text description
        string priority "LOW, MEDIUM, HIGH, URGENT"
        string status "SUBMITTED, UNDER_REVIEW, IN_PROGRESS, RESOLVED, REJECTED, ESCALATED, CLOSED"
        int assigned_to_id FK
        datetime deadline
        boolean is_escalated
        datetime created_at
        datetime updated_at
        datetime resolved_at
    }

    GRIEVANCE_COMMENT {
        int id PK
        int grievance_id FK
        int sender_id FK
        text message
        boolean is_internal_note
        datetime created_at
    }

    AUDIT_LOG {
        int id PK
        int actor_id FK
        string action_type
        string target_model
        string target_object_id
        text details
        string ip_address
        datetime created_at
    }
```

---

## 4. Role-Based Access Control (RBAC) & Permission Matrix

The application strictly segregates privileges based on user role and administrative designation.

| Feature / Resource | Student | Grievance Officer | HOD | Chief Warden / Warden | Admin / Superadmin |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Submit Grievance** | ✅ Full | ❌ | ❌ | ❌ | ❌ |
| **View Own Grievances** | ✅ Full | ❌ | ❌ | ❌ | ❌ |
| **View Assigned Grievances** | ❌ | ✅ Scoped | ✅ Dept Scoped | ✅ Hostel Scoped | ✅ Global |
| **Update Grievance Status** | ❌ | ✅ Assigned | ✅ Dept Level | ✅ Hostel Level | ✅ Global |
| **Internal Resolution Notes**| ❌ | ✅ | ✅ | ✅ | ✅ |
| **Reassign Grievance** | ❌ | ❌ | ✅ Dept Level | ✅ Hostel Level | ✅ Global |
| **Escalate Grievance** | ✅ (Appeal) | ✅ | ✅ | ✅ | ✅ |
| **Academic Hierarchy CRUD** | ❌ | ❌ | ❌ | ❌ | ✅ Global |
| **Category & SLA Routing Rules** | ❌ | ❌ | ❌ | ❌ | ✅ Global |
| **Manage Department Users** | ❌ | ❌ | ❌ | ❌ | ✅ Global |
| **System Settings & SMTP Config** | ❌ | ❌ | ❌ | ❌ | ✅ Superadmin |
| **Audit Log Inspection** | ❌ | ❌ | ❌ | ❌ | ✅ Superadmin |
| **Analytics & Data Export** | ❌ | Scoped CSV | Scoped CSV | Scoped CSV | ✅ Full System |

---

## 5. Grievance Lifecycle & Auto-Assignment Engine

```mermaid
flowchart TD
    Start([Student Submits Grievance]) --> Validate[Validate Input & Upload Attachments]
    Validate --> GenTrack[Generate Unique Tracking ID]
    
    GenTrack --> RuleCheck{Is Auto-Assignment Enabled?}
    
    RuleCheck -- Yes --> MatchRule[Lookup CategoryAssignment for Category + Dept]
    RuleCheck -- No --> AssignDefault[Queue in Unassigned Pool for Admin Triage]
    
    MatchRule --> HasAssignee{Specific Assignee Defined?}
    HasAssignee -- Yes --> AssignOfficer[Assign to Designated Officer/HOD]
    HasAssignee -- No --> RoleLookup{Category Default Role}
    
    RoleLookup -- HOD --> AssignDeptHOD[Assign to Department HOD]
    RoleLookup -- Warden --> AssignWarden[Assign to Active Hostel Warden]
    RoleLookup -- General --> AssignOfficerPool[Assign to Default Officer]

    AssignDefault --> StatusSubmitted[Status: SUBMITTED]
    AssignOfficer --> StatusSubmitted
    AssignDeptHOD --> StatusSubmitted
    AssignWarden --> StatusSubmitted
    AssignOfficerPool --> StatusSubmitted

    StatusSubmitted --> NotifyOfficer[Dispatch Email & In-App Notification]
    NotifyOfficer --> UnderReview[Officer Opens: UNDER_REVIEW]

    UnderReview --> ActionDecision{Resolution Action}
    
    ActionDecision -- Request Info --> ChatThread[Chat with Student / Add Comment]
    ChatThread --> ActionDecision
    
    ActionDecision -- Work on Solution --> InProgress[Status: IN_PROGRESS]
    InProgress --> Resolved[Status: RESOLVED + Enter Resolution Summary]
    
    ActionDecision -- Invalid / Duplicate --> Rejected[Status: REJECTED + Rejection Reason]

    InProgress --> SLACheck{SLA Deadline Exceeded?}
    SLACheck -- Yes --> AutoEscalate[Celery Beat Triggers SLA Escalation]
    AutoEscalate --> EscalateStatus[Status: ESCALATED -> Assigned to Dean/Superadmin]
    EscalateStatus --> ActionDecision

    Resolved --> StudentAccept{Student Satisfied within 7 Days?}
    StudentAccept -- Yes / Timeout --> Closed([Status: CLOSED])
    StudentAccept -- No --> AppealFiled[Student Files Appeal]
    AppealFiled --> EscalateStatus
    Rejected --> Closed
```

---

## 6. Real-Time Chat & Grievance Discussion Engine

The system supports real-time / low-latency communication between students and handling officers within a specific grievance thread.

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student (Browser)
    participant Server as Django API / Views
    participant DB as PostgreSQL
    participant Celery as Celery Worker
    actor Officer as Assigned Officer

    Student->>Server: POST /students/grievance/<id>/add-comment/ (Message + File)
    Server->>DB: INSERT into GrievanceComment
    Server->>DB: INSERT into GrievanceAttachment (if files present)
    Server->>DB: INSERT into AuditLog
    Server->>Celery: Queue email_notification_task (Async)
    Server-->>Student: 200 OK (JSON Comment Payload)
    
    Celery->>Officer: Send Email Alert (New Message on Grievance #ID)

    Officer->>Server: GET /admin/grievances/<id>/comments/ (Polling / Fetch)
    Server->>DB: SELECT GrievanceComments WHERE grievance_id=<id>
    Server-->>Officer: JSON List of Comments
    
    Officer->>Server: POST /admin/grievances/<id>/add-admin-response/ (Response)
    Server->>DB: INSERT into GrievanceComment (is_internal_note=False)
    Server->>Celery: Queue email_notification_task to Student
    Server-->>Officer: 200 OK
    Celery->>Student: Send Email Alert (Officer responded)
```

---

## 7. Asynchronous Task Pipeline (Celery & Redis)

Background jobs prevent blocking synchronous web request-response cycles for high-latency operations.

```mermaid
flowchart LR
    subgraph Web App
        A[User Action / API Call] --> B[Django Views / Signals]
        B --> C[celery.send_task]
    end

    subgraph Broker & Scheduler
        C --> D[(Redis Message Broker)]
        E[Celery Beat Scheduler] -->|Periodic Crons| D
    end

    subgraph Celery Workers
        D --> F[Worker Node 1]
        D --> G[Worker Node 2]
    end

    subgraph Background Execution
        F --> H[send_otp_email_task]
        F --> I[send_grievance_status_email_task]
        G --> J[check_sla_breaches_task]
        G --> K[generate_bulk_report_csv_task]
    end

    subgraph External Systems
        H --> L[SMTP Mailer / Google Relay]
        I --> L
        J --> M[(PostgreSQL DB Escalation Update)]
        K --> N[File System / S3]
    end
```

---

## 8. Codebase Audit Findings & Risk Matrix

### 8.1 Critical Architecture Bottlenecks (Addressed in this Refactor)

1. **Monolithic Admin Views (`src/apps/admin_panel/views.py` - 4,156 lines):**
   - *Risk:* High cognitive complexity, high merge collision risk, hard to unit test.
   - *Refactored Solution:* Decomposed into a cohesive package `src/apps/admin_panel/views/` segmented by domain (`dashboard_views.py`, `grievance_views.py`, `category_views.py`, `school_views.py`, `department_views.py`, `user_views.py`, `export_views.py`, `audit_views.py`, `profile_views.py`).

2. **Dead & Orphaned Code Files:**
   - `src/apps/admin_panel/views_simple.py`: Redundant prototype view file left unreferenced.
   - `src/templates/admin_panel/audit_logs_clean.html`: Duplicate template superseded by `audit_logs.html`.
   - *Action:* Safely pruned.

3. **N+1 Database Query Patterns:**
   - *Issue:* Iterating over grievances in dashboard and list views previously performed standalone queries for `student.profile`, `student.profile.department`, and `category`.
   - *Solution:* Enforced `select_related('student', 'student__studentprofile', 'category', 'assigned_to', 'department')` across all view queries.

4. **Security & Input Validation Audit:**
   - **CSRF Protection:** Validated across all forms and AJAX endpoints (CSRF tokens embedded in headers).
   - **Role Escalation Defense:** Verified `@role_required` and `@superadmin_required` decorators prevent horizontal and vertical privilege escalation.
   - **File Upload Security:** Attachment validators restrict mime-types and file extensions (`.pdf`, `.jpg`, `.png`, `.docx`) and cap size at 10MB to prevent denial-of-service.

---

## 9. Modular File Structure (Post-Refactoring)

```
Student_Grievance_Management_System/
├── ARCHITECTURE.md                  # Comprehensive architectural blueprint
├── manage.py
├── requirements.txt
├── src/
│   ├── config/                      # Django project core configuration
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── apps/
│   │   ├── authentication/          # User model, Auth OTP, Registrations, RBAC
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── decorators.py
│   │   ├── students/                # Academic hierarchy & student profiles
│   │   │   ├── models.py            # School, Department, StudentProfile, AdminProfile
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   ├── grievances/              # Core grievance, category & workflow models
│   │   │   ├── models.py            # Grievance, Category, Assignment, AuditLog, Comments
│   │   │   ├── views.py
│   │   │   └── services.py          # Auto-assignment & routing business logic
│   │   ├── notifications/           # Real-time and async alert dispatch
│   │   │   ├── models.py
│   │   │   ├── tasks.py             # Celery email workers
│   │   │   └── views.py
│   │   └── admin_panel/             # Modularized administrative controller suite
│   │       ├── models.py            # SystemSettings
│   │       ├── urls.py
│   │       └── views/               # Domain-separated view modules
│   │           ├── __init__.py      # Backward-compatible API re-export
│   │           ├── dashboard_views.py
│   │           ├── grievance_views.py
│   │           ├── category_views.py
│   │           ├── school_views.py
│   │           ├── department_views.py
│   │           ├── user_views.py
│   │           ├── export_views.py
│   │           ├── audit_views.py
│   │           └── profile_views.py
│   ├── static/                      # CSS, JavaScript & theme assets
│   └── templates/                   # Clean HTML templates segregated by app
```

---

## 10. Refactoring & Maintenance Roadmap

1. **Phase 1 (Complete):** Monolithic view decomposition, dead code cleanup, architecture formalization.
2. **Phase 2 (Recommended Next Steps):**
   - **REST API / DRF Transition:** Expose standard REST endpoints (`/api/v1/grievances/`) using Django REST Framework for future mobile app integration.
   - **WebSocket Integration:** Replace AJAX comment polling with Django Channels for instant zero-latency chat updates.
   - **Elasticsearch Integration:** Add full-text search across historical grievances and knowledge base articles for high-volume deployments.

