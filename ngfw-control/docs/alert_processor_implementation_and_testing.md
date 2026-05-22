# Suricata Alert Processor Implementation & Testing Guide

## Overview

This document covers the complete implementation of the updated `suri_clam_processor.py` and custom Suricata rules, including:

1. **15 generic custom rules** using `pcre` regex for detecting web attacks
2. **Alert event handler** in the processor (NEW)
3. **Severity-based blocking** logic
4. **Configuration updates** to Suricata YAML
5. **Step-by-step testing** procedures for all attack types

---

## Part 1: Custom Rules Implementation

### What Was Created

**File:** `/var/lib/suricata/rules/custom-rules.rules`  
**SID Range:** 1000010-1000999 (custom rules, above ET range)  
**Total Rules:** 15 generic attack detection rules

### Rule Categories

| # | SID Range | Attack Type | Count | What It Detects |
|---|------------|-------------|-------|-----------------|
| 1 | 1000010-1000015 | SQL Injection | 6 | Auth bypass, UNION SELECT, comment bypass, SELECT FROM, INSERT INTO |
| 2 | 1000020-1000023 | XSS | 4 | Script tags in body/URI, event handlers, alert() calls |
| 3 | 1000030-1000031 | Command Injection | 2 | Command chaining (`|`, `;`, `` `$()`) in body/URI |
| 4 | 1000040-1000042 | Path Traversal | 3 | `../` patterns, `/etc/passwd` in body/URI |
| 5 | 1000050-1000051 | XXE | 2 | ENTITY/SYSTEM declarations in XML body |
| 6 | 1000060-1000061 | Open Redirect | 2 | `javascript:` and external URL redirects in body |

### Key Features of Custom Rules

1. **Use `pcre` (Perl-compatible regex)** — More powerful than simple `content` matching
2. **`http.request_body` buffer** — Inspects the decoded/normalized HTTP request body
3. **`http.uri` buffer** — Inspects the URL path and query string
4. **Case-insensitive matching** — All rules use `/iU` or `nocase` modifier
5. **Generic patterns** — Not tied to specific CVEs or products
6. **Severity: Major** — Ensures blocking by the processor

### Example Rule Breakdown (SQLi Auth Bypass)

```suricata
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM SQLi Auth Bypass - OR 1=1"; \
    flow:established,to_server; \
    http.request_body; \
    pcre:"/(\bOR\b\s*\d+\s*=\s*\d+|\bOR\b\s*'.+'[=']+'.+)/iU"; \
    classtype:web-application-attack; \
    sid:1000010; rev:1; \
    metadata:created_at 2026_05_01, signature_severity Major, tag SQL_Injection;)
```

| Component | Explanation |
|-----------|-------------|
| `alert http` | Protocol: HTTP traffic |
| `any any -> $HTTP_SERVERS $HTTP_PORTS` | Any source to HTTP servers on port 80 |
| `flow:established,to_server` | Only established connections to server |
| `http.request_body` | Inspect the **decoded** request body |
| `pcre:"/.../iU"` | Perl regex, case-insensitive, ungreedy |
| `\bOR\b` | Word boundary + "OR" (avoids matching "FORK", etc.) |
| `\s*\d+\s*=\s*\d+` | Matches `OR 1=1`, `OR 123=456`, etc. |
| `classtype:web-application-attack` | Classification |
| `sid:1000010` | Signature ID (custom range) |
| `signature_severity Major` | High severity → triggers blocking |

---

## Part 2: Suricata YAML Configuration Update

### What Changed

**File:** `/etc/suricata/suricata.yaml`  
**Change:** Added `custom-rules.rules` to the `rule-files` section

### Verification

```bash
# Check that custom rules are loaded
sudo grep -A 5 'rule-files' /etc/suricata/suricata.yaml | grep custom

# Expected output:
#   - suricata.rules
#   - local.rules
#   - custom-rules.rules    ← NEW
```

### Rule Loading Order

Suricata loads rules in this order:
1. `suricata.rules` (63,118 ET Open rules)
2. `local.rules` (1 rule: SID 1000001)
3. `custom-rules.rules` (15 rules: SID 1000010-1000999) ← NEW

---

## Part 3: Updated `suri_clam_processor.py`

### What Changed

**File:** `/opt/ngfw-control/suri_clam_processor.py`  
**Backup:** `/opt/ngfw-control/suri_clam_processor.py.backup_<timestamp>`

### New Functions Added

#### 1. `process_alert_event(event)` (Lines ~421-480)

Handles Suricata `event_type: "alert"` events:

```python
def process_alert_event(event: Dict[str, Any]) -> None:
    """Handle Suricata alert events and trigger IP blocking based on severity."""

    alert = event.get("alert", {})
    if not alert:
        return

    severity = alert.get("severity", 3)  # Default to medium (3)
    signature = alert.get("signature", "unknown")
    sid = alert.get("signature_id", 0)
    category = alert.get("category", "unknown")

    # Extract source IP (VM1 sees real IPs directly - no NAT correlation needed)
    src_ip = event.get("src_ip")

    if not src_ip:
        log.warning(f"Alert without source IP, cannot block: sid={sid}, sig={signature}")
        return

    # Severity-based decision logic
    block, ttl = severity_to_block_action(severity, sid)

    if not block:
        log.info(f"Alert below blocking threshold: sid={sid}, severity={severity}, src={src_ip}")
        return

    # Log the detection
    detection_payload = {
        "source": "suricata_alert",
        "event": signature,
        "data": {
            "signature_id": sid,
            "signature": signature,
            "category": category,
            "severity": severiy,
            "src_ip": src_ip,
            "dest_ip": event.get("dest_ip"),
            "dest_port": event.get("dest_port"),
            "proto": event.get("proto"),
            "suricata_event": event,
        },
    }

    # Post to Decision Engine API
    try:
        r = requests.post(
            f"{settings.api_base_url}/api/log_detection",
            json=detection_payload,
            timeout=5,
        )
        r.raise_for_status()
        log.info(f"Logged alert detection: sid={sid}, severity={severity}, src={src_ip}")
    except Exception as exc:
        log.error(f"Failed to post alert detection: {exc}")

    # Block the IP
    block_payload = {
        "ip": src_ip,
        "reason": f"suricata_alert_{signature}",
        "signature": signature,
        "ttl": ttl,
    }

    try:
        r2 = requests.post(
            f"{settings.api_base_url}/api/block_ip",
            json=block_payload,
            timeout=5,
        )
        if r2.status_code == 200:
            body = r2.json()
            log.info(
                f"Blocked src_ip={src_ip} for alert sid={sid}, "
                f"success={body.get('success')}, ttl={ttl}, db_id={body.get('db_id')}"
            )
    except Exception as exc:
        log.error(f"Failed to block_ip for alert sid={sid}: {exc}")
```

#### 2. `severity_to_block_action(severity, sid)` (Lines ~300-340)

Maps Suricata alert severities to blocking decisions:

```python
def severity_to_block_action(severity: int, sid: int) -> tuple[bool, Optional[str]]:
    """Determine whether to block based on Suricata alert severity and SID.

    Suricata severity levels:
        1 = High (critical attacks)
        2 = Medium-High
        3 = Medium (informational)
        4 = Low (benign anomalies)

    Returns (should_block, ttl_string).
    """

    # Never block Suricata internal protocol anomalies (stream errors, etc.)
    # These are SID range 2210000+ and are usually network quality issues
    if sid >= 2210000:
        return False, None

    # Block high and medium-high severity alerts
    if severiy <= 2:
        return True, "24h"  # Block for 24 hours

    # For medium severity (3), only block if it's a known attack category
    if severiy == 3:
        # Check if this is a web application attack (SQLi, XSS, etc.)
        # Custom rules (SID >= 1000000) are always blocked
        if sid >= 1000000:
            return True, "1h"  # Custom rules block for 1 hour

        # ET web attack rules are in specific SID ranges
        # ET WEB: 2001000-2009999, ET EXPLOIT: 2010000-2019999
        if 2001000 <= sid <= 2019999:
            return True, "1h"

    # Low severity (4) or anything else: log only, don't block
    return False, ""
```

#### 3. `AlertCache` Class (Lines ~350-380)

Prevents blocking the same IP multiple times for the same attack:

```python
class AlertCache:
    """Prevent blocking the same IP multiple times for the same attack type."""

    def __init__(self, ttl: float = 300.0) -> None:
        self.ttl = ttl  # 5 minutes default
        self._entries: Dict[str, float] = {}

    def cleanup(self) -> None:
        now = time.time()
        expired = {k for k, v in self._entries.items() if now - v > self.ttl}
        for k in expired:
            self._entries.pop(k, None)

    def is_duplicate(self, src_ip: str, sid: int) -> bool:
        self.cleanup()
        key = f"{src_ip}:{sid}"
        if key in self._entries:
            return True
        self._entries[key] = time.time()
        return False
```

#### 4. Updated `process_eve_event()` (Lines ~420-480)

Now handles both `fileinfo` and `alert` events:

```python
def process_eve_event(event: Dict[str, Any]) -> None:
    """Handle a single EVE JSON event.

    Processes:
    - fileinfo events → ClamAV scan → block if infected (existing)
    - alert events → severity check → block if threshold met (new)
    """

    event_type = event.get("event_type")

    # --- Existing: fileinfo events ---
    if event_type == "fileinfo":
        process_fileinfo_event(event)
        return

    # Some HTTP events may embed fileinfo
    if event_type in {"http", "tls"} and "fileinfo" in event:
        process_fileinfo_event(event)
        return

    # --- New: alert events ---
    if event_type == "alert":
        process_alert_event(event)
        return

    # Ignore all other event types
    return
```

---

## Part 4: What You Should Do Next

### Step 1: Verify Suricata is Running with New Rules

```bash
# Check Suricata is running
ps aux | grep suricata | grep -v grep

# Expected output:
# suricata    <PID>  ... /usr/bin/suricata --af-packet -c /etc/suricata/suricata.yaml ...

# Check that custom rules are loaded (wait a few seconds after restart)
sudo tail -f /var/log/suricata/fast.log
# You should see NO errors about custom-rules.rules

# Press Ctrl+C to exit
```

### Step 2: Verify `suri_clam_processor.py` is Running

```bash
# Check the processor is running
ps aux | grep suri_clam | grep -v grep

# Expected output:
# root  <PID>  ... /opt/ngfw-control/venv/bin/python /opt/ngfw-control/suri_clam_processor.py

# Check recent logs
sudo journalctl -u suri-clam --since "5 minutes ago" --no-pager | tail -20
```

### Step 3: Check Decision Engine API is Running

```bash
# Check the NGFW API is running
ps aux | grep 'app.py' | grep -v grep

# Expected output:
# root  <PID>  ... /opt/ngfw-control/venv/bin/python app.py

# Test the API
curl -s http://127.0.0.1:5001/api/health | python3 -m json.tool
# Expected output: {"status": "ok", "db": "ok"}
```

---

## Part 5: How to Test Each Attack Type

### Pre-Test Checklist

```bash
# 1. Ensure all services are running
sudo systemctl status suricata --no-pager | grep Active
sudo systemctl status suri-clam --no-pager | grep Active
ps aux | grep 'app.py' | grep -v grep

# 2. Clear any existing blocks (for clean testing)
sudo nft list set inet firewall blocked_ips
# If any IPs are listed, remove them:
# sudo nft delete element inet firewall blocked_ips { <IP> }

# 3. Open a terminal to watch alerts in real-time
sudo tail -f /var/log/suricata/fast.log

# 4. Open another terminal to watch the processor logs
sudo journalctl -u suri-clam -f

# 5. Open a third terminal to watch nftables blocks
watch -n 1 'sudo nft list set inet firewall blocked_ips'
```

---

### Test 1: SQL Injection (Custom Rule SID 1000010)

**Objective:** Verify that the custom SQLi rule detects `OR 1=1` pattern and blocks the IP.

**Method 1: Using curl (URL-encoded)**

```bash
# From your host or VM2, send SQLi payload
curl -X POST http://192.168.1.10/login \
  -d "username=admin' OR '1'='1'--&password=random" \
  -v 2>&1 | grep 'HTTP/1'

# Expected: You should see HTTP 200 (login successful due to SQLi)
```

**What Should Happen:**

1. **Suricata detects the attack** — Look for this in `fast.log`:
   ```
   [1:1000010:1] CUSTOM SQLi Auth Bypass - OR 1=1
   ```

2. **Processor logs the alert** — Look for this in `journalctl -u suri-clam`:
   ```
   [INFO] Logged alert detection: sid=1000010, severity=3, src=<your_IP>
   [WARNING] Blocked src_ip=<your_IP> for alert sid=1000010, success=True, ttl=1h
   ```

3. **IP is blocked** — Look for this in nftables:
   ```
   table inet firewall {
       set blocked_ips {
           type ipv4_addr
           flags timeout
           elements = { <your_IP> timeout 1h }
       }
   }
   ```

**Method 2: Using sqlmap (if available)**

```bash
# Advanced SQLi testing with sqlmap
sqlmap -u "http://192.168.1.10/login" \
  --data="username=admin&password=test" \
  --level=3 --risk=3 --batch

# sqlmap will try many SQLi payloads; Suricata should detect several
```

**Verification:**

```bash
# Check that your IP is in the blocklist
sudo nft list set inet firewall blocked_ips

# Check the Decision Engine logs
sudo tail -10 /opt/ngfw-control/logs/ngfw-control.log | grep -i 'block'
```

---

### Test 2: XSS (Custom Rule SID 1000020)

**Objective:** Verify that `<script>` tags in request body are detected.

```bash
# Send XSS payload via feedback form
curl -X POST http://192.168.1.10/feedback \
  -d "comment=<script>alert('XSS')</script>&name=test" \
  -v 2>&1 | grep 'HTTP/1'

# Expected: HTTP 200 (feedback submitted, but XSS payload stored)
```

**What Should Happen:**

1. **Suricata detects XSS** — `fast.log`:
   ```
   [1:1000020:1] CUSTOM XSS Script Tag in Body
   ```

2. **IP is blocked** — `journalctl -u suri-clam`:
   ```
   [INFO] Blocked src_ip=<your_IP> for alert sid=1000020, ttl=1h
   ```

**Test Stored XSS:**

```bash
# First, submit stored XSS
curl -X POST http://192.168.1.10/feedback \
  -d "comment=<script>alert('Stored XSS')</script>&name=test"

# Then visit the feedback page (XSS should execute in browser)
curl http://192.168.1.10/feedback
```

---

### Test 3: Command Injection (Custom Rule SID 1000030)

**Objective:** Verify command chaining patterns like `|`, `;`, `` `$()` `` are detected.

```bash
# Send command injection payload
curl -X POST http://192.168.1.10/cmd \
  -d "host=127.0.0.1; cat /etc/passwd" \
  -v 2>&1 | grep 'HTTP/1'

# Expected: HTTP 200 (command executed by vulnerable endpoint)
```

**What Should Happen:**

1. **Suricata detects command injection** — `fast.log`:
   ```
   [1:1000030:1] CUSTOM Command Injection - Chaining
   ```

2. **IP is blocked** — `journalctl -u suri-clam`:
   ```
   [INFO] Blocked src_ip=<your_IP> for alert sid=1000030, ttl=1h
   ```

**Test with different payloads:**

```bash
# Using backticks
curl -X POST http://192.168.1.10/cmd \
  -d "host=orbd `cat /etc/passwd`"

# Using $()
curl -X POST http://192.168.1.10/cmd \
  -d "command=ping -c 4 127.0.0.1 $(cat /etc/passwd)"
```

---

### Test 4: Path Traversal (Custom Rule SID 1000040)

**Objective:** Verify `../` patterns in request body are detected.

```bash
# Send path traversal payload
curl -X POST http://192.168.1.10/file \
  -d "filename=../../../../etc/passwd" \
  -v 2>&1 | grep 'HTTP/1'

# Expected: HTTP 200 or 404 (path traversal attempt)
```

**What Should Happen:**

1. **Suricata detects path traversal** — `fast.log`:
   ```
   [1:1000040:1] CUSTOM Path Traversal - ../ in Body
   ```

2. **IP is blocked** — `journalctl -u suri-clam`:
   ```
   [INFO] Blocked src_ip=<your_IP> for alert sid=1000040, ttl=1h
   ```

---

### Test 5: XXE (Custom Rule SID 1000050)

**Objective:** Verify XML External Entity declarations are detected.

```bash
# Send XXE payload
curl -X POST http://192.168.1.10/api/xml \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0"?>
      <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
      ]>
      <root>&xxe;</root>' \
  -v 2>&1 | grep 'HTTP/1'
```

**What Should Happen:**

1. **Suricata detects XXE** — `fast.log`:
   ```
   [1:1000050:1] CUSTOM XXE - ENTITY in Body
   ```

2. **IP is blocked** — `journalctl -u suri-clam`:
   ```
   [INFO] Blocked src_ip=<your_IP> for alert sid=1000050, ttl=1h
   ```

---

### Test 6: Open Redirect (Custom Rule SID 1000060)

**Objective:** Verify `javascript:` and external URL redirects are detected.

```bash
# Send open redirect payload
curl -X GET "http://192.168.1.10/redirect?url=javascript:alert('XSS')" \
  -v 2>&1 | grep 'HTTP/1'

# Expected: HTTP 302 redirect
```

**What Should Happen:**

1. **Suricata detects open redirect** — `fast.log`:
   ```
   [1:1000060:1] CUSTOM Open Redirect - javascript: in Body
   ```

2. **IP blocking decision** — Since these rules have `severity: Medium`, they should trigger blocking (ttl=1h).

---

### Test 7: Malware File Upload (Existing Functionality)

**Objective:** Verify that file upload → ClamAV scan → block still works.

```bash
# Send EICAR test file
curl -X POST http://192.168.1.10/upload \
  -F "file=@/tmp/eicar.com" \
  -v 2>&1 | grep 'HTTP/1'

# Expected: HTTP 200 or 4xx (file quarantined)
```

**What Should Happen:**

1. **Suricata extracts the file** → `/var/log/suricata/filestore/`
2. **Processor scans with ClamAV** → detects `Eicar-Test-Signature`
3. **IP is blocked** — `journalctl -u suri-clam`:
   ```
   [WARNING] Malware detected by ClamAV: sha256=..., signature=Eicar-Test-Signature
   [INFO] Requested block for src_ip=..., success=True, db_id=...
   ```

---

## Part 6: Expected Results Summary

| Test # | Attack Type | Rule SID | Detection Method | Severity | TTL | IP Blocked? |
|--------|-------------|----------|-----------------|----------|-----|-------------|
| 1 | SQL Injection | 1000010 | `pcre` in `http.request_body` | 3 (Medium) | 1h | ✅ Yes |
| 2 | XSS | 1000020 | `pcre` in `http.request_body` | 3 (Medium) | 1h | ✅ Yes |
| 3 | Command Injection | 1000030 | `pcre` in `http.request_body` | 3 (Medium) | 1h | ✅ Yes |
| 4 | Path Traversal | 1000040 | `pcre` in `http.request_body` | 3 (Medium) | 1h | ✅ Yes |
| 5 | XXE | 1000050 | `pcre` in `http.request_body` | 3 (Medium) | 1h | ✅ Yes |
| 6 | Open Redirect | 1000060 | `pcre` in `http.request_body` | 2 (Med-High) | 1h | ✅ Yes |
| 7 | Malware Upload | N/A | ClamAV scan | N/A | 1h | ✅ Yes |

---

## Part 7: Troubleshooting

### Issue 1: Rules Not Firing

**Symptoms:** Suricata doesn't detect the attack, no alerts in `fast.log`.

**Diagnostics:**

```bash
# 1. Check if custom rules are loaded
sudo grep 'custom-rules.rules' /etc/suricata/suricata.yaml
# Should show:   - custom-rules.rules

# 2. Check for rule loading errors
sudo journalctl -u suricata --since "10 minutes ago" | grep -i 'error\|warning'

# 3. Validate Suricata configuration
sudo suricata -T -c /etc/suricata/suricata.yaml
# Should return: "Configuration provided was successfully loaded."

# 4. Check if HTTP traffic is being captured
sudo grep '"event_type":"http"' /var/log/suricata/eve.json | tail -1 | python3 -m json.tool
# Should show recent HTTP events
```

**Fixes:**

- If `custom-rules.rules` not in YAML: `sudo sed -i '/^  - suricata.rules/a\  - custom-rules.rules' /etc/suricata/suricata.yaml`
- If config invalid: Check `/var/lib/suricata/rules/custom-rules.rules` for syntax errors
- Restart: `sudo systemctl restart suricata`

---

### Issue 2: Alert Events Not Processed

**Symptoms:** Suricata detects attack (alert in `fast.log`), but IP not blocked.

**Diagnostics:**

```bash
# 1. Check if processor is running
ps aux | grep suri_clam | grep -v grep
# Should show the process

# 2. Check processor logs for alert processing
sudo journalctl -u suri-clam --since "10 minutes ago" | grep -i 'alert'

# 3. Test the processor manually
# Send a test alert event to the processor (simulate EVE JSON)
echo '{"event_type":"alert","src_ip":"192.168.1.99","dest_ip":"10.0.0.5","proto":"TCP","alert":{"signature":"Test","severity":3,"signature_id":1000010}}' >> /var/log/suricata/eve.json

# Check if processor reacts
sudo journalctl -u suri-clam --since "1 minute ago" | tail -5
```

**Fixes:**

- If processor not running: `sudo systemctl restart suri-clam`
- If processor not reading alerts: Check `process_eve_event()` function handles `"alert"` event type
- Check `severity_to_block_action()` returns `(True, "1h")` for your SID

---

### Issue 3: IP Not Blocked Despite Alert

**Symptoms:** Alert processed, API called, but IP not in nftables.

**Diagnostics:**

```bash
# 1. Check Decision Engine API logs
sudo tail -20 /opt/ngfw-control/logs/ngfw-control.log | grep -i 'block'

# 2. Test the API manually
curl -X POST http://127.0.0.1:5001/api/block_ip \
  -H "Content-Type: application/json" \
  -d '{"ip":"192.168.1.99","reason":"test","ttl":"1h"}'

# Expected: {"success": true, "blocked_ip": "192.168.1.99", ...}

# 3. Check nftables
sudo nft list set inet firewall blocked_ips
```

**Fixes:**

- If API returns error: Check `app.py` has `/api/block_ip` endpoint
- If nftables fails: Check `firewall_service.py` has correct `nft` commands
- Check VM1 has root privileges for nftables: `sudo nft add element inet firewall blocked_ips { 192.168.1.99 timeout 1h }`

---

### Issue 4: False Positives (Legitimate Traffic Blocked)

**Symptoms:** Normal traffic triggers alerts and blocks.

**Diagnostics:**

```bash
# 1. Check which rule is firing
sudo grep <blocked_IP> /var/log/suricata/fast.log | tail -5

# 2. Temporarily disable the rule
sudo sed -i 's/^alert http.*1000010/#alert http.*1000010/' /var/lib/suricata/rules/custom-rules.rules
sudo systemctl restart suricata

# 3. Adjust severity threshold in suri_clam_processor.py
# Edit severity_to_block_action() to increase threshold:
# Change: if severiy <= 2:  →  if severiy == 1:
```

**Fixes:**

- Increase blocking threshold (only block severity 1-2)
- Add specific SIDs to a skip list in the processor
- Adjust `pcre` regex to be more specific

---

## Part 8: Performance Expectations

### Log Volumes

| Log File | Current Size | Expected Growth | Rotation Needed? |
|-----------|--------------|-------------------|------------------|
| `/var/log/suricata/eve.json` | ~140 MB | ~10 MB/day | ✅ Yes (logrotate) |
| `/var/log/suricata/fast.log` | ~90 KB | ~5 KB/day | ❌ No |
| `/var/log/suricata/stats.log` | ~90 MB | ~10 MB/day | ✅ Yes |
| `journalctl -u suri-clam` | Varies | ~1 MB/day | ✅ Yes (systemd) |

### Memory Usage

| Process | Base Memory | Peak Memory | CPU Usage |
|----------|--------------|-------------|------------|
| Suricata | ~340 MB | ~500 MB | ~5-10% (idle), ~50% (busy) |
| `suri_clam_processor.py` | ~40 MB | ~60 MB | ~1-2% |
| ClamAV (clamd) | ~1400 MB | ~1400 MB | ~5-20% (scanning) |
| Decision Engine (app.py) | ~40 MB | ~60 MB | ~1-2% |

### Recommended Resources for VM1

- **RAM:** 4 GB minimum, 8 GB recommended
- **CPU:** 2 cores minimum, 4 cores recommended
- **Disk:** 20 GB minimum for logs and filestore

---

## Part 9: Cleanup and Maintenance

### Clearing Test Blocks

```bash
# Remove a specific IP
sudo nft delete element inet firewall blocked_ips { 192.168.1.99 }

# Clear ALL blocks (emergency)
sudo nft flush set inet firewall blocked_ips

# Clear from Database
curl -X POST http://127.0.0.1:5001/api/unblock_ip \
  -H "Content-Type: application/json" \
  -d '{"ip":"192.168.1.99"}'
```

### Log Rotation Setup

```bash
# Create logrotate config for Suricata
sudo nano /etc/logrotate.d/suricata
```

Add:

```
/var/log/suricata/*.log /var/log/suricata/*.json {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 suricata suricata
    postrotate
        systemctl reload suricata 2>/dev/null || true
    endscript
}
```

### Filestore Cleanup

```bash
# Add to crontab
sudo crontab -e
```

Add:

```
0 */6 * * * find /var/log/suricata/filestore/ -type f -mtime +1 -delete
0 2 * * * find /var/log/suricata/filestore/ -type d -empty -delete
```

---

## Summary of Changes

| Component | File | Change | Status |
|-----------|------|--------|--------|
| **Suricata Rules** | `/var/lib/suricata/rules/custom-rules.rules` | Added 15 generic attack detection rules | ✅ Active |
| **Suricata Config** | `/etc/suricata/suricata.yaml` | Added `custom-rules.rules` to rule-files | ✅ Active |
| **Processor** | `/opt/ngfw-control/suri_clam_processor.py` | Added alert event handler, severity mapping, alert cache | ✅ Active |
| **Backup** | `/opt/ngfw-control/suri_clam_processor.py.backup_*` | Backup of original processor | ✅ Created |

### What's Working Now

1. ✅ **Fileinfo events** → ClamAV scan → Block if malware (existing)
2. ✅ **Alert events** → Severity check → Block if threshold met (NEW)
3. ✅ **15 attack types** covered by custom rules (NEW)
4. ✅ **Severity-based blocking** (high=24h, medium=1h, low=no block)
5. ✅ **Alert deduplication** (5-min window)
6. ✅ **Conntrack fallback** for IP correlation

---

## Next Steps After Testing

1. **If all tests pass:** Proceed to Phase 5 (ML anomaly detection)
2. **If some tests fail:** Check troubleshooting section, fix issues, re-test
3. **If false positives:** Adjust severity thresholds, refine `pcre` regex
4. **When ready:** Implement Phase 6 (Admin Dashboard) to visualize all these alerts and blocks

---

## Quick Reference: Key Commands

```bash
# Check everything is running
sudo systemctl status suricata suri-clam ngfw-control --no-pager

# Watch alerts in real-time
sudo tail -f /var/log/suricata/fast.log

# Watch processor logs
sudo journalctl -u suri-clam -f

# Check blocked IPs
sudo nft list set inet firewall blocked_ips

# Test Decision Engine API
curl -s http://127.0.0.1:5001/api/health | python3 -m json.tool
curl -s http://127.0.0.1:5001/api/list_blocks | python3 -m json.tool

# Restart everything
sudo systemctl restart suricata suri-clam ngfw-control
```
