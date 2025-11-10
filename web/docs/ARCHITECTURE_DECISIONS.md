# 🏗️ Critical Architecture Decisions

**Date:** November 10, 2025  
**Project:** Adaptive NGFW Test Website (VM2)

---

## 🔴 CRITICAL: VM1/VM2 IP Handling Architecture

### The Fundamental Rule

**VM2 must NEVER receive, extract, or be aware of real external client IP addresses.**

### Why This Architecture?

1. **VM1 is the Firewall Gateway**
   - VM1 has full visibility of real source IPs
   - VM1 handles NAT translation
   - VM1 maintains conntrack table with IP mappings
   - VM1 performs all IP-based blocking in nftables

2. **VM2 is Behind NAT**
   - All traffic to VM2 is DNATed through VM1
   - VM2 only sees VM1's internal IP (10.0.0.1) as the source
   - VM2 cannot distinguish between different external clients
   - VM2 has no direct access to real client IPs

3. **Security Separation**
   - Clear separation of concerns
   - VM1 = Network layer security
   - VM2 = Application layer security
   - Prevents VM2 from being a single point of failure

### What This Means for Implementation

#### ❌ WRONG Approach (Do NOT Do This):
```python
# VM2 trying to extract real IP from headers
ip_address = request.headers.get('X-Real-IP')  # WRONG!
ip_address = request.headers.get('X-Forwarded-For')  # WRONG!
ip_address = extract_ip_address(request)  # WRONG!

# VM2 trying to send IP to VM1
requests.post('http://10.0.0.1:5001/api/block_ip', 
              json={'ip': client_ip})  # WRONG!
```

#### ✅ CORRECT Approach:
```python
# VM2 only logs VM1's IP
ip_address = request.remote_addr or '10.0.0.1'  # CORRECT!

# VM2 sends event data WITHOUT IP
requests.post('http://10.0.0.1:5001/api/malware_alert',
              json={
                  'filename': filename,
                  'file_hash': file_hash,
                  'signature': signature,
                  'timestamp': timestamp
                  # NO IP ADDRESS!
              })  # CORRECT!
```

---

## 🔄 Communication Flow

### One-Directional Communication: VM2 → VM1

```
┌─────────────────────────────────────────────────────────┐
│  External Client (192.168.1.100)                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  VM1 - Firewall Gateway (10.0.2.15 / 10.0.0.1)         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  • Sees real IP: 192.168.1.100                   │  │
│  │  • Maintains conntrack table                     │  │
│  │  • Performs DNAT to VM2                          │  │
│  │  • Blocks IPs in nftables                        │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ DNAT (source becomes 10.0.0.1)
                     ↓
┌─────────────────────────────────────────────────────────┐
│  VM2 - Web Application (10.0.0.5)                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  • Sees only VM1's IP: 10.0.0.1                  │  │
│  │  • Scans files with ClamAV                       │  │
│  │  • Logs events to database                       │  │
│  │  • Sends alerts to VM1 (NO IP)                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
                     ↓ (if malware detected)
              Alert to VM1 API
              {filename, hash, signature}
                     ↓
┌─────────────────────────────────────────────────────────┐
│  VM1 - Firewall Control API (10.0.0.1:5001)            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  1. Receive alert from VM2                       │  │
│  │  2. Correlate with conntrack                     │  │
│  │  3. Find real IP: 192.168.1.100                  │  │
│  │  4. Block in nftables                            │  │
│  │  5. Return confirmation to VM2                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Rate Limiting Architecture

### Why Session/Account-Based Instead of IP-Based?

**Problem with IP-Based Rate Limiting:**
- VM2 only sees VM1's IP (10.0.0.1)
- All clients appear as the same IP
- Cannot distinguish between different users
- Would rate limit ALL traffic together

**Solution: Three-Tier Rate Limiting**

### Tier 1: Session-Based (Unauthenticated Users)
```python
# Auto-generate session ID if not exists
if 'session_id' not in session:
    session['session_id'] = str(uuid.uuid4())

identifier = f"session:{session['session_id']}"
# Limit: 100 requests/minute per session
```

### Tier 2: Account-Based (Authenticated Users)
```python
# After successful login
session['username'] = 'john_doe'

identifier = f"user:{session['username']}"
# Limit: 100 requests/minute per account
```

### Tier 3: Global Flood Protection
```python
# Check global rate limit first
global_allowed = limiter.is_allowed('GLOBAL', is_global_check=True)
# Limit: 50 requests/second site-wide
# Prevents application crashes during DDoS
```

### Rate Limiting Flow:
```
Request arrives
    ↓
Check global limit (50 req/sec)
    ↓ (if allowed)
Check if authenticated
    ├─ Yes → Check account limit (100 req/min)
    └─ No  → Check session limit (100 req/min)
    ↓
Allow or deny request
```

---

## 🗄️ Enhanced Database Logging

### LogEvent Table Schema

```sql
CREATE TABLE log_events (
    id INTEGER PRIMARY KEY,
    ip_address VARCHAR(45),          -- Always '10.0.0.1' (VM1's IP)
    endpoint VARCHAR(255),
    method VARCHAR(10),
    payload TEXT,
    user_agent VARCHAR(512),
    status_code INTEGER,
    timestamp DATETIME,
    
    -- NEW COLUMNS:
    session_id VARCHAR(255),         -- Session tracking
    username VARCHAR(100),           -- Account tracking
    upload_result VARCHAR(20),       -- 'clean', 'infected', 'error'
    filename VARCHAR(255),           -- Uploaded file name
    file_hash VARCHAR(64),           -- SHA256 hash
    response_time FLOAT              -- Response time in seconds
);

CREATE INDEX idx_log_events_session_id ON log_events(session_id);
CREATE INDEX idx_log_events_username ON log_events(username);
CREATE INDEX idx_log_events_file_hash ON log_events(file_hash);
```

### Why These Columns?

1. **session_id / username**
   - Track user behavior across requests
   - Correlate attacks to specific sessions/accounts
   - Support session-based rate limiting

2. **upload_result / filename / file_hash**
   - Track which files were uploaded
   - Link malware detections to sessions
   - Provide audit trail for security incidents

3. **response_time**
   - Identify slow endpoints
   - Detect potential DoS attacks
   - Performance optimization

---

## 🦠 Malware Detection Workflow

### Step-by-Step Process

**1. File Upload (VM2)**
```python
# User uploads file
file = request.files['file']
filepath = save_temp_file(file)
```

**2. ClamAV Scan (VM2)**
```python
# Scan with ClamAV
result = scan_file(filepath)

if result['status'] == 'infected':
    # Move to quarantine
    move_to_quarantine(filepath)
```

**3. Alert VM1 (VM2 → VM1)**
```python
# Calculate file hash
file_hash = hashlib.sha256(open(filepath, 'rb').read()).hexdigest()

# Send alert to VM1 (NO IP ADDRESS)
alert_payload = {
    'event_type': 'malware_detected',
    'filename': filename,
    'timestamp': datetime.utcnow().isoformat(),
    'result': 'infected',
    'file_hash': file_hash,
    'signature': result['signature'],
    'vm2_source': 'web_upload_scanner'
}

response = requests.post(
    'http://10.0.0.1:5001/api/malware_alert',
    json=alert_payload,
    timeout=5
)
```

**4. Correlate and Block (VM1)**
```python
# VM1 receives alert
@app.route('/api/malware_alert', methods=['POST'])
def malware_alert():
    data = request.json
    
    # Correlate with conntrack to find real client IP
    client_ip = correlate_conntrack_to_vm2_connection()
    
    # Block real IP in nftables
    if client_ip and client_ip not in ['10.0.0.1', '127.0.0.1']:
        os.system(f"sudo nft add element inet firewall blocked_ips {{ {client_ip} timeout 1h }}")
        
        # Return confirmation
        return jsonify({
            'status': 'blocked',
            'blocked_ip': client_ip,
            'reason': 'malware_upload',
            'signature': data['signature'],
            'timestamp': datetime.utcnow().isoformat()
        })
```

**5. Log Confirmation (VM2)**
```python
# VM2 logs VM1's response (audit only)
if response.status_code == 200:
    vm1_response = response.json()
    logger.info(f"VM1 blocked IP: {vm1_response['blocked_ip']}")
    
    # Store in database for audit
    create_log_event(
        ip_address='10.0.0.1',  # VM2 only sees VM1's IP
        endpoint='/upload',
        method='POST',
        upload_result='infected',
        filename=filename,
        file_hash=file_hash,
        payload=f"Malware: {signature}. VM1 blocked attacker."
    )
```

---

## 🔧 Configuration Summary

### config.py Settings

```python
# Middleware Configuration
ENABLE_RATE_LIMIT = True
RATE_LIMIT_PER_MINUTE = 100              # Per session/account
GLOBAL_RATE_LIMIT_PER_SECOND = 50        # Site-wide flood protection
ENABLE_SECURITY_HEADERS = True
ENABLE_REQUEST_LOGGING = True

# VM1 API Configuration
VM1_API_URL = 'http://10.0.0.1:5001/api/malware_alert'
VM1_API_TIMEOUT = 5  # seconds
```

---

## ✅ Implementation Checklist

### VM2 Code Review Checklist:
- [ ] No calls to `extract_ip_address(request)`
- [ ] No reading of `X-Real-IP` or `X-Forwarded-For` headers
- [ ] All IP logging uses `request.remote_addr` (will be 10.0.0.1)
- [ ] Malware alerts sent to VM1 without IP address
- [ ] Rate limiting uses session_id or username (not IP)
- [ ] Database logs session_id and username
- [ ] Upload results logged with file_hash

### VM1 Requirements:
- [ ] Firewall Control API at `http://10.0.0.1:5001/api/malware_alert`
- [ ] Conntrack correlation function implemented
- [ ] nftables blocked_ips set configured
- [ ] API validates IPs before blocking (no internal IPs)
- [ ] API returns confirmation with blocked_ip

---

## 📚 Key Takeaways

1. **VM2 is IP-blind** - It only sees VM1's IP and doesn't need real IPs
2. **VM1 is IP-aware** - It handles all real IP tracking and blocking
3. **Communication is one-way** - VM2 sends alerts to VM1, not vice versa
4. **Rate limiting is user-based** - Session/account tracking, not IP-based
5. **Logging is comprehensive** - Session, account, uploads, and performance tracked
6. **Malware workflow is clean** - VM2 detects, VM1 blocks, VM2 logs confirmation

---

## 🚀 Benefits of This Architecture

1. **Clear Separation of Concerns**
   - Network security (VM1) vs Application security (VM2)
   
2. **Resilient to NAT**
   - Works correctly despite IP translation
   
3. **Scalable**
   - Can add more VM2 instances behind VM1
   
4. **Secure**
   - VM2 compromise doesn't expose real client IPs
   
5. **Maintainable**
   - Each component has well-defined responsibilities

---

**This architecture ensures the Adaptive NGFW system works correctly with proper separation between the firewall layer (VM1) and the application layer (VM2).**
