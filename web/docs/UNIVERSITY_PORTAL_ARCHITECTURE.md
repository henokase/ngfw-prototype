# 🏗️ University Portal - Technical Architecture

## System Architecture Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Riverside University Portal              │
├─────────────────────────────────────────────────────────────┤
│  Frontend Layer (Templates + Static Assets)                │
│  ├── Public Website (Marketing/Information)                │
│  ├── Student Portal (Authenticated SIS)                    │
│  ├── Faculty Portal (Course Management)                    │
│  └── Admin Portal (Administrative Functions)               │
├─────────────────────────────────────────────────────────────┤
│  Application Layer (Flask Routes + Business Logic)         │
│  ├── Authentication & Authorization                        │
│  ├── Student Information System (SIS)                      │
│  ├── Course Management System (CMS)                        │
│  ├── Document Management System                            │
│  └── Administrative Services                               │
├─────────────────────────────────────────────────────────────┤
│  Security Layer (Middleware + Services)                    │
│  ├── Authentication Manager                                │
│  ├── Authorization Engine                                  │
│  ├── File Upload Security (ClamAV)                        │
│  ├── Request Logging & Monitoring                         │
│  └── Rate Limiting & DDoS Protection                      │
├─────────────────────────────────────────────────────────────┤
│  Data Layer (Database + File Storage)                      │
│  ├── University Database (SQLite/PostgreSQL)              │
│  ├── Document Storage (File System)                        │
│  └── Session Storage (Memory/Database)                     │
└─────────────────────────────────────────────────────────────┘
```

## Application Structure

### Enhanced Flask Application Organization
```
web/
├── app.py                          # Application factory and main entry point
├── config.py                       # Environment-based configuration
├── models.py                       # SQLAlchemy database models
├── wsgi.py                         # Production WSGI entry point
├── requirements.txt                # Python dependencies
│
├── src/
│   ├── __init__.py
│   ├── university/                 # University-specific modules
│   │   ├── __init__.py
│   │   ├── academic.py            # Academic calendar, courses, grades
│   │   ├── admissions.py          # Application processing, requirements
│   │   ├── campus_services.py     # Dining, housing, parking, events
│   │   ├── financial.py           # Tuition, payments, financial aid
│   │   └── library.py             # Library services, resources
│   │
│   ├── routes/                     # Route handlers organized by function
│   │   ├── __init__.py
│   │   ├── public_routes.py        # Homepage, about, academics (guest access)
│   │   ├── auth_routes.py          # Login, logout, registration [SQL Injection]
│   │   ├── student_routes.py       # Student portal, dashboard, profile
│   │   ├── academic_routes.py      # Courses, grades, enrollment
│   │   ├── document_routes.py      # File uploads, downloads [File Upload, Path Traversal]
│   │   ├── admin_routes.py         # Administrative functions
│   │   ├── api_routes.py           # Internal APIs [XXE, Command Injection]
│   │   ├── feedback_routes.py      # Course evaluations, suggestions [XSS]
│   │   └── redirect_routes.py      # External links, resources [Open Redirect]
│   │
│   ├── middleware/                 # Request/Response processing
│   │   ├── __init__.py
│   │   ├── auth_middleware.py      # Session management, user context
│   │   ├── rate_limit.py           # Enhanced rate limiting for university workflows
│   │   ├── request_logger.py       # Comprehensive request logging
│   │   └── security_headers.py     # Security headers with university customizations
│   │
│   ├── services/                   # Business logic and external integrations
│   │   ├── __init__.py
│   │   ├── auth_service.py         # Authentication and authorization
│   │   ├── academic_service.py     # Grade calculations, GPA, transcripts
│   │   ├── notification_service.py # Email notifications, announcements
│   │   ├── file_service.py         # Document management, antivirus scanning
│   │   ├── report_service.py       # Academic reports, analytics
│   │   └── integration_service.py  # External system integrations (VM1 communication)
│   │
│   └── templates/                  # Jinja2 templates organized by section
│       ├── base/                   # Base templates and layouts
│       │   ├── base.html          # Main layout template
│       │   ├── nav.html           # Navigation components
│       │   ├── footer.html        # Footer content
│       │   └── errors/            # Error pages (404, 500, etc.)
│       │
│       ├── public/                # Public website templates
│       │   ├── index.html         # University homepage
│       │   ├── about.html         # About the university
│       │   ├── academics.html     # Academic programs
│       │   ├── admissions.html    # Admissions information
│       │   └── campus_life.html   # Campus services and activities
│       │
│       ├── auth/                  # Authentication templates
│       │   ├── login.html         # Student/Staff login form
│       │   ├── register.html      # New user registration
│       │   └── forgot_password.html
│       │
│       ├── student/               # Student portal templates
│       │   ├── dashboard.html     # Student dashboard
│       │   ├── profile.html       # Student profile management
│       │   ├── courses.html       # Enrolled courses
│       │   ├── grades.html        # Grade viewer
│       │   ├── transcript.html    # Unofficial transcript
│       │   └── schedule.html      # Class schedule
│       │
│       ├── academic/              # Academic function templates
│       │   ├── course_catalog.html # Browse available courses
│       │   ├── enrollment.html    # Course enrollment form
│       │   ├── assignments.html   # Assignment submissions
│       │   └── evaluations.html   # Course evaluation forms
│       │
│       ├── documents/             # Document management templates
│       │   ├── upload.html        # File upload interface
│       │   ├── viewer.html        # Document viewer
│       │   └── library.html       # Library resources
│       │
│       └── admin/                 # Administrative templates
│           ├── dashboard.html     # Admin dashboard
│           ├── users.html         # User management
│           ├── courses.html       # Course management
│           └── reports.html       # Administrative reports
│
├── static/                        # Static assets
│   ├── css/
│   │   ├── university.css         # Main university styling
│   │   ├── dashboard.css          # Dashboard-specific styles
│   │   ├── forms.css             # Form styling
│   │   └── responsive.css        # Mobile responsiveness
│   │
│   ├── js/
│   │   ├── university.js          # Main JavaScript functionality
│   │   ├── dashboard.js          # Dashboard interactions
│   │   ├── forms.js              # Form validation and submission
│   │   └── charts.js             # Data visualization for grades/reports
│   │
│   ├── images/
│   │   ├── university/           # University branding assets
│   │   │   ├── logo.png          # University logo
│   │   │   ├── seal.png          # University seal
│   │   │   └── campus/           # Campus photos
│   │   │
│   │   ├── icons/                # UI icons and graphics
│   │   └── backgrounds/          # Background images
│   │
│   └── documents/                # Static document templates
│       ├── forms/                # Downloadable forms
│       ├── policies/             # University policies
│       └── guides/               # Student/faculty guides
│
├── data/                          # Application data and configuration
│   ├── seed_data/                # Database seeding data
│   │   ├── universities.json     # University information
│   │   ├── students.json         # Sample student records
│   │   ├── courses.json          # Course catalog data
│   │   ├── faculty.json          # Faculty information
│   │   └── academic_calendar.json # Semester/term data
│   │
│   ├── uploads/                  # User-uploaded files
│   │   ├── assignments/          # Student assignment submissions
│   │   ├── documents/            # Administrative documents
│   │   └── quarantine/           # Quarantined malware files
│   │
│   └── logs/                     # Application logs
│       ├── security.log          # Security events
│       ├── access.log            # Request access logs
│       └── error.log             # Error logs
│
└── tests/                        # Testing framework
    ├── unit/                     # Unit tests for components
    ├── integration/              # Integration tests
    ├── security/                 # Security testing
    │   ├── payloads/            # University-specific attack payloads
    │   └── scenarios/           # Realistic attack scenarios
    └── performance/              # Load and performance tests
```

## Database Architecture

### Enhanced Entity Relationship Model

#### Core University Entities
- **University**: Institution metadata
- **Users**: Students, Faculty, Staff, Admins
- **Academic**: Departments, Programs, Courses
- **Enrollment**: Student-Course relationships
- **Grades**: Academic performance records
- **Documents**: File management and metadata
- **Events**: Academic calendar and activities

#### Security and Logging Entities
- **Sessions**: User session management
- **AuditLogs**: Security and access logging
- **SecurityEvents**: Incident tracking
- **RateLimitEvents**: DDoS protection logs

## Route Architecture

### Public Routes (Guest Access)
```python
# University homepage and information
GET  /                          # University homepage
GET  /about                     # About the university
GET  /academics                 # Academic programs
GET  /admissions               # Admissions information
GET  /campus-life              # Campus services and activities
GET  /contact                  # Contact information
GET  /news                     # University news and announcements
```

### Authentication Routes [SQL Injection Vulnerability]
```python
# Student and staff authentication
GET  /login                    # Login form
POST /login                    # Process login [SQL Injection]
GET  /logout                   # Logout user
GET  /register                 # New user registration
POST /register                 # Process registration
GET  /forgot-password          # Password recovery
POST /forgot-password          # Process password recovery
```

### Student Portal Routes
```python
# Authenticated student access
GET  /student/dashboard        # Student dashboard
GET  /student/profile          # Profile management
POST /student/profile          # Update profile
GET  /student/courses          # Enrolled courses
GET  /student/grades           # Grade viewer
GET  /student/transcript       # Unofficial transcript
GET  /student/schedule         # Class schedule
```

### Academic Management Routes
```python
# Course and academic functions
GET  /courses                  # Course catalog
GET  /courses/<id>             # Course details
POST /enroll/<course_id>       # Course enrollment [Rate Limiting Vulnerability]
GET  /assignments             # Assignment list
POST /assignments/submit       # Assignment submission [File Upload Vulnerability]
GET  /evaluations             # Course evaluation forms
POST /evaluations             # Submit evaluations [XSS Vulnerability]
```

### Document Management Routes [Multiple Vulnerabilities]
```python
# File and document handling
GET  /documents               # Document browser [Path Traversal Vulnerability]
GET  /documents/<path>         # View document [Path Traversal Vulnerability]
POST /upload                   # File upload [File Upload Malware Vulnerability]
GET  /library                 # Library resources
GET  /library/external/<url>   # External resource redirect [Open Redirect Vulnerability]
```

### Administrative Routes
```python
# Staff and admin functions
GET  /admin/dashboard          # Administrative dashboard
GET  /admin/users              # User management
GET  /admin/courses            # Course management
POST /admin/import             # Data import [XXE Vulnerability]
GET  /admin/reports            # Administrative reports
GET  /admin/diagnostics        # System diagnostics [Command Injection Vulnerability]
```

### API Routes [Technical Vulnerabilities]
```python
# Internal and external APIs
POST /api/xml/grades           # Grade import via XML [XXE Vulnerability]
POST /api/network/ping         # Network diagnostics [Command Injection Vulnerability]
POST /api/search               # Internal search functionality
GET  /api/calendar             # Academic calendar data
POST /api/notifications        # Notification system
```

## Security Integration Points

### Vulnerability Embedding Strategy

#### 1. SQL Injection (Authentication)
- **Location**: `/login` route in `auth_routes.py`
- **Context**: Student/faculty authentication
- **Implementation**: Vulnerable SQL query in login validation
- **Disguise**: Standard university login portal

#### 2. File Upload Malware (Assignments)
- **Location**: `/assignments/submit` route in `academic_routes.py`
- **Context**: Student assignment submission
- **Implementation**: File upload without proper validation
- **Disguise**: Academic document submission system

#### 3. Command Injection (IT Services)
- **Location**: `/admin/diagnostics` route in `admin_routes.py`
- **Context**: Network diagnostics for IT staff
- **Implementation**: Ping utility with command injection
- **Disguise**: Administrative network tools

#### 4. Path Traversal (Document Viewer)
- **Location**: `/documents/<path>` route in `document_routes.py`
- **Context**: Academic resource browser
- **Implementation**: Unvalidated file path access
- **Disguise**: Library and academic document system

#### 5. Cross-Site Scripting (Course Evaluations)
- **Location**: `/evaluations` route in `feedback_routes.py`
- **Context**: Student course feedback system
- **Implementation**: Unescaped user input display
- **Disguise**: Standard course evaluation forms

#### 6. XML External Entity (Data Import)
- **Location**: `/admin/import` route in `admin_routes.py`
- **Context**: Administrative data import
- **Implementation**: XML parsing without entity protection
- **Disguise**: Academic record import system

#### 7. Open Redirect (External Resources)
- **Location**: `/library/external/<url>` route in `document_routes.py`
- **Context**: Library external database links
- **Implementation**: Unvalidated URL redirection
- **Disguise**: Academic resource linking

#### 8. Rate Limiting (Course Registration)
- **Location**: `/enroll/<course_id>` route in `academic_routes.py`
- **Context**: High-traffic course enrollment
- **Implementation**: Insufficient rate limiting
- **Disguise**: Course registration system

#### 9. Session Management (Portal Authentication)
- **Location**: Authentication middleware in `auth_middleware.py`
- **Context**: Student portal session handling
- **Implementation**: Weak session management
- **Disguise**: Standard university portal sessions

## Performance Considerations

### Database Optimization
- **Indexing Strategy**: Optimize queries for student lookups, course searches
- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Minimize N+1 queries in academic data

### Caching Strategy
- **Static Content**: CSS, JS, images cached with long TTL
- **Dynamic Content**: Course catalogs, announcements cached for 1 hour
- **Session Data**: Memory-based session storage for performance

### Scalability Planning
- **Concurrent Users**: Support 100+ simultaneous users
- **File Storage**: Efficient handling of document uploads
- **Database Growth**: Plan for academic year data accumulation

## Configuration Management

### Environment-Based Configuration
```python
# Development configuration
class DevelopmentConfig:
    DEBUG = True
    DATABASE_URI = 'sqlite:///university_dev.db'
    UPLOAD_PATH = './data/uploads/dev'
    CLAMAV_HOST = '10.0.0.1'  # VM1 for malware scanning

# Production configuration
class ProductionConfig:
    DEBUG = False
    DATABASE_URI = 'sqlite:///university_prod.db'
    UPLOAD_PATH = '/var/university/uploads'
    CLAMAV_HOST = '10.0.0.1'  # VM1 for malware scanning

# Testing configuration
class TestingConfig:
    TESTING = True
    DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
```

### University-Specific Configuration
```python
# University identity and branding
UNIVERSITY_NAME = "Riverside University"
UNIVERSITY_MOTTO = "Innovation Through Education"
UNIVERSITY_ESTABLISHED = 2010
UNIVERSITY_COLORS = {
    'primary': '#1B365D',    # Navy Blue
    'secondary': '#F4A261',  # Gold
    'accent': '#2A9D8F'      # Teal
}

# Academic configuration
CURRENT_SEMESTER = "Fall 2024"
REGISTRATION_OPEN = True
GRADING_SCALE = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
```

## Integration Points

### VM1 Communication (NGFW Testing)
- **Malware Detection**: ClamAV integration for file scanning
- **Security Events**: Real-time threat reporting to VM1
- **IP Blocking**: Adaptive blocking based on attack detection
- **Log Correlation**: Security event correlation between VMs

### External Service Simulation
- **Email System**: Simulated email notifications
- **Payment Gateway**: Mock financial transaction processing
- **Library Systems**: Simulated external database access
- **Emergency Notifications**: Campus-wide alert system simulation

This architecture provides a solid foundation for creating a realistic university portal while maintaining sophisticated security testing capabilities.