# 🔄 Implementation Changes Summary

**Date:** November 10, 2025  
**Phase:** Post-Phase 4 Enhancements

---

## 📋 Overview

This document summarizes the critical changes made to the codebase to address:
1. **Rate Limiting Strategy** - Changed from IP-based to session/account-based with global flood protection
2. **IP Translation Issue** - Addressed NAT translation between VM1 and VM2
3. **Enhanced Logging** - Added new columns to LogEvent table for better tracking

---

## 1. Rate Limiting Changes

### ❌ Old Approach (IP-based)
- Tracked requests per IP address
- Problem: VM2 only sees VM1's IP (10.0.0.1) due to NAT
- All clients appeared as the same IP

### ✅ New Approach (Session/Account-based + Global)

**Three-tier rate limiting:**

1. **Session-based (Unauthenticated Users)**
   - Tracks requests per session ID
   - Session ID stored in Flask session
   - Limit: 100 requests/minute per session

2. **Account-based (Authenticated Users)**
   - Tracks requests per username
   - Username stored in Flask session after login
   - Limit: 100 requests/minute per account

3. **Global Fallback (Site-wide Flood Protection)**
   - Tracks total requests per second across all users
   - Prevents application crashes during DDoS
   - Limit: 50 requests/second site-wide

### Files Modified:
- `src/middleware/rate_limit.py` - Complete rewrite of RateLimiter class
- `config.py` - Added `GLOBAL_RATE_LIMIT_PER_SECOND` configuration

### Key Changes in rate_limit.py:
```python
# Old: IP-based tracking
self.request_log = defaultdict(list)  # {ip: [timestamps]}

# New: Identifier-based tracking
self.request_log = defaultdict(list)  # {identifier: [timestamps]}
self.global_requests = []  # Global request timestamps

# Identifier format:
# - "session:<uuid>" for unauthenticated users
# - "user:<username>" for authenticated users
# - "GLOBAL" for site-wide tracking
```

---

## 2. IP Translation Issue Resolution

### 🔴 Problem
VM2 cannot see the real client IP address because:
- VM1 performs NAT translation
- All requests to VM2 appear to come from VM1's internal IP (10.0.0.1)
- When malware is detected, VM2 doesn't know which real IP to block

### ✅ Solution

**Step 1: VM1 forwards real IP via HTTP headers**
```nginx
# VM1 nginx configuration
location / {
    proxy_pass http://10.0.0.5:5000;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
}
```

**Step 2: VM2 extracts real IP from headers**
- Already implemented in `src/services/utils.py`
- `extract_ip_address()` function checks X-Real-IP and X-Forwarded-For headers

**Step 3: VM2 sends real IP back to VM1 when malware detected**
```python
# In antivirus_service.py
if scan_result['status'] == 'infected':
    real_client_ip = extract_ip_address(request)
    requests.post(
        "http://10.0.0.1:5000/api/block_ip",
        json={
            "ip": real_client_ip,
            "reason": "malware_upload",
            "signature": signature_name,
            "filename": filename
        }
    )
```

**Step 4: VM1 blocks the real client IP**
```python
# VM1 API endpoint
@app.route('/api/block_ip', methods=['POST'])
def block_ip():
    ip = request.json['ip']
    # Validate not internal IP
    if ip not in ['10.0.0.1', '127.0.0.1']:
        os.system(f"sudo nft add element inet firewall blocked_ips {{ {ip} timeout 1h }}")
```

### IP Flow Diagram:
```
Client (192.168.1.100)
    ↓
VM1 (10.0.2.15) - adds X-Real-IP: 192.168.1.100
    ↓
VM2 (10.0.0.5) - extracts real IP, scans file
    ↓ (if infected)
VM2 → VM1 API: {"ip": "192.168.1.100", "reason": "malware"}
    ↓
VM1 blocks 192.168.1.100 in nftables
```

### Files Modified:
- `docs/file-scanning-process.md` - Added detailed IP translation section
- `src/services/antivirus_service.py` - Will be updated to send real IP to VM1

---

## 3. Enhanced Logging System

### New Columns Added to `log_events` Table:

| Column | Type | Purpose |
|--------|------|---------|
| `session_id` | String(255) | Session ID for unauthenticated users |
| `username` | String(100) | Username for authenticated users |
| `upload_result` | String(20) | File scan result: 'clean', 'infected', 'error', or None |
| `filename` | String(255) | Uploaded filename (if applicable) |
| `file_hash` | String(64) | SHA256 hash of uploaded file |
| `response_time` | Float | Response time in seconds |

### Benefits:
1. **Better User Tracking** - Can correlate requests by session or account
2. **Upload Monitoring** - Track which files were uploaded and their scan results
3. **Performance Analysis** - Response time tracking for optimization
4. **Security Analysis** - Link malware uploads to specific sessions/users

### Files Modified:
- `models.py` - Updated LogEvent model with new columns
- `src/services/database_service.py` - Updated `create_log_event()` function
- `src/middleware/request_logger.py` - Updated to capture new fields

### Usage Example:
```python
# Request logger automatically captures:
create_log_event(
    ip_address=ip_address,
    endpoint=endpoint,
    method=method,
    payload=payload,
    user_agent=user_agent,
    status_code=status_code,
    session_id=session.get('session_id'),  # NEW
    username=session.get('username'),      # NEW
    upload_result=g.get('upload_result'),  # NEW
    filename=g.get('upload_filename'),     # NEW
    file_hash=g.get('upload_file_hash'),   # NEW
    response_time=duration                 # NEW
)
```

---

## 4. Configuration Changes

### config.py Updates:

```python
# Old
RATE_LIMIT_PER_MINUTE = 100  # Per IP

# New
RATE_LIMIT_PER_MINUTE = 100  # Per session/account
GLOBAL_RATE_LIMIT_PER_SECOND = 50  # Site-wide flood protection
```

---

## 5. Database Migration Required

### ⚠️ IMPORTANT: Database Schema Changes

The `log_events` table has new columns. You need to either:

**Option 1: Drop and recreate database (for development)**
```bash
cd ~/ngfw-prototype/web
rm instance/database.db
python app.py  # Will recreate with new schema
```

**Option 2: Add columns manually (for production)**
```sql
ALTER TABLE log_events ADD COLUMN session_id VARCHAR(255);
ALTER TABLE log_events ADD COLUMN username VARCHAR(100);
ALTER TABLE log_events ADD COLUMN upload_result VARCHAR(20);
ALTER TABLE log_events ADD COLUMN filename VARCHAR(255);
ALTER TABLE log_events ADD COLUMN file_hash VARCHAR(64);
ALTER TABLE log_events ADD COLUMN response_time FLOAT;

CREATE INDEX idx_log_events_session_id ON log_events(session_id);
CREATE INDEX idx_log_events_username ON log_events(username);
CREATE INDEX idx_log_events_file_hash ON log_events(file_hash);
```

---

## 6. Testing Checklist

### Rate Limiting Tests:
- [ ] Test session-based rate limiting (unauthenticated)
- [ ] Test account-based rate limiting (authenticated)
- [ ] Test global rate limiting (flood simulation)
- [ ] Verify session ID is created automatically
- [ ] Verify rate limits reset after time window

### IP Tracking Tests:
- [ ] Verify X-Real-IP header is set by VM1 nginx
- [ ] Verify VM2 extracts correct client IP
- [ ] Test malware upload triggers VM1 API call
- [ ] Verify correct IP is blocked in VM1 nftables
- [ ] Test that VM1's own IP cannot be blocked

### Logging Tests:
- [ ] Verify session_id is logged for unauthenticated requests
- [ ] Verify username is logged after login
- [ ] Verify upload_result is logged for file uploads
- [ ] Verify file_hash is calculated and logged
- [ ] Verify response_time is calculated correctly

---

## 7. Next Steps

### Immediate Actions:
1. **Drop and recreate database** to apply schema changes
2. **Test rate limiting** with multiple sessions
3. **Configure VM1 nginx** to forward X-Real-IP header
4. **Implement VM1 API endpoint** for IP blocking
5. **Update antivirus_service.py** to call VM1 API

### Future Enhancements:
1. Add Redis for distributed rate limiting (multi-server)
2. Add persistent session storage (database-backed sessions)
3. Add rate limit bypass for whitelisted IPs
4. Add rate limit dashboard/monitoring
5. Add automatic rate limit adjustment based on load

---

## 8. Files Changed Summary

### Modified Files:
1. `models.py` - LogEvent model (6 new columns)
2. `src/services/database_service.py` - create_log_event() function
3. `src/middleware/request_logger.py` - Capture new fields
4. `src/middleware/rate_limit.py` - Complete rewrite for session/account-based limiting
5. `config.py` - Added GLOBAL_RATE_LIMIT_PER_SECOND
6. `docs/file-scanning-process.md` - Added IP translation section

### Files to Create/Update (Phase 5):
1. `src/routes/upload_routes.py` - Set g.upload_result, g.upload_filename, g.upload_file_hash
2. `src/routes/auth_routes.py` - Set session['username'] after login
3. VM1 API service - Create /api/block_ip endpoint

---

## 9. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Client Browser                        │
│              (192.168.1.100)                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                VM1 - NGFW (10.0.2.15)                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  nginx: Add X-Real-IP: 192.168.1.100             │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  nftables: Forward to VM2                        │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  API: /api/block_ip (blocks real IPs)           │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                VM2 - Web Server (10.0.0.5)              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Rate Limiter:                                    │  │
│  │  - Global: 50 req/sec                            │  │
│  │  - Session: 100 req/min                          │  │
│  │  - Account: 100 req/min                          │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Request Logger:                                  │  │
│  │  - Captures session_id/username                  │  │
│  │  - Logs upload results                           │  │
│  │  - Tracks response times                         │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Antivirus Service:                              │  │
│  │  - Scans uploaded files                          │  │
│  │  - Extracts real IP from X-Real-IP               │  │
│  │  - Notifies VM1 if malware detected              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Summary

These changes significantly improve the system's ability to:
1. **Track users accurately** despite NAT translation
2. **Prevent abuse** with multi-tier rate limiting
3. **Respond adaptively** by blocking real attacker IPs
4. **Analyze traffic** with enhanced logging

All changes maintain the intentionally vulnerable nature of the test website while adding robust defensive layers for NGFW testing.
