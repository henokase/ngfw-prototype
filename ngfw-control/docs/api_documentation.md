# NGFW Control API Documentation

**Version:** 1.0 (As of May 2026)  
**Base URL:** `http://192.168.1.3:5001` (VM1 Gateway)  
**API Host:** VM1 (10.0.0.1 / 192.168.1.3)  
**Framework:** Flask (Python)

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration](#configuration)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
   - [POST /api/block_ip](#post-apiblock_ip)
   - [POST /api/unblock_ip](#post-apiunblock_ip)
   - [POST /api/log_detection](#post-apilog_detection)
   - [GET /api/list_blocks](#get-apilist_blocks)
   - [GET /api/health](#get-apihealth)
5. [Database Models](#database-models)
6. [Integration Points](#integration-points)
7. [Request/Response Examples](#requestresponse-examples)
8. [Logging](#logging)
9. [Error Handling](#error-handling)

---

## Overview

The NGFW Control API is the central decision engine running on VM1 (Gateway). It provides RESTful endpoints for:

- **IP Blocking/Unblocking** - Manage nftables firewall rules
- **Detection Logging** - Record security events from Suricata
- **Block Management** - View and manage currently blocked IPs

**Architecture Note:** VM1 handles all threat detection and IP blocking independently. VM2 does NOT communicate with VM1. All traffic is inspected by Suricata on VM1 before being forwarded to VM2, so VM1 sees real source IPs directly (no NAT correlation needed).

**Key Files:**
- API Server: `/opt/ngfw-control/app.py`
- Database Models: `/opt/ngfw-control/database.py`
- Firewall Service: `/opt/ngfw-control/firewall_service.py`
- Configuration: `/opt/ngfw-control/config.py`
- Logs: `/opt/ngfw-control/logs/ngfw-control.log`, `/opt/ngfw-control/logs/ngfw-security.log`

---

## Configuration

Configured via `/opt/ngfw-control/config.py` and environment variables:

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `NGFW_BIND_HOST` | `0.0.0.0` | IP to bind the Flask server |
| `NGFW_BIND_PORT` | `5001` | Port for the API server |
| `NGFW_DB_PATH` | `/opt/ngfw-control/ngfw.db` | SQLite database path |
| `NGFW_LOG_DIR` | `/opt/ngfw-control/logs` | Log directory |
| `NGFW_NFT_BIN` | `nft` | nftables binary path |
| `NGFW_NFT_TABLE` | `inet firewall` | nftables table name |
| `NGFW_NFT_BLOCK_SET` | `blocked_ips` | nftables set for blocked IPs |
| `NGFW_DEFAULT_TTL` | `1h` | Default block duration |
| `NGFW_API_KEY` | (none) | Optional API authentication key |
| `NGFW_SECRET_KEY` | `ngfw_control_dev_secret_change_me` | Flask secret key |
| `NGFW_LOG_LEVEL` | `INFO` | Logging level |

**Current Deployment:**
```bash
# VM1 API Server
Host: 192.168.1.3:5001 (bridged interface)
Internal: 10.0.0.1:5001 (NAT interface)
Process ID: 13290 (as of May 2026)
```

---

## Authentication

**Current Status:** No authentication required (API_KEY not set).

For production use, set `NGFW_API_KEY` environment variable and validate in endpoints:

```python
# Example middleware (not currently implemented)
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if config.API_KEY and request.headers.get('X-API-Key') != config.API_KEY:
            return jsonify({"success": False, "error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated_function
```

---

## API Endpoints

### POST /api/block_ip

Block an IP address by adding it to nftables `blocked_ips` set and logging to database.

**Request:**
```http
POST /api/block_ip
Content-Type: application/json

{
  "ip": "192.168.1.100",
  "reason": "malware:ClamAV-EICAR",
  "ttl": "24h",
  "signature": "ClamAV-EICAR-Test-Signature"
}
```

**Request Body Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ip` | string | ✅ Yes | IPv4/IPv6 address to block |
| `reason` | string | No | Reason for blocking (default: "unknown") |
| `ttl` | string/int | No | Block duration (e.g., "1h", "300s", or seconds as int) |
| `signature` | string | No | Suricata/ClamAV signature that triggered the block |

**TTL Format:**
- String with suffix: `"1h"`, `"30m"`, `"300s"`
- Integer (seconds): `3600`
- If omitted: uses `NGFW_DEFAULT_TTL` (default: `"1h"`)

**Response:**
```json
{
  "success": true,
  "blocked_ip": "192.168.1.100",
  "ttl": "24h",
  "db_id": 42
}
```

**Response Codes:**
- `200 OK` - IP successfully blocked
- `400 Bad Request` - Missing or invalid IP
- `500 Internal Server Error` - nftables command failed

**Side Effects:**
1. Adds IP to nftables `blocked_ips` set with timeout
2. Creates record in `blocks` database table
3. Logs event to `logs` database table
4. Writes security log entry (WARNING level)

---

### POST /api/unblock_ip

Remove an IP address from nftables `blocked_ips` set and delete from database.

**Request:**
```http
POST /api/unblock_ip
Content-Type: application/json

{
  "ip": "192.168.1.100"
}
```

**Request Body Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ip` | string | ✅ Yes | IPv4/IPv6 address to unblock |

**Response:**
```json
{
  "success": true,
  "unblocked_ip": "192.168.1.100",
  "rows_deleted": 1
}
```

**Response Codes:**
- `200 OK` - IP successfully unblocked
- `400 Bad Request` - Missing IP
- `500 Internal Server Error` - nftables command failed

**Side Effects:**
1. Removes IP from nftables `blocked_ips` set
2. Deletes all records for IP from `blocks` database table
3. Logs event to `logs` database table

---

### POST /api/log_detection

Log a detection event (Suricata alert, malware scan result, etc.) to the database.

**Request:**
```http
POST /api/log_detection
Content-Type: application/json

{
  "source": "suricata_processor",
  "event": "alert_sqli_detected",
  "data": {
    "src_ip": "192.168.1.9",
    "dest_ip": "10.0.0.5",
    "signature": "SQL Injection Attempt",
    "severity": 2
  }
}
```

**Request Body Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | No | Source of detection (default: "unknown") |
| `event` | string | No | Event type (default: "detection") |
| `data` | object | No | Additional event data (JSON-serializable) |

**Response:**
```json
{
  "success": true,
  "log_id": 123
}
```

**Response Codes:**
- `200 OK` - Detection logged successfully
- `500 Internal Server Error` - Database error

**Side Effects:**
1. Creates record in `logs` database table
2. Writes info-level log entry to security logger

---

### GET /api/list_blocks

List all currently blocked IP addresses (from database, not nftables).

**Request:**
```http
GET /api/list_blocks
```

**Response:**
```json
{
  "success": true,
  "blocks": [
    {
      "id": 42,
      "ip": "192.168.1.100",
      "reason": "malware:ClamAV-EICAR",
      "timestamp": "2026-05-01T10:30:00.123456",
      "ttl": 86400
    },
    {
      "id": 43,
      "ip": "10.0.0.50",
      "reason": "suricata_alert_SQLi_Attempt",
      "timestamp": "2026-05-01T11:15:00.789012",
      "ttl": 3600
    }
  ]
}
```

**Response Codes:**
- `200 OK` - Blocks retrieved successfully

**Note:** This returns database records, not live nftables state. To check nftables directly:
```bash
sudo nft list set inet firewall blocked_ips
```

---

### GET /api/health

Health check endpoint to verify API and database status.

**Request:**
```http
GET /api/health
```

**Response (Healthy):**
```json
{
  "status": "ok",
  "db": "ok"
}
```

**Response (Degraded):**
```json
{
  "status": "degraded",
  "db": "error"
}
```

**Response Codes:**
- `200 OK` - Always returns 200 (check `status` field for health)

**Health Check Logic:**
- Attempts to initialize database tables
- If successful: `status: "ok"`
- If failed: `status: "degraded"`, logs error

---

## Database Models

SQLite database located at `/opt/ngfw-control/ngfw.db`.

### Table: `blocks`

Stores currently blocked IP addresses.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `ip` | String(64) | Blocked IP address |
| `reason` | Text | Reason for blocking |
| `timestamp` | String(64) | ISO-8601 timestamp |
| `ttl` | Integer | TTL in seconds (nullable) |

### Table: `logs`

General event logging (detections, API actions, etc.).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `source` | String(64) | Event source (e.g., "api", "vm2", "suricata") |
| `event` | String(128) | Event type (e.g., "block_ip", "log_detection") |
| `data` | Text | JSON-serialized event data |
| `timestamp` | String(64) | ISO-8601 timestamp |

---

## Integration Points

### Suricata Processor → API (VM1 Only)

The `suri_clam_processor.py` on VM1 calls the API for:

**Logging Detections:**
```python
# In send_detection_to_api()
requests.post(
    f"{api_base_url}/api/log_detection",
    json={
        "source": "suricata_processor",
        "event": "alert_sqli_detected",
        "data": {
            "src_ip": "192.168.1.9",
            "signature": "SQL Injection Attempt",
            ...
        }
    },
    timeout=5
)
```

**Blocking IPs (Alert Events):**
```python
# In process_alert_event()
requests.post(
    f"{api_base_url}/api/block_ip",
    json={
        "ip": "192.168.1.9",
        "reason": "suricata_alert_SQLi_Attempt",
        "signature": "SQL Injection Attempt",
        "ttl": "1h"
    },
    timeout=5
)
```

**Blocking IPs (Malware Events):**
```python
# In process_fileinfo_event()
# VM1 sees real src_ip directly from Suricata (no NAT correlation needed)
requests.post(
    f"{api_base_url}/api/block_ip",
    json={
        "ip": "192.168.1.9",  # Real source IP from Suricata event
        "reason": "malware:ClamAV.EICAR",
        "signature": "ClamAV.EICAR.Test.File",
        "ttl": "24h"
    },
    timeout=5
)
```

### 2. nftables Integration

The API uses `firewall_service.py` to execute nftables commands:

**Block IP:**
```python
# Equivalent to: nft add element inet firewall blocked_ips { 192.168.1.100 timeout 1h }
subprocess.run(["nft", "add", "element", "inet firewall", "blocked_ips", "{ 192.168.1.100 timeout 1h }"])
```

**Unblock IP:**
```python
# Equivalent to: nft delete element inet firewall blocked_ips { 192.168.1.100 }
subprocess.run(["nft", "delete", "element", "inet firewall", "blocked_ips", "{ 192.168.1.100 }"])
```

---

## Request/Response Examples

### Example 1: Block an IP for SQL Injection

**Request:**
```bash
curl -X POST http://192.168.1.3:5001/api/block_ip \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.9",
    "reason": "suricata_alert_SQLi_Attempt",
    "ttl": "1h",
    "signature": "SQL Injection Attempt (SID 1000010)"
  }'
```

**Response:**
```json
{
  "success": true,
  "blocked_ip": "192.168.1.9",
  "ttl": "1h",
  "db_id": 42
}
```

**Verify:**
```bash
sudo nft list set inet firewall blocked_ips
# Output should include: 192.168.1.9 timeout 1h
```

---

### Example 2: List All Blocks

**Request:**
```bash
curl http://192.168.1.3:5001/api/list_blocks
```

**Response:**
```json
{
  "success": true,
  "blocks": [
    {
      "id": 42,
      "ip": "192.168.1.9",
      "reason": "suricata_alert_SQLi_Attempt",
      "timestamp": "2026-05-01T10:30:00.123456",
      "ttl": 3600
    },
    {
      "id": 43,
      "ip": "10.0.0.50",
      "reason": "malware:ClamAV.EICAR.Test.File",
      "timestamp": "2026-05-01T12:00:00.000000",
      "ttl": 86400
    }
  ]
}
```

---

### Example 3: Unblock an IP

**Request:**
```bash
curl -X POST http://192.168.1.3:5001/api/unblock_ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.9"}'
```

**Response:**
```json
{
  "success": true,
  "unblocked_ip": "192.168.1.9",
  "rows_deleted": 1
}
```

---

### Example 4: Health Check

**Request:**
```bash
curl http://192.168.1.3:5001/api/health
```

**Response (Healthy):**
```json
{
  "status": "ok",
  "db": "ok"
}
```

---

## Logging

### Application Log

**File:** `/opt/ngfw-control/logs/ngfw-control.log`  
**Level:** INFO (configurable via `NGFW_LOG_LEVEL`)  
**Format:** `[timestamp] LEVEL logger_name in module: message`

**Example Entries:**
```
[2026-05-01 10:30:00,123] INFO ngfw-control in app: NGFW control DB initialized
[2026-05-01 10:30:15,456] ERROR ngfw-control in app: Failed to add nftables block for 192.168.1.100: nft command failed
```

### Security Log

**File:** `/opt/ngfw-control/logs/ngfw-security.log`  
**Level:** INFO (configurable)  
**Format:** Same as application log

**Example Entries:**
```
[2026-05-01 10:30:15,789] WARNING ngfw-security in app: Blocked IP 192.168.1.9 via API
[2026-05-01 12:00:00,123] CRITICAL ngfw-security in app: Malware alert received from VM2
```

**Structured Data (extra fields):**
- `ip` - IP address involved
- `reason` - Reason for action
- `signature` - Suricata/ClamAV signature
- `malware_filename` - Name of malware file
- `malware_file_hash` - Hash of malware file

---

## Error Handling

### Common Error Responses

**400 Bad Request - Missing Required Field:**
```json
{
  "success": false,
  "error": "ip is required"
}
```

**400 Bad Request - Malware Alert Missing Fields:**
```json
{
  "success": false,
  "error": "missing required fields",
  "missing": ["event_type", "filename", "file_hash"]
}
```

**500 Internal Server Error - nftables Failure:**
```json
{
  "success": false,
  "error": "nft command failed: Error: Could not process rule: No such file or directory"
}
```

**500 Internal Server Error - Database Error:**
```json
{
  "success": false,
  "error": "Database connection failed"
}
```

### Error Logging

All errors are logged to:
- **Application Log** (`ngfw-control.log`) - ERROR level
- **Security Log** (`ngfw-security.log`) - WARNING/CRITICAL level for security-related errors

### nftables Error Handling

The `firewall_service.py` wraps nftables commands in try-except blocks:

```python
def _run_nft(args: List[str]) -> Tuple[bool, str]:
    try:
        completed = subprocess.run(
            [config.NFT_BIN] + args,
            check=False,
            capture_output=True,
            text=True,
        )
        success = completed.returncode == 0
        output = completed.stdout if success else completed.stderr
        if not success:
            app_logger.error(f"nft command failed: {' '.join(cmd)} :: {output}")
        return success, output.strip()
    except FileNotFoundError:
        app_logger.error("nft binary not found; firewall operations unavailable")
        return False, "nft not found"
```

---

## Quick Reference

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/block_ip` | POST | Block an IP address | No |
| `/api/unblock_ip` | POST | Unblock an IP address | No |
| `/api/log_detection` | POST | Log a detection event | No |
| `/api/list_blocks` | GET | List all blocked IPs | No |
| `/api/health` | GET | Health check | No |

**Base URL:** `http://192.168.1.3:5001` or `http://10.0.0.1:5001`

**Process Management:**
```bash
# Check API status
ps aux | grep "app.py" | grep -v grep

# View logs
sudo journalctl -u ngfw-api -f  # If running as service
tail -f /opt/ngfw-control/logs/ngfw-control.log  # Direct log file

# Restart (if using systemd)
sudo systemctl restart ngfw-api
```

---

**Documentation Version:** 1.0  
**Last Updated:** May 1, 2026  
**Maintainer:** NGFW Development Team
