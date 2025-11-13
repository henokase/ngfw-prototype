# 🚀 Adaptive NGFW Test Website - Implementation Plan

## Project Overview
Build a deliberately vulnerable Flask web application to test the Adaptive NGFW system's detection, inspection, and response capabilities.

---

## 🔍 Critical Architecture: File Upload & Scanning Workflow

### Complete Data Flow for File Uploads

```
1. User uploads file → HTTP POST /upload
   ↓
2. VM1 (Firewall) - Packet inspection
   • nftables allows HTTP traffic (DNAT rule)
   • Suricata DPI logs packets & metadata
   • Traffic forwarded to VM2 (10.0.0.5)
   ↓
3. VM2 (Web Server) - nginx → Flask
   • Flask receives file via request.files['file']
   • Extract client IP from X-Real-IP header
   ↓
4. Temporary Storage
   • Save file to /tmp/uploads/
   ↓
5. ClamAV Scanning (VM2)
   • antivirus_service.scan_file() called
   • PyClamd sends file to clamd daemon
   • ClamAV checks: hash, signatures, compressed files
   ↓
6. Decision Point - Scan Result
   
   ✅ IF CLEAN:
      • Move file: /tmp/uploads → /uploads/safe/
      • Create DB record (UploadedFile model)
      • Log: "Clean file uploaded"
      • Return: 200 OK with success message
   
   ❌ IF INFECTED:
      • Move file: /tmp/uploads → /uploads/quarantine/
      • Log: "Malware detected: [signature_name]"
      • Call VM1 API: POST http://10.0.0.1:5000/api/block_ip
      • Send: {"ip": uploader_ip}
      • Return: 400 Bad Request "File infected"
   ↓
7. VM1 Adaptive Response (if infected)
   • VM1 API receives block request
   • Execute: nft add element inet firewall blocked_ips {IP timeout 1h}
   • IP dynamically blocked for 1 hour
   • All future requests from that IP dropped
```

### Key Implementation Points

1. **Temp Storage Required**: `/tmp/uploads/` for pre-scan storage
2. **Dual Destinations**: `/uploads/safe/` (clean) vs `/uploads/quarantine/` (infected)
3. **Cross-VM Communication**: VM2 → VM1 API for adaptive blocking
4. **IP Extraction**: Use `request.headers.get('X-Real-IP')` from nginx
5. **Database Tracking**: Store scan results, signatures, uploader IPs
6. **Error Handling**: Gracefully handle ClamAV daemon failures
7. **ML Integration**: Log all scan results for ML training data

---

## 📋 Phase 1: Project Foundation & Setup

### Step 1.1: Environment Setup
- [ ] Create Python virtual environment on VM2
- [ ] Install core dependencies (Flask, SQLAlchemy, etc.)
- [ ] Set up `.gitignore` for Python projects
- [ ] Create `.env` file for configuration

**Commands:**
```bash
cd ~/ngfw-prototype/web
python3 -m venv venv
source venv/bin/activate
```

### Step 1.2: Create Base Project Structure
- [ ] Create `app.py` (application entry point)
- [ ] Create `config.py` (centralized configuration)
- [ ] Create `models.py` (database models)
- [ ] Create `requirements.txt` (dependencies list)
- [ ] Create `wsgi.py` (production entry point)

### Step 1.3: Create Directory Structure
- [ ] `instance/` - Runtime database storage
- [ ] `logs/` - Application logs (app.log, error.log, access.log)
- [ ] `uploads/safe/` - Clean uploaded files
- [ ] `uploads/quarantine/` - Infected files flagged by ClamAV
- [ ] `/tmp/uploads/` - Temporary storage for files during scanning
- [ ] `src/` - Main application code
- [ ] `src/routes/` - Route handlers
- [ ] `src/services/` - Business logic
- [ ] `src/middleware/` - Request interceptors
- [ ] `src/templates/` - HTML templates
- [ ] `static/css/` - Stylesheets
- [ ] `static/js/` - JavaScript files
- [ ] `static/images/` - Images and assets
- [ ] `nginx/` - Nginx configuration
- [ ] `tests/` - Test scripts and payloads
- [ ] `docs/` - Documentation

**Deliverable:** Complete folder structure with empty `__init__.py` files

---

## 📋 Phase 2: Core Application Setup

### Step 2.1: Configuration (`config.py`)
- [ ] Define Flask app configuration class
- [ ] Set database URI (SQLite)
- [ ] Configure upload folders
- [ ] Set secret key and security settings
- [ ] Define logging configuration
- [ ] Add environment-based configs (dev/prod)

### Step 2.2: Database Models (`models.py`)
- [ ] Create `User` model (id, username, password, email, created_at)
- [ ] Create `Feedback` model (id, user_id, message, created_at)
- [ ] Create `UploadedFile` model (id, filename, filepath, scan_status, scan_result, signature_name, uploader_ip, uploaded_at)
- [ ] Create `LogEvent` model (id, ip_address, endpoint, payload, timestamp)
- [ ] Add relationships between models

### Step 2.3: Application Entry Point (`app.py`)
- [ ] Initialize Flask app
- [ ] Load configuration from `config.py`
- [ ] Initialize SQLAlchemy database
- [ ] Register blueprints for routes
- [ ] Set up error handlers (404, 500)
- [ ] Configure logging
- [ ] Add middleware registration

**Deliverable:** Working Flask app skeleton that starts without errors

---

## 📋 Phase 3: Services Layer

### Step 3.1: Logging Service (`src/services/logging_service.py`)
- [ ] Configure rotating file handler
- [ ] Set up formatters (timestamp, IP, endpoint, payload)
- [ ] Create separate handlers for app.log and error.log
- [ ] Add helper functions for structured logging

### Step 3.2: Database Service (`src/services/database_service.py`)
- [ ] Create database initialization function
- [ ] Add helper functions for common queries
- [ ] Implement safe database connection handling
- [ ] Add transaction management utilities

### Step 3.3: Antivirus Service (`src/services/antivirus_service.py`)
- [ ] Initialize PyClamd connection to local `clamd` daemon
- [ ] Create file scanning function using `scan_file()` or `instream()`
- [ ] Implement temp file storage in `/tmp/uploads` before scanning
- [ ] Implement quarantine logic (move infected files to `/uploads/quarantine/`)
- [ ] Add scan result logging (clean/infected, signature name, source IP)
- [ ] Handle ClamAV connection errors gracefully (socket errors, daemon down)
- [ ] Create function to notify VM1 API when malware detected
- [ ] Log scan results for ML analysis (labeled data)

### Step 3.4: Utilities (`src/services/utils.py`)
- [ ] Safe path join function (for file operations)
- [ ] Input sanitization helpers (for demonstration)
- [ ] Response formatting utilities
- [ ] Common validation functions

**Deliverable:** Reusable service modules for core functionality

---

## 📋 Phase 4: Middleware Components

### Step 4.1: Request Logger (`src/middleware/request_logger.py`)
- [ ] Log all incoming requests (IP, method, path, headers)
- [ ] Capture request payload/parameters
- [ ] Log response status codes
- [ ] Store in LogEvent database table

### Step 4.2: Security Headers (`src/middleware/security_headers.py`)
- [ ] Add basic security headers (optional, for comparison)
- [ ] X-Content-Type-Options
- [ ] X-Frame-Options
- [ ] Content-Security-Policy (relaxed for XSS testing)

### Step 4.3: Rate Limiter (`src/middleware/rate_limit.py`)
- [ ] Simple in-memory rate limiting
- [ ] Track requests per IP
- [ ] Configurable thresholds
- [ ] Log rate limit violations

**Deliverable:** Middleware that intercepts and logs all traffic

---

## 📋 Phase 5: Vulnerable Route Modules

### Step 5.1: Authentication Routes (`src/routes/auth_routes.py`)
**Endpoint:** `/login`
- [ ] Create login form (GET)
- [ ] Implement vulnerable SQL query (POST)
- [ ] **Vulnerability:** SQL Injection (`' OR 1=1--`)
- [ ] Log all login attempts
- [ ] Return success/failure messages

**Test Payload:** `username: admin' OR '1'='1'--`

### Step 5.2: File Upload Routes (`src/routes/upload_routes.py`)
**Endpoint:** `/upload`
- [ ] Create file upload form (GET)
- [ ] Accept file uploads via `request.files['file']` (POST)
- [ ] **Vulnerability:** No file type validation
- [ ] Save file temporarily to `/tmp/uploads` before scanning
- [ ] Call `antivirus_service.scan_file()` on temp file
- [ ] **If CLEAN:** Move to `/uploads/safe/`, create DB record, return success
- [ ] **If INFECTED:** Move to `/uploads/quarantine/`, log detection, notify VM1 API at `http://10.0.0.1:5001/api/malware_alert`
- [ ] **CRITICAL:** Do NOT extract client IP - VM2 only sees VM1's IP (10.0.0.1)
- [ ] Send alert to VM1 with: filename, file_hash, signature, timestamp (NO IP)
- [ ] VM1 correlates with conntrack to find real client IP and blocks it
- [ ] Log VM1's response for audit (VM1 returns blocked_ip in response)
- [ ] Handle ClamAV errors gracefully (return 500 if scanner unavailable)

**Test Payloads:** 
- EICAR test file (standard malware test)
- Compressed archives with malware
- Webshell files (PHP, JSP)

### Step 5.3: Command Injection Routes (`src/routes/command_routes.py`)
**Endpoint:** `/cmd`
- [ ] Create "ping test" form (GET)
- [ ] Execute system command with user input (POST)
- [ ] **Vulnerability:** Command injection (`; cat /etc/passwd`)
- [ ] Return command output
- [ ] Log all command executions

**Test Payload:** `8.8.8.8; whoami`

### Step 5.4: Path Traversal Routes (`src/routes/file_routes.py`)
**Endpoint:** `/file`
- [ ] Create file viewer form (GET)
- [ ] Read and display file contents (POST)
- [ ] **Vulnerability:** Path traversal (`../../etc/passwd`)
- [ ] No path sanitization
- [ ] Log file access attempts

**Test Payload:** `filename: ../../etc/passwd`

### Step 5.5: XSS Routes (`src/routes/xss_routes.py`)
**Endpoint:** `/feedback`
- [ ] Create feedback form (GET)
- [ ] Store user feedback in database (POST)
- [ ] Display all feedback without escaping (GET)
- [ ] **Vulnerability:** Stored XSS
- [ ] **Vulnerability:** Reflected XSS in search
- [ ] Log feedback submissions

**Test Payload:** `<script>alert('XSS')</script>`

### Step 5.6: XML Routes (`src/routes/xml_routes.py`)
**Endpoint:** `/api/xml`
- [ ] Create XML upload form (GET)
- [ ] Parse XML with external entity processing (POST)
- [ ] **Vulnerability:** XXE attack
- [ ] Return parsed XML data
- [ ] Log XML processing

**Test Payload:** 
```xml
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<data>&xxe;</data>
```

### Step 5.7: Redirect Routes (`src/routes/redirect_routes.py`)
**Endpoint:** `/redirect`
- [ ] Accept URL parameter
- [ ] **Vulnerability:** Open redirect (no validation)
- [ ] Redirect to user-supplied URL
- [ ] Log redirect attempts

**Test Payload:** `/redirect?url=http://malicious.com`

### Step 5.8: Compute Routes (`src/routes/compute_routes.py`)
**Endpoint:** `/compute`
- [ ] Create computation form (GET)
- [ ] Perform CPU-intensive operation (POST)
- [ ] **Vulnerability:** Resource exhaustion
- [ ] No rate limiting on heavy operations
- [ ] Log computation requests

**Test Payload:** Large factorial calculation or hash iterations

### Step 5.9: Miscellaneous Routes (`src/routes/misc_routes.py`)
**Endpoints:** `/`, `/about`, `/help`
- [ ] Create homepage with links to all endpoints
- [ ] About page (project description)
- [ ] Help page (usage instructions)
- [ ] Success/error pages

**Deliverable:** 9 working vulnerable endpoints with logging

---

## 📋 Phase 6: Frontend Templates

### Step 6.1: Base Template (`src/templates/base.html`)
- [ ] Create HTML5 boilerplate
- [ ] Include Bootstrap CSS
- [ ] Add navigation menu
- [ ] Create footer with project info
- [ ] Add block sections for content

### Step 6.2: Individual Page Templates
- [ ] `index.html` - Homepage with endpoint cards
- [ ] `login.html` - Login form
- [ ] `upload.html` - File upload form
- [ ] `command.html` - Ping test form
- [ ] `file.html` - File viewer form
- [ ] `feedback.html` - Feedback form + display
- [ ] `xml_api.html` - XML upload form
- [ ] `redirect.html` - Redirect test form
- [ ] `compute.html` - Computation form
- [ ] `error.html` - Error display
- [ ] `success.html` - Success messages

### Step 6.3: Styling
- [ ] Create `static/css/style.css`
- [ ] Add custom Bootstrap overrides
- [ ] Style forms and buttons
- [ ] Add responsive design
- [ ] Include vulnerability warnings (red badges)

**Deliverable:** Professional-looking UI with clear navigation

---

## 📋 Phase 7: Static Assets

### Step 7.1: CSS Files
- [ ] Download Bootstrap 5.x CSS
- [ ] Create custom `style.css`
- [ ] Add syntax highlighting for code blocks

### Step 7.2: JavaScript Files
- [ ] Download jQuery (if needed)
- [ ] Create `main.js` for form validation
- [ ] Add AJAX handlers (optional)

### Step 7.3: Images
- [ ] Create or download logo
- [ ] Add placeholder images
- [ ] Include warning icons

**Deliverable:** Complete static asset library

---

## 📋 Phase 8: Nginx Configuration ✅ COMPLETE

### Step 8.1: Basic Nginx Reverse Proxy ✅
- [x] Configure server block (listen on port 80)
- [x] Set up reverse proxy to Flask (127.0.0.1:5000)
- [x] Add proxy headers (X-Real-IP, X-Forwarded-For)

**Status:** ✅ Complete - Basic Nginx reverse proxy configured on VM2
**Note:** Advanced features (rate limiting, compression, etc.) handled by NGFW/ML layers

**Deliverable:** ✅ Working nginx reverse proxy

---

## 📋 Phase 9: Testing & Payloads

### Step 9.1: Normal Traffic Tests (`tests/test_normal_requests.py`)
- [ ] Create legitimate user scenarios
- [ ] Normal login attempts
- [ ] Safe file uploads
- [ ] Regular browsing patterns
- [ ] Form submissions

### Step 9.2: Attack Payload Tests (`tests/test_attack_payloads.py`)
- [ ] SQL injection payloads
- [ ] XSS payloads
- [ ] Command injection payloads
- [ ] Path traversal payloads
- [ ] XXE payloads
- [ ] DDoS simulation scripts

### Step 9.3: Payload Files
- [ ] `tests/payloads/sql_injection.txt`
- [ ] `tests/payloads/xss.txt`
- [ ] `tests/payloads/lfi.txt`
- [ ] `tests/payloads/xxe.txt`
- [ ] `tests/payloads/redirect.txt`
- [ ] `tests/payloads/ddos_script.py`

**Deliverable:** Automated test suite for validation

---

## 📋 Phase 10: Documentation

### Step 10.1: Endpoint Documentation (`docs/endpoint_specs.md`)
- [ ] Document each endpoint
- [ ] List vulnerabilities
- [ ] Provide example payloads
- [ ] Show expected responses

### Step 10.2: Payload Reference (`docs/payload_reference.md`)
- [ ] Categorize attack types
- [ ] List common payloads
- [ ] Explain detection methods
- [ ] Reference Suricata rules

### Step 10.3: Logging Policy (`docs/logging_policy.md`)
- [ ] Define log formats
- [ ] Explain log rotation
- [ ] Document integration with NGFW
- [ ] Show sample log entries

### Step 10.4: Architecture Diagram
- [ ] Create network topology diagram
- [ ] Show data flow
- [ ] Illustrate NGFW integration

**Deliverable:** Complete documentation package

---

## 📋 Phase 11: VM1-VM2 Cross-Communication API

### Step 11.1: Create VM1 Blocking API Service
- [ ] Create simple Flask/FastAPI service on VM1
- [ ] Add `/api/block_ip` endpoint (POST)
- [ ] Accept JSON payload with IP address
- [ ] Execute nftables command to add IP to blocked_ips set
- [ ] Set timeout (e.g., 1 hour) for dynamic blocking
- [ ] Return JSON response with status
- [ ] Add authentication/API key for security
- [ ] Log all blocking requests

**Example Implementation:**
```python
@app.route('/api/block_ip', methods=['POST'])
def block_ip():
    ip = request.json['ip']
    os.system(f"sudo nft add element inet firewall blocked_ips {{ {ip} timeout 1h }}")
    return jsonify({"status": "blocked", "ip": ip})
```

### Step 11.2: Integrate VM1 API Calls in VM2
- [ ] Add VM1 API endpoint URL to config (http://10.0.0.1:5000)
- [ ] Update `antivirus_service.py` to call VM1 API on malware detection
- [ ] Send uploader IP address when infected file detected
- [ ] Handle API call failures gracefully (log but don't crash)
- [ ] Add retry logic for failed API calls
- [ ] Log all cross-VM communications

**Deliverable:** Adaptive response system - malware uploads trigger automatic IP blocking

---

## 📋 Phase 12: Integration & Deployment

### Step 12.1: Database Initialization
- [ ] Create database initialization script
- [ ] Seed initial data (test users)
- [ ] Verify table creation

### Step 12.2: Local Testing
- [ ] Run Flask development server
- [ ] Test all endpoints manually
- [ ] Verify logging works
- [ ] Check file uploads and scanning

### Step 12.3: Nginx Integration
- [ ] Install nginx on VM2
- [ ] Copy configuration files
- [ ] Test reverse proxy
- [ ] Verify logs are written

### Step 12.4: ClamAV Setup
- [ ] Install ClamAV on VM2 (`sudo apt install clamav clamav-daemon`)
- [ ] Update virus definitions (`sudo freshclam`)
- [ ] Start clamd service (`sudo systemctl start clamav-daemon`)
- [ ] Verify clamd is running (`sudo systemctl status clamav-daemon`)
- [ ] Test PyClamd connection from Flask
- [ ] Upload EICAR test file to verify scanning works
- [ ] Check quarantine folder for infected files
- [ ] Verify scan results are logged

### Step 12.5: Production Deployment
- [ ] Configure Gunicorn
- [ ] Set up systemd service
- [ ] Enable nginx
- [ ] Test from external network

**Deliverable:** Fully deployed test website on VM2

---

## 📋 Phase 13: NGFW Integration Testing

### Step 13.1: Network Routing
- [ ] Configure VM1 DNAT rules (80 → 10.0.0.5:80)
- [ ] Verify traffic flows through NGFW
- [ ] Test from external client

### Step 13.2: Suricata Integration
- [ ] Verify Suricata monitors traffic on VM1
- [ ] Test SQL injection detection
- [ ] Test XSS detection
- [ ] Check eve.json logs for alerts
- [ ] Verify file upload traffic is logged

### Step 13.3: ClamAV Integration & Adaptive Blocking
- [ ] Upload EICAR test file through website
- [ ] Verify ClamAV scanning detects malware
- [ ] Check file moved to `/uploads/quarantine/`
- [ ] Verify VM2 calls VM1 API to block uploader IP
- [ ] Check nftables blocked_ips set on VM1
- [ ] Attempt second upload from blocked IP (should fail)
- [ ] Verify logs show cross-VM communication

### Step 13.4: ML Model Integration
- [ ] Generate normal traffic
- [ ] Generate attack traffic
- [ ] Verify ML anomaly detection
- [ ] Test adaptive IP blocking

**Deliverable:** End-to-end NGFW validation

---

## 📋 Phase 14: Final Validation & Documentation

### Step 14.1: Comprehensive Testing
- [ ] Run all attack payloads
- [ ] Verify NGFW detections
- [ ] Check dashboard updates
- [ ] Validate IP blocking

### Step 14.2: Performance Testing
- [ ] Load testing with wrk/ab
- [ ] DDoS simulation
- [ ] Resource monitoring
- [ ] Log analysis

### Step 14.3: Final Documentation
- [ ] Create test report (`docs/test_report.md`)
- [ ] Document findings
- [ ] List detected vs. missed attacks
- [ ] Document cross-VM adaptive blocking workflow
- [ ] Include file scanning process diagram
- [ ] Provide recommendations

### Step 14.4: Code Cleanup
- [ ] Remove debug statements
- [ ] Add inline comments
- [ ] Format code consistently
- [ ] Update README

**Deliverable:** Production-ready test website with complete documentation

---

## 🎯 Success Criteria Checklist

- [ ] All 9 vulnerable endpoints functional
- [ ] Website accessible via NGFW external IP
- [ ] All requests logged properly
- [ ] ClamAV scanning works on VM2
- [ ] Infected files moved to quarantine folder
- [ ] VM2 successfully calls VM1 API on malware detection
- [ ] VM1 dynamically blocks uploader IPs via nftables
- [ ] Attack payloads trigger NGFW alerts
- [ ] Suricata detects malicious patterns
- [ ] ML model identifies anomalies
- [ ] Adaptive blocking functions correctly
- [ ] No routing or proxy errors
- [ ] Complete documentation delivered
- [ ] Cross-VM communication tested and validated

---

## 📦 Key Deliverables Summary

1. **Source Code**: Complete Flask application
2. **Configuration**: nginx, Gunicorn, systemd
3. **Database**: SQLite with models and seed data
4. **Logs**: Structured logging system
5. **Tests**: Attack payloads and automation scripts
6. **Documentation**: Endpoint specs, payloads, architecture
7. **Integration**: Working NGFW pipeline

---

## ⚠️ Important Notes

- This is an **intentionally vulnerable** application for research purposes
- **Never deploy to production** or public internet
- Use only in controlled lab environment (VM2 behind NGFW)
- All vulnerabilities are deliberate for testing
- Follow academic and ethical guidelines

---

## 🔄 Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1-2 | 2-3 hours | None |
| Phase 3-4 | 2-3 hours | Phase 1-2 |
| Phase 5 | 4-6 hours | Phase 3-4 |
| Phase 6-7 | 2-3 hours | Phase 5 |
| Phase 8 | 1-2 hours | Phase 6-7 |
| Phase 9-10 | 2-3 hours | Phase 5 |
| Phase 11 | 2-3 hours | Phase 3 (antivirus service) |
| Phase 12 | 2-3 hours | All previous |
| Phase 13 | 3-4 hours | Phase 12 |
| Phase 14 | 2-3 hours | Phase 13 |
| **Total** | **22-33 hours** | Sequential |

---

## 🚀 Getting Started

To begin implementation:

```bash
# Navigate to project
cd c:\Projects\NGFW-Prototype\ngfw-prototype\web

# Start with Phase 1, Step 1.1
# Follow each step sequentially
# Mark items as complete with [x]
```

**Next Action:** Begin Phase 1 - Project Foundation & Setup

---

## 📚 Related Documentation

- **`file-scanning-process.md`** - Detailed explanation of file upload, scanning, and cross-VM blocking workflow
- **`Requirements.ms`** - Complete project requirements and design report
- **`Project-structure.md`** - Professional file and folder structure specification

**Note:** Review `file-scanning-process.md` before implementing Phase 5.2 (File Upload Routes) and Phase 11 (VM1-VM2 API Integration)
