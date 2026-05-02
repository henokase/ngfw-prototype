# 🧱 Project Design Report (PDR)

## Adaptive NGFW — Test Website Component

### Document Purpose

This document describes the design, objectives, features, and implementation plan for the **Test Website** — a key component of the **Adaptive Next Generation Firewall (NGFW) Prototype**. It provides complete context for AI agents or developers contributing to its creation.

---

## 1. Project Context

### 1.1 Overview of the Adaptive NGFW Project

The **Adaptive NGFW** prototype is a research and development project designed to simulate a **modern, intelligent network security system**.
It combines:

* **Stateful packet filtering** (using nftables),
* **Deep Packet Inspection (DPI)** (via Suricata),
* **Antivirus scanning** (via ClamAV),
* **Machine Learning–based anomaly detection** (using CIC-IDS2017 dataset), and
* **Automated response systems** (dynamic IP blocking, logging, dashboard alerting).

The system runs in a **dual-VM topology**:

* **VM1:** Ubuntu Desktop – acts as the **firewall gateway (NGFW)**.
* **VM2:** Ubuntu Server – hosts the **test web application (victim site)**.

Traffic flows from client → NGFW → Test Website, allowing full inspection and adaptive protection.

---

## 2. Role of the Test Website

### 2.1 Purpose

The test website acts as the **victim environment** behind the NGFW.
It is **intentionally vulnerable** to various cyberattacks so that:

* The NGFW can capture, analyze, and respond to malicious traffic.
* Machine learning models can classify abnormal patterns.
* Antivirus modules can inspect uploaded files.
* The adaptive response system can dynamically block attacker IPs.

**In essence:**

> The Test Website generates realistic network and application-layer traffic to evaluate every capability of the Adaptive NGFW system.

### 2.2 Scope of Functionality

The website includes multiple vulnerable modules simulating:

* SQL injection
* Command injection
* File upload (malware)
* Cross-Site Scripting (XSS)
* XML External Entity (XXE)
* Path traversal
* Open redirects

It also includes **legitimate interactions** — login, registration, form submission, file upload, and browsing.

---

## 3. Network Integration Architecture

### 3.1 Deployment Topology

```
[Client / Attacker]
        │
   (eth0: external)
┌────────────────────────┐
│  VM1 – Adaptive NGFW   │
│  • nftables filtering   │
│  • Suricata (DPI)       │
│  • ClamAV scanner       │
│  • ML anomaly engine    │
│  • Auto IP blocking     │
│  • Dashboard & logging  │
│  (acts as proxy/NAT)    │
└────────────────────────┘
   (eth1: internal)
        │
[VM2 – Test Website Server]
```

* **VM1** handles all packet routing and inspection.
* **VM2** runs the vulnerable test web app.
* HTTP/HTTPS traffic is DNATed or proxied from VM1 → VM2.

### 3.2 Network Interfaces

| Interface | Host | Role                    | Example IP |
| --------- | ---- | ----------------------- | ---------- |
| `enp0s3`  | VM1  | External (Internet/NAT) | 10.0.2.15  |
| `enp0s8`  | VM1  | Internal bridge         | 10.0.0.1   |
| `enp0s8`  | VM2  | Internal interface      | 10.0.0.5   |

---

## 4. Technical Architecture of the Test Website

### 4.1 Technology Stack

| Layer               | Tool / Framework                        | Purpose                                         |
| ------------------- | --------------------------------------- | ----------------------------------------------- |
| **Backend**         | Flask (Python 3.x)                      | Simple, modular web framework                   |
| **Web Server**      | Nginx                                   | Reverse proxy to Flask (port 80 → 5000)         |
| **Database**        | SQLite                                  | Lightweight relational DB for user and log data |
| **Storage**         | Local directory (`uploads/`)            | For safe and quarantined file uploads           |
| **Frontend**        | HTML, Bootstrap 5.3.0, Bootstrap Icons  | Clean responsive interface with forms           |
| **Logging**         | Python logging → `logs/app.log`, `logs/error.log` | Request logging and error tracking   |
| **AntiVirus**       | ClamAV (pyClamd)                        | Local file scanning with simulation fallback    |

---

## 5. Website Design Overview

### 5.1 Core Principles

* Modular structure (`app.py`, `models.py`, `templates/`, `static/`).
* Every feature generates distinct, traceable traffic.
* Intentional vulnerabilities reflect real-world attack vectors.
* Supports integration with ClamAV and Suricata logs.
* Serves as dataset generator for ML analysis.

### 5.2 High-Level Functional Flow

1. A client sends a request to the public IP of the firewall.
2. NGFW intercepts and inspects the packet.
3. Clean traffic is forwarded to the test site.
4. The website responds; Suricata logs the session.
5. If malicious:

   * DPI or ClamAV flags the content.
   * ML model identifies anomaly.
   * Decision Engine adds source IP to blocked list in nftables.

---

## 6. Detailed Module Specifications

### 6.1 Vulnerable Modules (Attack Simulation)

| **Module**                    | **Endpoint**                    | **Vulnerability**              | **Example Attack**                          | **Expected NGFW Detection** |
| ----------------------------- | ------------------------------- | ------------------------------ | ------------------------------------------- | --------------------------- |
| **1. Authentication**         | `POST /login`                   | SQL Injection                  | `' OR 1=1--`                                | DPI regex + ML anomaly      |
| **2. File Upload**            | `POST /upload`                  | Malware/webshell upload        | EICAR test file                             | ClamAV scan + IP block      |
| **3. Command Execution**      | `POST /command/execute`         | Command injection              | `8.8.8.8; cat /etc/passwd`                  | DPI + ML anomaly            |
| **4. File Viewer**            | `GET /file/viewer`              | Path traversal                 | `../../etc/passwd`                          | DPI + auto block            |
| **5. Feedback**               | `POST /feedback`                | Stored/Reflected XSS           | `<script>alert(1)</script>`                 | DPI regex                   |
| **6. XML API**                | `POST /api/xml`                 | XXE attack                     | `<!ENTITY xxe SYSTEM "file:///etc/passwd">` | DPI payload analysis        |
| **7. Redirect**               | `GET /redirect?url=...`         | Open redirect                  | `/redirect?url=http://evil.com`             | DPI pattern detection       |

### 6.2 Legitimate Modules (Normal Traffic Generation)

| **Module**                    | **Endpoint**                    | **Purpose**                               |
| ----------------------------- | ------------------------------- | ----------------------------------------- |
| **Registration**              | `GET/POST /register`            | User account creation                     |
| **User Profile**              | `GET/POST /profile`             | View/edit user settings                   |
| **Stats Dashboard**           | `GET /stats`                    | View attack statistics and activity logs  |
| **About / Help**              | `GET /about`, `GET /help`       | Informational pages                       |
| **Upload History**            | `GET /uploads`                  | View previously uploaded files            |

Each module includes both vulnerable and secure implementations to compare detection results.

---

## 7. Integration with NGFW Components

| **Firewall Component**       | **Integration with Test Website**         | **Description**                         |
| ---------------------------- | ----------------------------------------- | --------------------------------------- |
| **Packet Filter (nftables)** | Routes all external traffic to web server | Enforces network-level security rules   |
| **Suricata DPI**             | Monitors and logs HTTP requests           | Detects SQLi, XSS, LFI, etc.            |
| **ClamAV**                   | Scans uploaded files from `/uploads`      | Detects malware and EICAR patterns      |
| **ML Anomaly Detection**     | Monitors request rate, payload anomalies  | Identifies DDoS and unknown threats     |
| **Decision Engine**          | Receives alerts from Suricata/ML          | Adds malicious IPs to `blocked_ips` set |
| **Dashboard**                | Displays attacks and blocked IPs          | Visual feedback for analysis            |

---

## 8. Development and Testing Workflow

### 8.1 Development Steps

1. **Clone Repository**: `git clone` from NGFW GitHub repo.
2. **Create Web Folder**: `web/` directory for Flask code.
3. **Create venv on VM2**: `python3 -m venv /home/ubuntuhero/ngfw/`.
4. **Install Dependencies**: `pip install -r requirements.txt` (Flask, SQLAlchemy, Werkzeug, pyClamd, requests).
5. **Develop Modules**: Implement endpoints sequentially with vulnerable and secure variants.
6. **Add Templates and Static Assets**: Use Bootstrap 5.3.0 for responsive UI.
7. **Configure nginx Reverse Proxy** (port 80 → 5000).
8. **Verify Communication via VM1** (DNAT 80 → 10.0.0.5:80).
9. **Add Logging and Test Payloads**.
10. **Document Results and Commit to GitHub.**

---

### 8.2 Testing Workflow

| Step | Action                       | Expected Outcome                |
| ---- | ---------------------------- | ------------------------------- |
| 1    | Access site through firewall | Normal operation                |
| 2    | Run SQLi payload             | Suricata detects and logs       |
| 3    | Upload malware file          | ClamAV detects and quarantines  |
| 4    | Run DoS tool                 | ML flags and firewall blocks IP |
| 5    | Check dashboard              | Real-time attack data visible   |

---

## 9. Deliverables

| **Deliverable**                | **Description**                                      | **Status** |
| ------------------------------ | ---------------------------------------------------- | ---------- |
| `web/src/` source code         | Complete Flask app with all vulnerable modules       | Complete   |
| `web/src/templates/`           | 19 HTML templates (Bootstrap 5.3)                    | Complete   |
| `web/src/static/`              | Custom CSS styling                                   | Complete   |
| `web/src/middleware/`          | Rate limiter, security headers, request logger       | Complete   |
| `web/src/services/`            | ClamAV integration, antivirus scanning service       | Complete   |
| `web/.env`                     | Environment configuration template                   | Complete   |
| `web/docs/VM2_API_DOCS.md`     | Complete API reference with attack examples          | Complete   |
| `web/docs/SETUP_DEPLOYMENT.md` | VM provisioning and deployment guide                 | Complete   |
| `web/docs/ARCHITECTURE_DECISIONS.md` | Design rationale and detection flow           | Complete   |
| `web/docs/IMPLEMENTATION_STATUS.md` | Feature tracking and roadmap                  | Complete   |
| `web/nginx.conf`               | Reverse proxy configuration (reference)              | Complete   |

---

## 10. Implementation Notes

### 10.1 Architecture Clarifications

* **VM1 handles detection independently** — Suricata and ClamAV on VM1 detect threats without receiving alerts from VM2
* **No VM2→VM1 API communication** — The malware alert endpoint was removed; VM1 inspects traffic at the network level
* **VM2 ClamAV is local-only** — Used for immediate feedback to users (quarantine/safe), not for NGFW blocking decisions
* **Rate limiting uses session/account IDs** — VM2 only sees VM1's NAT IP (`10.0.0.1`), so IP-based rate limiting is ineffective

### 10.2 Completed Features

* 7 vulnerable endpoints with realistic attack vectors
* 6 legitimate endpoints for normal traffic generation
* Session-based rate limiting (100 req/min per account, 50 req/sec global flood protection)
* Security headers middleware (CSP, X-Frame-Options, X-XSS-Protection, etc.)
* Request/response logging to `logs/app.log`
* ClamAV integration with simulation fallback
* File quarantine system (malicious → `uploads/quarantine/`, safe → `uploads/safe/`)
* 19 HTML templates with Bootstrap 5.3 UI
* Stats dashboard showing attack counts and blocked IPs
* Seed users for immediate testing: `admin/admin123`, `user/password`, `test/test123`, `guest/guest`

---

## 11. Success Criteria

| **Metric**                          | **Target** |
| ----------------------------------- | ---------- |
| Full functionality of all 7 vulnerable modules | Complete |
| Legitimate endpoints (registration, profile, stats, help) | Complete |
| Accessible via NGFW external IP (VM1 DNAT) | Verified |
| Proper forwarding and request logging | Verified |
| Attack payloads trigger Suricata/ClamAV events | Verified |
| Rate limiting enforces per-session/account limits | Verified |
| ClamAV scans uploads (real or simulation mode) | Verified |
| No routing or proxy errors | Verified |

---

### ✅ Final Summary

This test website is a **controlled attack simulation platform** for the Adaptive NGFW prototype.
It emulates real-world web vulnerabilities to generate observable data for packet filtering, DPI, antivirus scanning, and ML-based threat detection.

**Implementation Status:** All modules are complete and deployed on VM2. The website:

* Serves as a realistic backend target behind the firewall (VM1 DNAT 80 → 10.0.0.5:80)
* Generates both malicious and legitimate traffic for NGFW validation
* Provides local ClamAV scanning with quarantine for immediate user feedback
* Includes rate limiting, security headers, and comprehensive request logging
* Forms the core of the Phase 2 deliverable in the NGFW implementation roadmap
