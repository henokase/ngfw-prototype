# Adaptive NGFW — Test Web Application (VM2)

> **WARNING**: This web application contains intentionally vulnerable code for security testing. Never deploy to production or expose to untrusted networks.

A deliberately vulnerable Flask web application that serves as the attack surface for the Adaptive NGFW prototype. It generates both malicious and legitimate HTTP traffic to evaluate the firewall's detection and response pipeline.

## Quick Start

```bash
# Activate virtual environment
source /home/ubuntuhero/ngfw/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the application
python3 app.py
```

Access at `http://10.0.0.5:5000` or `http://localhost:5000` for local testing.

## Project Structure

```
web/
├── app.py                          # Flask application entry point
├── models.py                       # SQLAlchemy models
├── config.py                       # Configuration management
├── .env                            # Environment variables
├── requirements.txt                # Python dependencies
├── nginx.conf                      # Nginx reverse proxy reference config
├── src/
│   ├── routes/
│   │   ├── auth_routes.py          # Login + registration (SQLi)
│   │   ├── upload_routes.py        # File upload with ClamAV scanning
│   │   ├── command_routes.py       # Ping tool (command injection)
│   │   ├── file_viewer_routes.py   # File viewer (path traversal)
│   │   ├── feedback_routes.py      # User feedback (XSS)
│   │   ├── xml_api_routes.py       # XML API (XXE)
│   │   └── redirect_routes.py      # URL redirect (open redirect)
│   ├── middleware/
│   │   ├── rate_limiter.py         # Session/account-based rate limiting
│   │   ├── request_logger.py       # Comprehensive request/response logging
│   │   └── security_headers.py     # CSP, X-Frame-Options, HSTS, etc.
│   ├── services/
│   │   ├── antivirus_service.py    # ClamAV integration with simulation fallback
│   │   ├── database_service.py     # DB initialization and seed data
│   │   └── log_service.py          # Logging helpers
│   ├── templates/                  # 19 HTML templates (Bootstrap 5.3)
│   └── static/css/
│       └── style.css               # Custom styles
├── docs/                           # Comprehensive documentation
│   ├── Requirements.md
│   ├── VM2_API_DOCS.md
│   ├── SETUP_DEPLOYMENT.md
│   ├── ARCHITECTURE_DECISIONS.md
│   └── IMPLEMENTATION_STATUS.md
├── tests/                          # Test payloads and scripts
├── logs/                           # Application and error logs
├── uploads/
│   ├── safe/                       # Clean uploaded files
│   └── quarantine/                 # Quarantined malicious files
└── instance/
    └── database.db                 # SQLite database
```

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Flask | 3.0.2 |
| Database | SQLite + SQLAlchemy | 2.0.27 |
| Templates | Jinja2 + Bootstrap 5.3.0 | - |
| AntiVirus | ClamAV + pyClamd | 0.4.6 |
| WSGI | Werkzeug | 3.0.1 |
| HTTP Client | requests | 2.31.0 |

## Endpoints

### Vulnerable Endpoints (Attack Simulation)

| Method | Path | Vulnerability | Description |
|--------|------|---------------|-------------|
| `GET/POST` | `/login` | SQL Injection | Authentication with unsanitized queries |
| `POST` | `/upload` | Unrestricted File Upload | Accepts any file type for ClamAV scanning |
| `POST` | `/command/execute` | Command Injection | "Ping test" passes input to `os.popen()` |
| `GET` | `/file/viewer` | Path Traversal | File viewer with insufficient path validation |
| `POST` | `/feedback` | Stored XSS | Comments rendered without sanitization |
| `POST` | `/api/xml` | XXE | Parses XML with external entity resolution |
| `GET` | `/redirect` | Open Redirect | Redirects to arbitrary URLs |

### Legitimate Endpoints (Normal Traffic)

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST` | `/register` | User registration |
| `GET/POST` | `/profile` | View/edit user profile |
| `GET` | `/stats` | Attack statistics dashboard |
| `GET` | `/uploads` | View upload history |
| `GET` | `/about` | About page |
| `GET` | `/help` | Help page |
| `GET` | `/` | Home page |

### Health & Info

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Application health check |

## Security Middleware

### Rate Limiter (`src/middleware/rate_limiter.py`)

Two-tier rate limiting using session/account identifiers (not IP, since VM2 only sees VM1's NAT IP `10.0.0.1`):

| Limit | Scope | Window | Action |
|-------|-------|--------|--------|
| 100 requests | Per session/account | 1 minute | Return HTTP 429 |
| 50 requests | Global | 1 second | Return HTTP 429 (flood protection) |

### Security Headers (`src/middleware/security_headers.py`)

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy: default-src 'self'`
- `Strict-Transport-Security: max-age=31536000`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`

### Request Logger (`src/middleware/request_logger.py`)

Logs every request with:
- Timestamp, method, path, query string
- Client IP (from `X-Forwarded-For` or `remote_addr`)
- Response status code
- User agent

## File Upload & Scanning

Uploads are processed through a quarantine-first workflow:

1. File uploaded to temp directory (`/tmp/uploads`)
2. ClamAV scans the file
3. If **infected**: moved to `uploads/quarantine/`, logged, and user notified
4. If **clean**: moved to `uploads/safe/`, logged, and user can view it

### ClamAV Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `CLAMAV_HOST` | `localhost` | ClamAV daemon host |
| `CLAMAV_PORT` | `3310` | ClamAV TCP port |
| Socket path | `/var/run/clamav/clamd.ctl` | Unix socket fallback |
| Simulation mode | Enabled (default) | Uses EICAR string matching when ClamAV unavailable |

## Database Models

### User

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `username` | String(80) | Unique, not null |
| `email` | String(120) | Unique, not null |
| `password_hash` | String(256) | Not null (hashed) |
| `created_at` | DateTime | Auto-generated |

### Feedback

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | Foreign key → User |
| `comment` | Text | Not null (unsanitized) |
| `created_at` | DateTime | Auto-generated |

### UploadedFile

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | Foreign key → User |
| `filename` | String(256) | Original filename |
| `stored_filename` | String(256) | UUID-based storage name |
| `file_path` | String(512) | Full path on disk |
| `file_size` | Integer | Bytes |
| `upload_date` | DateTime | Auto-generated |
| `scan_status` | String(20) | `clean`, `infected`, `scanning` |
| `quarantined` | Boolean | Default `False` |

### LogEvent

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | Foreign key → User (nullable) |
| `event_type` | String(50) | Event classification |
| `description` | Text | Event details |
| `ip_address` | String(45) | Client IP |
| `user_agent` | Text | Browser/agent string |
| `created_at` | DateTime | Auto-generated |

## Seed Users

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Administrator |
| `user` | `password` | Regular user |
| `test` | `test123` | Test account |
| `guest` | `guest` | Guest account |

## Configuration

### Environment Variables (`.env`)

```env
# Flask
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=<change-in-production>

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///instance/database.db
SQLALCHEMY_TRACK_MODIFICATIONS=False

# Uploads
UPLOAD_FOLDER=uploads/safe
QUARANTINE_FOLDER=uploads/quarantine
TEMP_UPLOAD_FOLDER=/tmp/uploads
MAX_CONTENT_LENGTH=16777216

# ClamAV
CLAMAV_HOST=localhost
CLAMAV_PORT=3310

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
ERROR_LOG_FILE=logs/error.log
```

## Testing

### With Attack Payloads

```bash
# Run test payloads
python3 tests/payloads/run_all_tests.py

# Run specific payload tests
python3 tests/payloads/run_payloads.py
```

Payload definitions are in `tests/payloads/payloads.json` with 19+ attack patterns across all vulnerable endpoints.

### Manual Testing

```bash
# SQL Injection
curl -X POST http://localhost:5000/login \
  -d "username=' OR 1=1--&password=anything"

# Command Injection
curl -X POST http://localhost:5000/command/execute \
  -d "ip=8.8.8.8; cat /etc/passwd"

# Path Traversal
curl "http://localhost:5000/file/viewer?filename=../../etc/passwd"

# XSS
curl -X POST http://localhost:5000/feedback \
  -d "comment=<script>alert('XSS')</script>"

# Open Redirect
curl "http://localhost:5000/redirect?url=http://evil.com"
```

## Nginx Reverse Proxy

Reference configuration in `nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Documentation

| Document | Description |
|----------|-------------|
| [Requirements](docs/Requirements.md) | PDR with design objectives, module specs, success criteria |
| [API Reference](docs/VM2_API_DOCS.md) | Complete endpoint documentation with attack examples |
| [Setup & Deployment](docs/SETUP_DEPLOYMENT.md) | VM provisioning, networking, service configuration |
| [Architecture](docs/ARCHITECTURE_DECISIONS.md) | Design rationale and detection flow |
| [Implementation Status](docs/IMPLEMENTATION_STATUS.md) | Feature tracking and roadmap |

## License

MIT
