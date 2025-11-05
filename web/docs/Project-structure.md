# 🧱 Adaptive NGFW Test Website

## Professional File & Folder Structure

```
web/
├── app.py
├── config.py
├── models.py
├── requirements.txt
├── wsgi.py
│
├── instance/
│   └── database.db                # SQLite database file (runtime-generated)
│
├── logs/
│   ├── app.log                    # General app log (requests, events)
│   ├── error.log                  # Error and exception logs
│   └── access.log                 # Optional access logs for comparison with nginx
│
├── uploads/
│   ├── safe/                      # Legitimate uploaded files
│   └── quarantine/                # Suspicious files flagged by ClamAV
│
├── src/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py         # /login endpoint (SQLi)
│   │   ├── upload_routes.py       # /upload endpoint (file handling)
│   │   ├── xss_routes.py          # /feedback (XSS)
│   │   ├── command_routes.py      # /cmd (command injection)
│   │   ├── file_routes.py         # /file (path traversal)
│   │   ├── xml_routes.py          # /api/xml (XXE)
│   │   ├── redirect_routes.py     # /redirect (open redirect)
│   │   ├── compute_routes.py      # /compute (resource exhaustion)
│   │   └── misc_routes.py         # index page, about, help, etc.
│   │
│   ├── services/
│   │   ├── antivirus_service.py   # ClamAV integration (PyClamd)
│   │   ├── logging_service.py     # Logging configuration (rotating file handler)
│   │   ├── database_service.py    # Helper for DB connections and queries
│   │   └── utils.py               # Common helper functions (safe join, etc.)
│   │
│   ├── middleware/
│   │   ├── request_logger.py      # Logs all HTTP requests and IPs
│   │   ├── security_headers.py    # Adds simple security headers (optional)
│   │   └── rate_limit.py          # Simulated rate-limit logi (optional)
│   │
│   └── templates/
│       ├── base.html              # Base layout
│       ├── index.html             # Home page (links to all endpoints)
│       ├── login.html
│       ├── upload.html
│       ├── feedback.html
│       ├── command.html
│       ├── file.html
│       ├── xml_api.html
│       ├── redirect.html
│       ├── compute.html
│       ├── error.html
│       └── success.html
│
├── static/
│   ├── css/
│   │   ├── style.css              # Styling (Bootstrap overrides)
│   │   └── bootstrap.min.css
│   ├── js/
│   │   ├── main.js                # Optional frontend logic
│   │   └── jquery.min.js
│   ├── images/
│   │   └── logo.png
│   └── uploads/                   # Temporary file access (served if needed)
│
├── nginx/
│   ├── testsite.conf              # nginx reverse proxy configuration
│   └── snippets/
│       └── proxy_params.conf      # Shared proxy configuration
│
├── tests/
│   ├── test_normal_requests.py    # Valid traffic simulation
│   ├── test_attack_payloads.py    # Attack payload automation
│   ├── payloads/
│   │   ├── sql_injection.txt
│   │   ├── xss.txt
│   │   ├── lfi.txt
│   │   ├── xxe.txt
│   │   ├── redirect.txt
│   │   └── ddos_script.py
│   └── results/
│       └── traffic_samples.log
│
├── docs/
│   ├── README.md                  # Documentation of this component
│   ├── architecture_diagram.png   # Topology diagram for integration
│   ├── endpoint_specs.md          # Endpoint details and vulnerabilities
│   ├── payload_reference.md       # Common payloads for Suricata/ML testing
│   ├── logging_policy.md          # Logging format for integration
│   └── test_report.md             # Summary of Phase 2 results
│
└── .env                           # Environment variables (secret key, DB URI)
```

---

## 🧩 Folder/Component Explanations

### 🔹 Root Level

* **`app.py`** — Application entry point. Imports and registers routes, services, and middleware.
* **`config.py`** — Central configuration: database, upload path, logging settings, secret key.
* **`models.py`** — Database ORM classes (User, Feedback, UploadedFile, LogEvent).
* **`requirements.txt`** — Python dependencies list (Flask, SQLAlchemy, PyClamd, etc.).
* **`wsgi.py`** — Gunicorn entry point for production use.

### 🔹 `instance/`

Holds runtime data that shouldn’t be tracked in Git — database, temp configs, or sensitive info.

### 🔹 `logs/`

Dedicated directory for log management:

* **`app.log`** — Main Flask events (info, warnings, attacks).
* **`error.log`** — Exceptions and tracebacks.
* **`access.log`** — Optional HTTP logs (mirrors nginx for ML correlation).

### 🔹 `uploads/`

Holds uploaded files from users:

* **`safe/`** — Non-malicious files.
* **`quarantine/`** — Files flagged by ClamAV.

### 🔹 `src/`

All application logic (Python code) neatly organized:

* **`routes/`** — One file per major endpoint category (makes code readable).
* **`services/`** — Background logic, helpers, antivirus scanning, logging setup.
* **`middleware/`** — Optional request and security handlers.
* **`templates/`** — Jinja2 HTML templates.

### 🔹 `static/`

Public assets:

* **`css/`** — Stylesheets (Bootstrap + custom).
* **`js/`** — JavaScript, AJAX requests, or DoS simulation scripts.
* **`images/`** — Branding, diagrams, etc.
* **`uploads/`** — Only used for testing if public file access needed.

### 🔹 `nginx/`

nginx reverse proxy configuration for the testsite.
Keeps deployment setup reproducible. Example:

* `testsite.conf` — main site config (listen 80 → proxy_pass 127.0.0.1:5000).
* `snippets/proxy_params.conf` — headers and proxy defaults.

### 🔹 `tests/`

Automation for both **legitimate traffic** and **malicious payload testing**.
Useful for replaying test cases during DPI and ML evaluation.

### 🔹 `docs/`

Comprehensive documentation — this folder ensures the test website can be independently understood by future maintainers or AI assistants. Includes endpoint specs, payload references, and test summaries.

### 🔹 `.env`

Contains environment variables like:

```
FLASK_ENV=development
SECRET_KEY=adaptive_ngfw_key
SQLALCHEMY_DATABASE_URI=sqlite:///instance/database.db
UPLOAD_FOLDER=uploads/safe
```

*(excluded from Git via `.gitignore`)*

---

## 🧠 Recommended `.gitignore` (for repo root)

```
# Python
__pycache__/
*.pyc
instance/
venv/
.env
uploads/
logs/
*.db

# Node/npm (if added)
node_modules/

# OS
.DS_Store
Thumbs.db
```

---

## ⚙️ Key Supporting Files

### `requirements.txt`

```
Flask==3.0.2
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.2
PyClamd==0.4.0
requests==2.32.3
gunicorn==21.2.0
lxml==5.2.1
python-dotenv==1.0.1
```

### `nginx/testsite.conf`

```nginx
server {
    listen 80;
    server_name _;
    access_log /home/ubuntu/ngfw-prototype/web/logs/access.log;
    error_log  /home/ubuntu/ngfw-prototype/web/logs/error.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        include /etc/nginx/proxy_params;
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📘 Developer Notes for AI / Collaborators

**Goal:** Build this test website as a deliberately vulnerable application to test and demonstrate the **Adaptive NGFW** capabilities.

### Context Summary for the AI Developer

* The NGFW system inspects, logs, and blocks malicious activities targeting this website.
* The website must generate both **normal** and **malicious** HTTP traffic patterns.
* Each endpoint intentionally contains at least one vulnerability.
* All requests and actions should be **logged** with client IPs and timestamps.
* The project is for **academic and prototype purposes only** — not a hardened production system.

### Implementation Guidelines

* Follow modular code structure shown above.
* Use clear inline comments documenting which vulnerabilities each endpoint simulates.
* Ensure nginx reverse proxy works with Flask on port 5000.
* Integrate ClamAV scanning for uploaded files using PyClamd.
* Include test payload files to support DPI and ML evaluation.
* Maintain proper version control (push to existing repo `NGFW-Prototype/web/`).

---