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
* DDoS-style stress requests

It must also include **legitimate interactions** for ML training and comparison — login, form submission, file upload, and browsing.

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
| `eth0`    | VM2  | Internal interface      | 10.0.0.5   |

---

## 4. Technical Architecture of the Test Website

### 4.1 Technology Stack

| Layer               | Tool / Framework                        | Purpose                                         |
| ------------------- | --------------------------------------- | ----------------------------------------------- |
| **Backend**         | Flask (Python 3.x)                      | Simple, modular web framework                   |
| **Web Server**      | Nginx                                   | Reverse proxy to Flask (port 80 → 5000)         |
| **Database**        | SQLite                                  | Lightweight relational DB for user and log data |
| **Storage**         | Local directory (`/uploads/`)           | For file uploads (to be scanned)                |
| **Frontend**        | HTML, Bootstrap                         | Clean interface with forms and links            |
| **Logging**         | Flask logger → `app.log`                | For all requests and attack attempts            |                     |

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

| **Module**                    | **Purpose / Feature**                 | **Key Vulnerabilities**        | **Example Attack**                          | **Expected NGFW Detection** |
| ----------------------------- | ------------------------------------- | ------------------------------ | ------------------------------------------- | --------------------------- |
| **1. Authentication Page**    | Simulate login logic with SQL backend | SQL Injection                  | `' OR 1=1--`                                | DPI regex + ML anomaly      |
| **2. File Upload Page**       | Accept user uploads                   | File upload (malware/webshell) | EICAR test file                             | ClamAV scan + IP block      |
| **3. Command Execution Page** | “Ping test” function                  | Command injection              | `8.8.8.8; cat /etc/passwd`                  | DPI + ML anomaly            |
| **4. Path Traversal Page**    | File viewer                           | Directory traversal            | `../../etc/passwd`                          | DPI + auto block            |
| **5. Feedback Page**          | User comment box                      | XSS (stored/reflected)         | `<script>alert(1)</script>`                 | DPI regex                   |
| **6. XML API**                | File upload via XML POST              | XXE attack                     | `<!ENTITY xxe SYSTEM "file:///etc/passwd">` | DPI payload analysis        |
| **7. Search / Chat Endpoint** | Reflect user queries                  | Parameter injection            | `%3Cscript%3E`                              | ML + DPI                    |
| **8. Compute Endpoint**       | CPU-heavy request handler             | DDoS simulation                | `wrk -t12 -c400`                            | ML anomaly, auto block      |
| **9. Redirect Feature**       | Link redirect                         | Open redirect                  | `/redirect?url=http://fake.com`             | DPI pattern detection       |

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

1. **Clone Repository**: Continue using main NGFW GitHub repo (`C:\Projects\NGFW-Prototype`).
2. **Create Web Folder**: `web/` directory for Flask code.
3. **Create venv on VM2**: `python3 -m venv ~/ngfw`.
4. **Install Dependencies**: Flask, SQLAlchemy, Werkzeug, gunicorn.
5. **Develop Modules**: Implement endpoints sequentially.
6. **Add Templates and Forms**: Use Bootstrap forms for clarity.
7. **Configure nginx Reverse Proxy**.
8. **Verify Communication via VM1 (DNAT 80 → 10.0.0.5:80)**.
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

| **Deliverable**         | **Description**                  |
| ----------------------- | -------------------------------- |
| `web/` source code      | Full Flask app with all modules  |
| `nginx.conf`            | Reverse proxy configuration      |
| `app.log`               | Access and attack logs           |
| `uploads/`              | Directory for uploaded files     |
| `docs/test_payloads.md` | Test payloads used in evaluation |
| `docs/phase2_report.md` | Documentation of implementation  |

---

## 10. Role of the AI Developer

The AI agent (or assistant) tasked with building this website should:

1. Understand that this is **not a production app**, but a *controlled vulnerable target* for NGFW testing.
2. Follow Flask best practices for structure, but deliberately introduce **vulnerabilities** in specific endpoints as described.
3. Ensure the app:

   * Logs all interactions,
   * Exposes endpoints exactly as specified,
   * Is compatible with nginx reverse proxy (port 80 → 5000),
   * Runs on VM2 with IP `10.0.0.5`.
4. Maintain readability, comments, and modular code for later ML data extraction.

The AI’s job:

> Implement, configure, and test the **complete test website** so it integrates smoothly with the Adaptive NGFW system for traffic inspection, file scanning, and adaptive blocking demonstration.

---

## 11. Success Criteria

| **Metric**                          | **Target** |
| ----------------------------------- | ---------- |
| Full functionality of all 8 modules | ✅          |
| Accessible via NGFW external IP     | ✅          |
| Proper forwarding and logging       | ✅          |
| Attack payloads trigger NGFW events | ✅          |
| No routing or proxy errors          | ✅          |

---

### ✅ Final Summary

This test website is a **controlled attack simulation platform** for the Adaptive NGFW prototype.
It emulates real-world web vulnerabilities to generate observable data for packet filtering, DPI, antivirus scanning, and ML-based threat detection.

When complete, it will:

* Serve as a realistic backend target behind the firewall.
* Enable full validation of the firewall’s detection and adaptive response pipeline.
* Form the core of the **Phase 2 deliverable** in your NGFW implementation roadmap.
