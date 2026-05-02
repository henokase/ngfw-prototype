# NGFW (Next-Generation Firewall) Project - Complete Overview

> **Author:** Cascade AI (Pair Programming Assistant)  
> **Last Updated:** May 1, 2026  
> **Project Type:** Academic Research / Senior Research Project  
> **Target Audience:** Academic institutions, government agencies, security researchers

---

## 🎯 What is This Project?

This is a **Next-Generation Firewall (NGFW) Prototype** that demonstrates modern network security concepts using open-source tools. The system acts as a **network gateway** that performs:

- **Deep Packet Inspection (DPI)** using Suricata
- **Stateful packet filtering** using nftables
- **Malware detection** using ClamAV
- **Automated threat response** via a REST API
- **Intentionally vulnerable test website** for validation

The project is designed for **academic/research purposes** and targets deployment in **government and academic institutions** for educational and testing scenarios.

---

## 🏗️ System Architecture & Topology

### Physical Layout (VirtualBox)

```
[Internet/Host] 
      ↕
[VM1 - NGFW Gateway] ← You are here (Ubuntu Desktop)
      ↕ enp0s8 (10.0.0.1/24)
      ↕
[VM2 - Test Website] (Ubuntu Server, 10.0.0.5)
```

### Network Interfaces (VM1)

| Interface | Name in Config | IP Address | CIDR | Role |
|-----------|----------------|------------|------|------|
| `enp0s3` | Bridged adapter | `192.168.1.3` (changes with WiFi) | `/24` | Faces host network / internet |
| `enp0s8` | Internal adapter | `10.0.0.1` | `/24` | Internal network (`ngfw-net`) |
| `lo` | Loopback | `127.0.0.1` | `/8` | Local communication |

### Protected Server (VM2)

| Property | Value |
|----------|-------|
| OS | Ubuntu Server |
| IP | `10.0.0.5` (connected via `enp0s8`) |
| Services | Flask web app (port 5001), nginx (port 80) |
| SSH Access | `ubuntuhero` / `ubuntuhero4433` |

---

## 🧩 What's Already Implemented

**Architecture Note:** VM1 handles all threat detection and IP blocking independently. VM2 does NOT communicate with VM1. All traffic is inspected by Suricata on VM1 before being forwarded to VM2, so VM1 sees real source IPs directly (no NAT correlation needed).

### 1. nftables Firewall (VM1)

**File:** `/etc/nftables.conf`

**Features:**
- **Stateful filtering** with `ct state established,related accept`
- **Default-deny policy** (input/forward chains)
- **Dynamic IP blocking** via `set blocked_ips` with TTL support (`flags timeout`)
- **NAT/Masquerading** for VM2 internet access
- **Port forwarding** (HTTP port 80 → VM2, SSH port 22 → VM2)

**Key Chains:**
```nftables
table inet firewall {
    set blocked_ips { ... }  # Dynamic block list with TTL
    
    chain input { ... }      # Controls traffic TO VM1
    chain forward { ... }  # Controls traffic BETWEEN VM1 ↔ VM2
}
table ip nat {
    chain prerouting { ... }  # Port forwarding rules
    chain postrouting { ... } # Masquerading
}
```

---

### 2. Suricata DPI (VM1)

**Config:** `/etc/suricata/suricata.yaml`  
**Rules:** `/var/lib/suricata/rules/custom-rules.rules`  
**Logs:** `/var/log/suricata/eve.json`, `/var/log/suricata/fast.log`  
**File Extraction:** `/var/log/suricata/filestore/`

**Features:**
- **Live capture** via `af-packet` on `enp0s3` and `enp0s8`
- **EVE JSON logging** for machine-readable events
- **File extraction** (filestore) for malware scanning
- **Custom rules** (13 rules, SID 1000010-1000061):
  - SQL Injection (5 rules)
  - XSS (4 rules)
  - Command Injection (3 rules)
  - Path Traversal (3 rules)
  - XXE (2 rules)
  - Open Redirect (2 rules)

**Key Config:**
```yaml
af-packet:
  - interface: enp0s3  # Bridged (host network)
  - interface: enp0s8  # Internal (VM2 network)
```

---

### 3. ClamAV Malware Scanning (VM1 + VM2)

**VM1 (Gateway):**
- **Daemon:** `clamd` (Unix socket: `/var/run/clamav/clamd.ctl`)
- **Scanner:** Called by `suri_clam_processor.py` for extracted files

**VM2 (Test Website):**
- **Local scanning:** Files uploaded to `/upload` are scanned before saving
- **Response:** Returns `"scan_result": "infected"` if malware detected

---

### 4. NGFW Control API (VM1)

**File:** `/opt/ngfw-control/app.py`  
**Port:** `5001` (binds to `0.0.0.0`)

**API Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/block_ip` | POST | Block an IP (called by processor) |
| `/api/unblock_ip` | POST | Remove an IP from block list |
| `/api/log_detection` | POST | Log a detection event |
| `/api/list_blocks` | GET | List currently blocked IPs |
| `/api/health` | GET | Health check |

**Database:** SQLite (`/opt/ngfw-control/ngfw.db`)  
**Tables:** `blocks`, `logs`

---

### 5. Suricata-ClamAV Processor (VM1)

**File:** `/opt/ngfw-control/suri_clam_processor.py`  
**Service:** `suri-clam` (systemd service)

**What it does:**
1. **Tails `/var/log/suricata/eve.json`** for new events
2. **Processes `alert` events:**
   - Checks severity/category via `severity_to_block_action()`
   - Whitelist check (dynamic + static)
   - Blocks IPs with severity ≤ 2 (High/Medium-High)
3. **Processes `fileinfo` events:**
   - Extracts file from `/var/log/suricata/filestore/`
   - Scans with ClamAV
   - **Blocks source IP** if malware detected (VM1 sees real IPs directly)
4. **Deduplication:** Avoids re-scanning/re-blocking same IP+rule within TTL

**Key Functions:**
```python
def process_alert_event(event)      # Handle Suricata alerts
def process_fileinfo_event(event)   # Handle file extraction + ClamAV
def severity_to_block_action()      # Decide block based on severity
def is_ip_whitelisted()          # Check static + dynamic whitelist
```

---

### 6. Test Website (VM2)

**Location:** `/home/ubuntuhero/ngfw-prototype/ngfw-control/`  
**Framework:** Flask (Python)  
**Web Server:** nginx (reverse proxy, port 80 → Flask port 5001)

**Vulnerable Endpoints (for testing):**
- `/login` - SQL Injection
- `/upload` - File upload with ClamAV scanning
- `/api/xml` - XXE injection
- `/api/redirect` - Open redirect

**Features:**
- Displays detection statistics
- Shows blocked IPs
- Generates intentional vulnerabilities for testing

---

## ⚠️ Current Issues (As of May 1, 2026)

### Issue #1: Malware Upload Blocking

**Symptom:** When you upload an EICAR test file, the file is detected as malware and the **uploader's IP is now blocked**.

**Architecture Note:** VM1 handles all threat detection independently. Suricata on VM1 sees the real source IP directly (no NAT correlation needed). The `fileinfo` event contains the correct `src_ip` of the attacker.

**What Was Fixed:**
- Removed unnecessary conntrack correlation code (VM1 sees real IPs directly)
- Simplified `process_fileinfo_event()` to use `src_ip` from Suricata event
- Malware detection now blocks the real source IP via `/api/block_ip`

**Current Status:** ✅ Working. VM1 blocks uploader's IP for 24h on malware detection.

---

### Issue #2: False Blocks from Legitimate Traffic

**Symptom:** Your host IP (192.168.1.9) was being blocked when:
- Visiting Notion.so (ET INFO rule SID 2038646)
- Uploading clean JSON files (triggered SQLi rules SID 1000010/1000013)

**Root Causes Fixed:**
1. **ET INFO rules** (signature starts with "ET INFO") now skipped via `severity_to_block_action()`
2. **`/upload` endpoint** now has a `pass` rule in Suricata to skip custom rule checks
3. **Clean file uploads** are now only scanned by ClamAV (no SQLi/XSS checks)

**Current Status:** ✅ Fixed.

---

### Issue #3: SSH to VM2 Not Working

**Symptom:** SSH connection to `10.0.0.5` was failing with `Permission denied`.

**Root Cause:** Missing `sshpass` package + incorrect assumption about credentials.

**What Was Fixed:**
- Installed `sshpass` on VM1
- Verified credentials: `ubuntuhero` / `ubuntuhero4433`
- Added SSH port 22 to nftables forward chain

**Current Status:** ✅ Working. Test with:
```bash
sshpass -p 'ubuntuhero4433' ssh -o StrictHostKeyChecking=no ubuntuhero@10.0.0.5
```

---

## 📂 Key Directories & Config Files

### Critical Paths (VM1 - Gateway)

| Purpose | Path |
|---------|------|
| **nftables config** | `/etc/nftables.conf` |
| **Suricata config** | `/etc/suricata/suricata.yaml` |
| **Suricata rules** | `/var/lib/suricata/rules/` |
| **Custom rules** | `/var/lib/suricata/rules/custom-rules.rules` |
| **Suricata logs** | `/var/log/suricata/eve.json`, `/var/log/suricata/fast.log` |
| **Filestore (extracted files)** | `/var/log/suricata/filestore/` |
| **ClamAV daemon socket** | `/var/run/clamav/clamd.ctl` |
| **NGFW Control API** | `/opt/ngfw-control/app.py` |
| **Processor script** | `/opt/ngfw-control/suri_clam_processor.py` |
| **Processor service** | `/etc/systemd/system/suri-clam.service` |
| **NGFW Database** | `/opt/ngfw-control/ngfw.db` |
| **Project docs** | `/home/heroubuntu/Desktop/ngfw-control/docs/` |

### Critical Paths (VM2 - Test Website)

| Purpose | Path |
|---------|------|
| **Flask app** | `/home/ubuntuhero/ngfw-prototype/ngfw-control/app.py` |
| **nginx config** | `/etc/nginx/sites-available/default` |
| **Upload directory** | `/var/www/html/uploads/` (or similar) |

---

## 🔧 Services & Commands

### Check Service Status

```bash
# VM1 (Gateway)
ps aux | grep -E "suricata|clamd|suri_clam|app.py" | grep -v grep

# Specific services
systemctl status suricata
systemctl status suri-clam
systemctl status ngfw-control
systemctl status clamav-daemon
```

### Restart Services

```bash
sudo systemctl restart suricata
sudo systemctl restart suri-clam
sudo systemctl restart ngfw-control
```

### Verify nftables Rules

```bash
sudo nft list table inet firewall
sudo nft list set inet firewall blocked_ips
```

### Test the System

```bash
# Test SQLi detection
curl -X POST http://10.0.0.5/login -d "username=admin' OR '1'='1'--&password=test"

# Test file upload (clean)
curl -X POST -F "file=@/tmp/clean.txt" http://10.0.0.5/upload

# Test file upload (malware - EICAR test)
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.com
curl -X POST -F "file=@/tmp/eicar.com" http://10.0.0.5/upload

# Check if IP is blocked
sudo nft list set inet firewall blocked_ips

# Monitor logs
sudo journalctl -u suri-clam -f
sudo tail -f /var/log/suricata/fast.log
```

---

## 📚 Documentation Files

| File | Description |
|------|-------------|
| `NGFW_PROJECT_OVERVIEW.md` (this file) | Complete project overview for newcomers |
| `nftables_configuration.md` | nftables setup and rules |
| `suricata_configuration.md` | Suricata setup and custom rules |
| `SYSTEM_ANALYSIS_FALSE_BLOCKS.md` | Analysis of false block issues |
| `ALL_4_FIXES_SUMMARY.md` | Summary of all fixes implemented |
| `FINAL_STATUS_ALL_FIXES_COMPLETE.md` | Final status after fixes |

---

## 🚀 Quick Start for New Developers

1. **Understand the topology:** VM1 is the gateway, VM2 is the test target
2. **Read the configs:** Start with `/etc/nftables.conf` and `/etc/suricata/suricata.yaml`
3. **Check running services:** `ps aux | grep -E "suricata|clamd|suri_clam|app.py"`
4. **Monitor the logs:** `sudo journalctl -u suri-clam -f`
5. **Test the system:** Upload EICAR test file, try SQLi attacks
6. **Check blocks:** `sudo nft list set inet firewall blocked_ips`

---

## 📊 Project History Summary

- **Phase 1-2:** Basic nftables + Suricata setup
- **Phase 3:** Custom rule creation (SQLi, XSS, etc.)
- **Phase 4 (Current):** Fix false blocks, improve malware detection
- **Phase 5 (Planned):** ML anomaly detection
- **Phase 6 (Planned):** Admin dashboard

---

**For more details, see the individual documentation files in `/home/heroubuntu/Desktop/ngfw-control/docs/`**
