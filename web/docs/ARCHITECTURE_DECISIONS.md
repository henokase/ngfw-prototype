# Architecture Decisions

**Date:** November 10, 2025
**Updated:** May 2, 2026
**Project:** Adaptive NGFW Prototype

---

## VM1/VM2 Detection Architecture

### The Fundamental Design

**VM1 handles all threat detection and IP blocking independently.** VM2 does not communicate with VM1.

### Why This Architecture?

1. **VM1 is the Firewall Gateway**
   - All traffic passes through VM1 before reaching VM2
   - VM1 has full visibility of real source IPs (pre-NAT)
   - Suricata on VM1 inspects traffic and extracts uploaded files
   - VM1's ClamAV scans extracted files for malware
   - VM1 blocks source IPs directly via nftables (no correlation needed)

2. **VM2 is Behind NAT**
   - All traffic to VM2 appears to come from VM1's IP (`10.0.0.1`)
   - VM2 cannot distinguish between different external clients
   - VM2 has no access to real client IPs
   - VM2's role is purely as the attack surface

3. **Security Separation**
   - VM1 = Network layer detection and response
   - VM2 = Application layer attack surface with local quarantine
   - No coupling between VMs — VM2 can be replaced or scaled independently

### Detection Flow

```
External Client (Real IP)
        │
        ▼
┌───────────────────────────────────┐
│  VM1 - Gateway (10.0.0.1)         │
│                                   │
│  Suricata monitors traffic        │
│    ↓                              │
│  Extracts uploaded files          │
│    ↓                              │
│  ClamAV scans files               │
│    ↓ (if malware)                 │
│  nftables blocks real source IP   │
│    ↓                              │
│  DNAT forwards traffic to VM2     │
└───────────────┬───────────────────┘
                │ DNAT (source = 10.0.0.1)
                ▼
┌───────────────────────────────────┐
│  VM2 - Web Server (10.0.0.5)      │
│                                   │
│  • Sees only VM1's IP             │
│  • Serves vulnerable endpoints    │
│  • Local ClamAV scan (secondary)  │
│  • Quarantines infected files     │
│  • Logs detections locally        │
│  • NO communication to VM1        │
└───────────────────────────────────┘
```

### VM2's Local ClamAV Purpose

VM2 runs its own ClamAV not to notify VM1, but to:
- Quarantine infected files locally
- Log malware detections in its own database
- Provide UI feedback about scan results
- Serve as a secondary detection layer

---

## Rate Limiting Architecture

### Why Session/Account-Based Instead of IP-Based?

**Problem with IP-Based Rate Limiting:**
- VM2 only sees VM1's IP (`10.0.0.1`)
- All clients appear as the same IP
- Cannot distinguish between different users

**Solution: Three-Tier Rate Limiting**

### Tier 1: Session-Based (Unauthenticated Users)
- Auto-generated session UUID
- 100 requests/minute per session
- Identifier: `session:<uuid>`

### Tier 2: Account-Based (Authenticated Users)
- Username from session after login
- 100 requests/minute per account
- Identifier: `user:<username>`

### Tier 3: Global Flood Protection
- 50 requests/second site-wide
- Prevents application crashes during DDoS
- Returns HTTP 503 when exceeded

### Rate Limiting Flow
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

## Database Logging Design

### LogEvent Table Schema

```sql
CREATE TABLE log_events (
    id INTEGER PRIMARY KEY,
    ip_address VARCHAR(45),          -- Always VM1's IP (10.0.0.1)
    endpoint VARCHAR(255),
    method VARCHAR(10),
    payload TEXT,
    user_agent VARCHAR(512),
    status_code INTEGER,
    timestamp DATETIME,
    session_id VARCHAR(255),         -- Session tracking
    username VARCHAR(100),           -- Account tracking
    upload_result VARCHAR(20),       -- 'clean', 'infected', 'error'
    filename VARCHAR(255),           -- Uploaded file name
    file_hash VARCHAR(64),           -- SHA256 hash
    response_time FLOAT              -- Response time in seconds
);
```

### Why These Columns?

1. **session_id / username** — Track behavior across requests, correlate attacks to specific sessions/accounts
2. **upload_result / filename / file_hash** — Track uploads, link malware detections to sessions, provide audit trail
3. **response_time** — Identify slow endpoints, detect potential DoS attacks

---

## Security Headers Design

Headers are intentionally relaxed to allow XSS testing:

| Header | Value | Rationale |
|--------|-------|-----------|
| `Content-Security-Policy` | `default-src 'self' 'unsafe-inline' 'unsafe-eval'` | Allows XSS payloads to execute |
| `X-XSS-Protection` | `0` | Disabled so browser doesn't filter XSS |
| `X-Content-Type-Options` | `nosniff` | Standard protection (doesn't block XSS) |
| `X-Frame-Options` | `SAMEORIGIN` | Standard protection |

---

## Key Takeaways

1. **VM1 detects and blocks independently** — Suricata + ClamAV on the gateway, no inter-VM communication
2. **VM2 is IP-blind** — Only sees VM1's NAT IP, has no awareness of real clients
3. **No VM2-to-VM1 alerts** — The previous design with `/api/malware_alert` and conntrack correlation was removed
4. **Rate limiting is user-based** — Session/account tracking, not IP-based
5. **VM2 ClamAV is local only** — Quarantines files and logs detections within the web app
6. **Logging is comprehensive** — Session, account, uploads, and performance all tracked

---

## Benefits

1. **Simpler architecture** — No complex correlation logic needed
2. **Accurate blocking** — VM1 sees real IPs directly, no guessing
3. **Resilient** — VM2 compromise doesn't affect VM1's detection capability
4. **Scalable** — Multiple VM2 instances can sit behind VM1
5. **Clear separation** — Network security (VM1) vs attack surface (VM2)
