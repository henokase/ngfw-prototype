# NGFW Prototype

> Open-source Next-Generation Firewall prototype combining Suricata, nftables stateful filtering, ClamAV malware detection, and ML-based anomaly detection with a React admin dashboard.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [System Topology](#system-topology)
- [Components](#components)
- [Data Flow](#data-flow)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

The NGFW Prototype is an academic research project that demonstrates a modern, defense-in-depth network security gateway. It integrates seven layers of detection and response into a unified system:

- **Stateful firewall** (nftables) with dynamic IP blocking and TTL-based expiry
- **Deep packet inspection** (Suricata 8.0.2) with 145 custom detection rules
- **Malware scanning** (ClamAV) via Suricata file extraction pipeline
- **ML anomaly detection** (5-model soft-voting ensemble: RF + XGB + DT + LR + CatBoost)
- **Centralized decision engine** (Flask REST API with 23+ endpoints)
- **Real-time monitoring** (React 19 dashboard with SSE)
- **Intentionally vulnerable test website** for attack validation

The system is deployed as a two-VM lab in VirtualBox. VM1 acts as the network gateway running all security services. VM2 hosts a deliberately vulnerable Flask web application used as the attack surface for validating detection and blocking capabilities.

> **WARNING:** This project contains intentionally vulnerable code for security research. Never deploy to production or expose to untrusted networks.

## Architecture

The system follows a three-layer architecture, with all services running on VM1 (gateway) except the test target on VM2:

```
                    ┌──────────────────────────────────────┐
                    │         VISUALIZATION LAYER          │
                    │   React Admin Dashboard (port 3000)  │
                    │     Real-time SSE, Auth, 7 Pages     │
                    └────────────────┬─────────────────────┘
                                     │ REST + SSE
                    ┌────────────────▼─────────────────────┐
                    │           DECISION LAYER             │
                    │  Flask Control API (port 5001)       │
                    │  ├─ Block management (nftables)      │
                    │  ├─ Event logging (SQLite)           │
                    │  ├─ Service control (systemd)        │
                    │  ├─ System/network stats             │
                    │  └─ Data export (JSON/CSV)           │
                    └────────────────┬─────────────────────┘
                                     │
            ┌────────────────────────┼────────────────────────┐
            │                        │                        │
  ┌─────────▼──────────┐  ┌─────────▼──────────┐  ┌─────────▼──────────┐
  │   DETECTION LAYER  │  │   DETECTION LAYER  │  │   DETECTION LAYER  │
  │  Suricata          │  │  ClamAV Antivirus  │  │  ML Ensemble       │
  │  AF_PACKET, EVE    │  │  clamd, INSTREAM   │  │  RF+XGB+DT+LR+CB   │
  │  145 custom rules  │  │  Port 3310         │  │  Port 5003          │
  └────────────────────┘  └────────────────────┘  └────────────────────┘
```

1. **Detection Layer** — Suricata inspects all traffic via AF_PACKET on both interfaces. Files are extracted and scanned by ClamAV. Network flows are analyzed by the ML ensemble. Detections are forwarded to the Decision Layer.
2. **Decision Layer** — The Flask Control API receives detection events, executes blocking actions via nftables, logs all events to SQLite, and streams real-time updates via SSE.
3. **Visualization Layer** — The React admin dashboard consumes REST and SSE endpoints for live monitoring and manual control.

## System Topology

The project runs on two VirtualBox VMs:

| VM | Role | Interfaces | Purpose |
|----|------|-----------|---------|
| VM1 (Gateway) | NGFW | enp0s3 (192.168.1.70/24 external), enp0s8 (10.0.0.1/24 internal) | nftables firewall, Suricata, ClamAV, ML inference, Control API, Dashboard |
| VM2 (Test Server) | Target | 10.0.0.5/24 | Deliberately vulnerable Flask web application |

```
[Internet/Host] --> enp0s3 (192.168.1.70) --> VM1 (NGFW Gateway) --> enp0s8 (10.0.0.1) --> VM2 (Test App 10.0.0.5)
                                                  ^
                                          [Admin Dashboard]
                                           (port 3000 on VM1)
```

VM1 performs NAT masquerading so VM2 can access the internet through the gateway. All traffic between the external network and VM2 passes through Suricata's inspection on VM1, allowing it to see real source IPs directly (no NAT correlation needed).

## Components

### 1. NGFW Control API

- **Purpose:** Central decision engine — manages IP blocking, event logging, service control, and real-time streaming
- **Technology:** Flask 3.0+, SQLAlchemy 2.0+, SQLite
- **Port:** 5001 (binds to 0.0.0.0)
- **Key files:** `/opt/ngfw-control/app.py`, `config.py`, `database.py`, `firewall_service.py`, `logger.py`
- **Key features:**
  - 23+ REST endpoints for block management, logging, stats, export
  - nftables integration via `firewall_service.py` (sudo nft wrapper)
  - SQLite database with blocks, logs, ml_predictions, and malware_alerts tables (plus backup tables)
  - SSE real-time stream (5-second poll interval) for dashboard live updates
  - Rotating file logging (app log + security log)
  - Service control via systemd with start/stop/restart/status
  - Data export in JSON and CSV formats

### 2. Suricata

- **Purpose:** Deep packet inspection — detects attacks via signature matching and extracts files for malware scanning
- **Technology:** Suricata 8.0.2, AF_PACKET capture, EVE JSON logging
- **Port:** N/A (kernel-level packet capture)
- **Config:** `/etc/suricata/suricata.yaml`
- **Key features:**
  - AF_PACKET capture on both enp0s3 (cluster-id 99) and enp0s8 (cluster-id 100)
  - 34 EVE event types enabled (alert, http, dns, tls, files, smtp, ssh, etc.)
  - File extraction with SHA-256 hashing to `/var/log/suricata/filestore/`

### 3. ClamAV Malware Detection

- **Purpose:** Scans files extracted by Suricata for malware signatures
- **Technology:** ClamAV clamd daemon, INSTREAM protocol
- **Port:** 3310 (TCP), `/var/run/clamav/clamd.ctl` (Unix socket)
- **Key features:**
  - Integrated with `suri_clam_processor.py` via custom minimal clamd client
  - Scans files from Suricata filestore using INSTREAM protocol
  - On detection: logs event, stores malware alert in DB, blocks source IP for 24h
  - Scan cache (7s TTL) and alert dedup cache (5s TTL) prevent duplicate processing

### 4. ML Inference Service

- **Purpose:** Real-time anomaly detection on network flow features using an ensemble of ML models
- **Technology:** Flask, scikit-learn, XGBoost, CatBoost, joblib
- **Port:** 5003
- **Key files:** `/opt/ngfw-ml/inference_service.py`, `ensemble_config.json`
- **Key features:**
  - 5-model soft-voting ensemble: Random Forest + XGBoost + Decision Tree + Logistic Regression + CatBoost
  - Equal weights (0.2 each) with StandardScaler preprocessing
  - 52 CICIDS2017-compatible flow features
  - Three-tier action policy: allow (<0.5), alert (0.5-0.74), block (>=0.75)
  - Block actions sent to Control API via `/api/block_ip`
  - Predictions stored in `ml_predictions` database table
  - 83.12% ensemble accuracy on CICIDS2017 test set

### 5. CICFlowMeter Bridge

- **Purpose:** Packet capture and flow feature extraction feeding the ML service
- **Technology:** cicflowmeter (scapy-based), Python
- **Interface:** enp0s3 (external)
- **Key files:** `/opt/ngfw-ml/cicflowmeter_bridge.py`
- **Key features:**
  - Creates sniffer on enp0s3, outputs 52 flow features
  - POSTs completed flows directly to ML service `/predict` endpoint
  - Waits for ML service readiness before starting capture

### 6. Admin Dashboard

- **Purpose:** Real-time monitoring and manual control of the NGFW system
- **Technology:** React 19, TypeScript, Vite 6, Tailwind CSS v4, lucide-react
- **Port:** 3000
- **Key files:** `src/App.tsx`, `src/services/api.ts`, `src/services/sse.ts`
- **Key features:**
  - 7 pages: Dashboard Home, Firewall Management, Attack Logs, Malware Detection, ML Detection, Service Control, Network Overview
  - Authentication via AuthContext (login page at `/login`, credentials: admin/Pass123!)
  - Real-time SSE integration with auto-reconnect
  - IP block/unblock/clear operations via REST API
  - Service start/stop/restart controls
  - Data export (JSON/CSV) for logs, ML predictions, and malware alerts
  - Protected routes with redirect to login

### 7. Test Website (VM2)

- **Purpose:** Intentionally vulnerable Flask web application for testing NGFW detection capabilities
- **Technology:** Flask, SQLAlchemy, nginx reverse proxy
- **Port:** 5000 (Flask), 80 (nginx)
- **Key files:** `web/app.py`, `config.py`, `models.py`, `src/routes/`
- **Vulnerable endpoints:**
  - `/login` — SQL Injection
  - `/cmd` — Command Injection
  - `/upload` — File upload with ClamAV scanning
  - `/feedback` — Stored XSS
  - `/file` — Path Traversal
  - `/api/xml` — XXE Injection
  - `/redirect` — Open Redirect
- **Middleware:** Rate limiter, request logger, security headers

### 8. nftables Firewall

- **Purpose:** Stateful packet filtering, dynamic IP blocking with TTL, NAT
- **Technology:** nftables v1.0.9, kernel 6.14.0
- **Config:** `/etc/nftables.conf`
- **Key features:**
  - Default-deny policy on input and forward chains
  - Dynamic IP blocking via `set blocked_ips` with `flags timeout` and `size 65536`
  - SYN flood protection (40/sec, burst 100)
  - UDP flood protection (100/sec, burst 50)
  - NAT masquerading for VM2 outbound traffic
  - Port forwarding (HTTP 80 -> VM2)
  - SSH access allowed on port 22
  - Connection tracking with `ct state established,related accept`

## Data Flow

The attack detection pipeline operates as follows:

```
Attacker --> enp0s3 --> nftables (checks blocked_ips set)
                         |
                     ┌───▼────────────────────────────────────┐
                     │  Suricata AF_PACKET (enp0s3 + enp0s8) │
                     │  ├─ Protocol parsing (HTTP, DNS, TLS) │
                     │  ├─ Rule engine (145 custom rules)     │
                     │  ├─ File extraction (filestore v2)     │
                     │  └─ EVE JSON log output                │
                     └───┬────────────────────────────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
     ┌────────────┐ ┌──────────┐ ┌──────────────────┐
     │ suri_clam  │ │ suri_clam│ │ cicflowmeter     │
     │ processor  │ │ processor│ │ bridge           │
     │ (alert     │ │ (fileinfo│ │ (flow features)  │
     │  events)   │ │  events) │ │                  │
     └──────┬─────┘ └────┬─────┘ └────────┬─────────┘
            │            │                │
            ▼            ▼                ▼
     ┌──────────────────────────────────────────────┐
     │           Decision Engine API                 │
     │  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
     │  │ Block IP │  │ Log      │  │ Malware    │  │
     │  │ (nftables)│  │ Event   │  │ Alert      │  │
     │  └──────────┘  │ (SQLite) │  │ (SQLite)   │  │
     │                └──────────┘  └────────────┘  │
     │  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
     │  │ ML Pred  │  │ SSE      │  │ Export     │  │
     │  │ (SQLite) │  │ Stream   │  │ (JSON/CSV) │  │
     │  └──────────┘  └──────────┘  └────────────┘  │
     └──────────────────────────────────────────────┘
```

1. Attacker sends a request toward VM2 (10.0.0.5)
2. nftables checks the `blocked_ips` set — if the source IP is blocked, the packet is dropped immediately
3. Suricata captures all packets via AF_PACKET on both interfaces, performs protocol parsing, and evaluates against 145 custom rules
4. Suricata writes all events to `/var/log/suricata/eve.json` (line-delimited JSON)
5. `suri_clam_processor.py` tails the EVE log and handles two event types:
   - **alert events:** Checks severity, category, and signature to decide blocking action. High-severity (1-2) alerts trigger a 24h block; custom rules (SID 1000000+) trigger a 1h block.
   - **fileinfo events:** Locates the extracted file in the filestore, scans it with ClamAV, and blocks the source IP for 24h if malware is detected.
6. `cicflowmeter_bridge.py` captures flow features on enp0s3 and POSTs them to the ML service at `/predict`
7. The ML service applies StandardScaler, scores the features with all 5 models, computes the ensemble confidence, and takes action (allow/alert/block)
8. The Decision Engine API (Flask, port 5001) receives all block/alert/log requests, executes nftables commands, stores events in SQLite, and streams updates via SSE
9. The Dashboard (React, port 3000) displays all events, blocks, and system status in real time

## Installation

### Prerequisites

- Ubuntu 22.04+ (or similar Linux distribution)
- Python 3.12+
- Node.js 20+ (for dashboard)
- Suricata 8.0.2+
- nftables v1.0.9+
- ClamAV + clamd daemon
- VirtualBox (for two-VM deployment)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ngfw-prototype
```

### 2. Control API Setup (VM1)

```bash
cd ngfw-control
pip install -r requirements.txt
# Flask>=3.0.0, SQLAlchemy>=2.0.0, conntrack, requests, netifaces
```

### 3. ML Service Setup (VM1)

```bash
cd ngfw-ml
pip install flask flask-cors joblib scikit-learn xgboost catboost numpy requests
```

### 4. Dashboard Setup (VM1)

```bash
cd ngfw-dashboard
npm install
# React 19, Vite 6, Tailwind CSS v4, lucide-react, react-router-dom v7
```

### 5. Suricata Configuration (VM1)

```bash

# Validate configuration
sudo suricata -T -c /etc/suricata/suricata.yaml

# Restart Suricata
sudo systemctl restart suricata
```

Key Suricata configuration:
- AF_PACKET capture on enp0s3 (cluster-id 99) and enp0s8 (cluster-id 100)
- EVE JSON logging enabled with alert, fileinfo, http, dns, tls, and 28 other event types
- File extraction to `/var/log/suricata/filestore/` with SHA-256 hashing

### 6. nftables Configuration (VM1)

```bash
# Apply nftables ruleset
sudo nft -f /etc/nftables.conf

# Allow required ports (dashboard, API, ML)
sudo nft add rule inet firewall input tcp dport 3000 accept
sudo nft add rule inet firewall input tcp dport 5001 accept
sudo nft add rule inet firewall input tcp dport 5003 accept
```

### 7. ClamAV Setup (VM1)

```bash
# Install ClamAV daemon
sudo apt-get install clamav-daemon

# Configure clamd socket at /var/run/clamav/clamd.ctl
# Ensure clamd is running before starting the processor
sudo systemctl start clamav-daemon

# Update virus definitions
sudo freshclam
```

### 8. Test Website Setup (VM2)

```bash
cd web
pip install -r requirements.txt
# Flask, Flask-SQLAlchemy, PyClamd, gunicorn, lxml, python-dotenv
python app.py
```

## Configuration

### Environment Variables

| Component | Variable | Default | Description |
|-----------|----------|---------|-------------|
| Control API | `NGFW_BIND_HOST` | `0.0.0.0` | API bind address |
| Control API | `NGFW_BIND_PORT` | `5001` | API port |
| Control API | `NGFW_DB_PATH` | `/opt/ngfw-control/ngfw.db` | SQLite database path |
| Control API | `NGFW_LOG_DIR` | `/opt/ngfw-control/logs` | Log directory |
| Control API | `NGFW_NFT_BIN` | `nft` | nftables binary path |
| Control API | `NGFW_NFT_TABLE` | `inet firewall` | nftables table name |
| Control API | `NGFW_NFT_BLOCK_SET` | `blocked_ips` | nftables blocked IP set |
| Control API | `NGFW_DEFAULT_TTL` | `1h` | Default block duration |
| Control API | `NGFW_API_KEY` | (unset) | Optional API authentication |
| Control API | `NGFW_SECRET_KEY` | `ngfw_control_dev_secret_change_me` | Flask secret key |
| Control API | `NGFW_LOG_LEVEL` | `INFO` | Logging level |
| suri_clam_processor | `SURI_EVE_LOG` | `/var/log/suricata/eve.json` | EVE log path |
| suri_clam_processor | `SURI_FILESTORE_DIR` | `/var/log/suricata/filestore` | Filestore directory |
| suri_clam_processor | `NGFW_API_URL` | `http://127.0.0.1:5001` | API base URL |
| suri_clam_processor | `CLAMD_UNIX_SOCKET` | `/var/run/clamav/clamd.ctl` | ClamAV socket |
| suri_clam_processor | `SURI_SCAN_CACHE_TTL` | `7` | Scan dedup TTL (seconds) |
| suri_clam_processor | `ALERT_CACHE_TTL` | `5` | Alert dedup TTL (seconds) |

### Config Files

| File | Component | Key Settings |
|------|-----------|-------------|
| `ngfw-control/config.py` | Control API | Bind host/port, DB path, log dir, nftables parameters |
| `ensemble_config.json` | ML Service | Model weights, feature columns, thresholds, action policy |
| `/etc/suricata/suricata.yaml` | Suricata | AF_PACKET interfaces, EVE logging, file extraction, HTTP parser |
| `/etc/nftables.conf` | nftables | blocked_ips set, input/forward chains, NAT, rate limits |
| `web/config.py` | Test Website | Upload paths, ClamAV host/port, rate limits, logging |

## Running the System

All services are managed via systemd (on VM1) except the dashboard (npm) and the test website (Flask on VM2).

| Service | systemd Name | Port | Start Command |
|---------|--------------|------|--------------|
| Suricata IDS/IPS | `suricata.service` | — | `sudo systemctl start suricata` |
| NGFW Control API | `ngfw-control.service` | 5001 | `sudo systemctl start ngfw-control` |
| Alert Processor | `suri-clam.service` | — | `sudo systemctl start suri-clam` |
| ML Inference | `ngfw-ml.service` | 5003 | `sudo systemctl start ngfw-ml` |
| Flow Meter | `ngfw-flowmeter.service` | — | `sudo systemctl start ngfw-flowmeter` |
| ClamAV Daemon | `clamav-daemon.service` | 3310 | `sudo systemctl start clamav-daemon` |
| Admin Dashboard | (npm) | 3000 | `cd ngfw-dashboard && npm run dev` |

Start all services at once:

```bash
sudo systemctl start suricata ngfw-control suri-clam ngfw-ml ngfw-flowmeter clamav-daemon
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-dashboard && npm run dev
```

Run dashboard in production mode:

```bash
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-dashboard
npm run build
npm run preview
```

Run the test website (on VM2):

```bash
cd /home/ubuntuhero/ngfw-prototype/web
python app.py
```

## API Reference

### NGFW Control API (port 5001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health check (DB status, event counts, blocks) |
| GET | `/api/list_blocks` | List all blocked IPs with IDs, reasons, TTLs |
| POST | `/api/block_ip` | Block an IP (adds to nftables + DB). Body: `{ip, reason, ttl, signature}` |
| POST | `/api/unblock_ip` | Unblock an IP (removes from nftables + DB). Body: `{ip}` |
| POST | `/api/clear_all_blocks` | Flush all blocked IPs from nftables and DB |
| GET | `/api/logs` | Paginated detection logs. Params: `limit, offset, search` |
| POST | `/api/log_detection` | Log a detection event. Body: `{source, action, src_ip, dest_ip, ...}` |
| POST | `/api/logs/clear` | Clear all detection logs |
| GET | `/api/ml_predictions` | ML prediction history. Params: `limit` |
| POST | `/api/ml_predictions` | Store an ML prediction. Body: `{attack_type, confidence, model_scores, ...}` |
| POST | `/api/ml_predictions/clear` | Clear all ML predictions |
| POST | `/api/malware_alert` | Store a malware alert. Body: `{filename, file_hash, signature, source_ip, action}` |
| GET | `/api/malware_alerts` | Malware alert history. Params: `limit, search` |
| POST | `/api/malware_alerts/clear` | Clear all malware alerts |
| GET | `/api/system/stats` | CPU load, memory usage, uptime, event counts |
| GET | `/api/network/stats` | Interface statistics, packet/byte counts, connections |
| GET | `/api/firewall/rules` | nftables rule counts per chain (input/output/forward) |
| GET | `/api/services` | List all NGFW services with active/inactive status |
| POST | `/api/service` | Start/stop/restart/status a service. Body: `{service, action}` |
| GET | `/api/stream` | SSE real-time event stream (5-second poll for dashboard) |
| GET | `/api/export/logs` | Export logs (JSON or CSV). Params: `format, limit` |
| GET | `/api/export/ml_predictions` | Export ML predictions (JSON or CSV) |
| GET | `/api/export/malware_alerts` | Export malware alerts (JSON or CSV) |

### ML Inference Service (port 5003)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | ML service health (models loaded, feature count, threshold) |
| POST | `/predict` | Real-time ML prediction. Body: flow features from cicflowmeter |

### Quick Examples

```bash
# Block an IP
curl -X POST http://localhost:5001/api/block_ip \
  -H "Content-Type: application/json" \
  -d '{"ip":"192.168.1.100","reason":"SQLi","ttl":"1h"}'

# List blocked IPs
curl http://localhost:5001/api/list_blocks | python3 -m json.tool

# Unblock an IP
curl -X POST http://localhost:5001/api/unblock_ip \
  -H "Content-Type: application/json" \
  -d '{"ip":"192.168.1.100"}'

# Check health
curl http://localhost:5001/api/health | python3 -m json.tool

# ML health check
curl http://localhost:5003/health | python3 -m json.tool
```

### TTL Format

Block durations can be specified as:
- String with suffix: `"1h"`, `"6h"`, `"24h"`, `"7d"`, `"permanent"`
- Integer (seconds): `3600`
- Default (if omitted): `"1h"` (configurable via `NGFW_DEFAULT_TTL`)

For detailed API documentation, see `ngfw-control/docs/api_documentation.md`.

## Testing

The system includes multiple testing strategies:

### Attack Simulation (against VM2)

```bash
# SQL Injection
curl -X POST http://10.0.0.5/login -d "username=admin' OR '1'='1'--&password=test"

# XSS
curl -X POST http://10.0.0.5/feedback -d "name=Test&message=<script>alert('XSS')</script>"

# Command Injection
curl -X POST http://10.0.0.5/cmd -d '{"command":"whoami"}' -H "Content-Type: application/json"

# Path Traversal
curl http://10.0.0.5/file?path=../../etc/passwd

# XXE
curl -X POST http://10.0.0.5/api/xml \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>'
```

### Malware Upload Test

```bash
# Create EICAR test file (harmless malware signature test)
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.com

# Upload through the test website
curl -X POST -F "file=@/tmp/eicar.com" http://10.0.0.5/upload
```

### Verification

```bash
# Check blocked IPs
sudo nft list set inet firewall blocked_ips

# Monitor Suricata alerts in real time
sudo tail -f /var/log/suricata/fast.log

# View EVE events
sudo tail -f /var/log/suricata/eve.json | jq '.'

# Check ML predictions
sudo journalctl -u ngfw-ml -f | grep PREDICT

# View processor logs
sudo journalctl -u suri-clam -f

# Clear all blocks (testing convenience)
curl -X POST http://localhost:5001/api/clear_all_blocks

# Reload Suricata rules
sudo kill -USR2 $(pgrep suricata)
```

## Project Structure

```
ngfw-prototype/
├── ngfw-control/              # Flask Decision Engine API (port 5001)
│   ├── app.py                 # 23+ REST endpoints (blocking, logging, stats, export, SSE)
│   ├── config.py              # Environment-based configuration (8 key env vars)
│   ├── database.py            # SQLAlchemy models (Block, LogEvent, MLPrediction, alerts, backups)
│   ├── firewall_service.py    # nftables command wrapper (block/unblock/list/flush)
│   ├── suri_clam_processor.py # EVE log tailer + ClamAV scanner + alert handler (903 lines)
│   ├── logger.py              # Rotating file + console logger (app + security)
│   ├── requirements.txt       # Flask, SQLAlchemy, requests, conntrack, netifaces
│   └── docs/                  # API docs, Suricata config, nftables config, project overview
├── ngfw-ml/                   # ML Inference Service (port 5003)
│   ├── inference_service.py   # 5-model ensemble (RF+XGB+DT+LR+CatBoost) with StandardScaler
│   ├── cicflowmeter_bridge.py # Flow feature extraction on enp0s3, POST to /predict
│   ├── ensemble_config.json   # Model weights, feature columns, thresholds, CICIDS2017 eval
│   └── models/                # Pickle model files (model_rf.pkl, model_xgb.pkl, ...)
├── ngfw-dashboard/            # React Admin Dashboard (port 3000)
│   ├── src/
│   │   ├── components/        # 14 React components (Layout, DashboardHome, FirewallManagement...)
│   │   ├── services/api.ts    # REST API client (18+ functions)
│   │   ├── services/sse.ts    # SSE manager with auto-reconnect (max 5 attempts)
│   │   ├── contexts/          # AuthContext (login/password protected routes)
│   │   └── pages/             # Login page
│   ├── package.json           # React 19, Vite 6, Tailwind CSS v4, lucide-react
│   └── vite.config.ts         # Port 3000, path aliases (@, @components, etc.)
├── web/                       # Vulnerable Test Website (VM2, port 5000)
│   ├── app.py                 # Flask app with 8 vulnerable route blueprints
│   ├── config.py              # Dev/Prod/Test config classes
│   ├── models.py              # User, Feedback, UploadedFile, LogEvent models
│   ├── src/routes/            # auth_routes, upload_routes, command_routes, file_routes,
│   │                          # xss_routes, xml_routes, redirect_routes, misc_routes
│   ├── src/middleware/        # Rate limiter, request logger, security headers
│   ├── src/services/          # ClamAV scanner, database helpers
│   ├── src/templates/         # HTML templates
│   └── tests/                 # Automated attack test scripts
├── docs/                      # Project-level documentation
│   └── CUSTOM_RULES.md        # 125 custom Suricata rule descriptions
├── AGENTS.md                  # AI assistant instructions
├── LICENSE                    # MIT License
└── README.md                  # This file
```

## Technology Stack

### Infrastructure
- **Virtualization:** VirtualBox (2 VMs: Ubuntu Desktop + Ubuntu Server)
- **OS:** Ubuntu 22.04+ (kernel 6.14.0)
- **Network:** NAT network (ngfw-net, 10.0.0.0/24) + Bridged adapter

### Firewall
- **nftables v1.0.9** — Stateful packet filtering, dynamic IP blocking with TTL, NAT masquerading, port forwarding, SYN/UDP flood protection

### Deep Packet Inspection
- **Suricata 8.0.2** — AF_PACKET capture, EVE JSON logging, 34 event types, file extraction

### Antivirus
- **ClamAV** — clamd daemon with INSTREAM protocol, Unix socket + TCP fallback

### Backend
- **Python 3.12+** — Primary development language
- **Flask 3.0+** — Web framework for Control API and test website
- **SQLAlchemy 2.0+** — ORM for SQLite database
- **SQLite** — Embedded database (ngfw.db with 7 tables + 3 backup tables)

### Machine Learning
- **scikit-learn** — Random Forest, Decision Tree, Logistic Regression, StandardScaler
- **XGBoost** — Gradient boosting model
- **CatBoost** — Categorical boosting model
- **CICFlowMeter** — Network flow feature extraction (52 features, CICIDS2017-compatible)

### Frontend
- **React 19** — UI framework
- **TypeScript** — Type-safe JavaScript
- **Vite 6** — Build tool and dev server
- **Tailwind CSS v4** — Utility-first styling
- **lucide-react** — Icon library
- **react-router-dom v7** — Client-side routing

### Real-time
- **Server-Sent Events (SSE)** — Real-time dashboard updates (5-second poll cycle)

## Development

### Running in Development Mode

```bash
# Dashboard (hot-reload)
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-dashboard
npm run dev

# Control API (debug mode)
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-control
python app.py

# ML Service
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-ml
python inference_service.py

# Alert Processor (requires root for reading Suricata logs)
sudo python suri_clam_processor.py
```

### Adding New API Endpoints

1. Add the route function in `ngfw-control/app.py`
2. If the endpoint needs database access, add the query function in `ngfw-control/database.py`
3. Add corresponding TypeScript function in `ngfw-dashboard/src/services/api.ts`
4. Optionally add dashboard UI components in `ngfw-dashboard/src/components/`

### Adding New Dashboard Pages

1. Create a new component in `ngfw-dashboard/src/components/`
2. Add the route in `ngfw-dashboard/src/App.tsx`
3. Add a navigation link in the Layout component

### Building for Production

```bash
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-dashboard
npm run build     # Produces optimized build in dist/
npm run preview   # Preview production build locally
```

## License

MIT License. See [LICENSE](LICENSE) for full text.
