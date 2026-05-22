# 5-Minute NGFW Prototype Demo Guide

## Prerequisites (Before Demo Starts)

```bash
# Terminal 1 — Web app (already running)
# Terminal 2 — Dashboard
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-dashboard && npm run dev

# Terminal 3 — Demo commands
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-tests
```

Verify all services are up:
```bash
sudo systemctl status ngfw-control ngfw-ml ngfw-flowmeter suricata-ips suri-clam clamav-daemon
```

---

## Script

### 0:00–0:30 — Opening

**Say:**
> "This is an Adaptive NGFW prototype built entirely from open-source components for resource-constrained institutions. It provides four detection layers — DPI via Suricata, malware scanning via ClamAV, behavioral anomaly detection via a 5-model ML ensemble, and packet-level rate limiting via nftables — all with automated IP blocking and a real-time dashboard."

---

### 0:30–1:30 — DPI Attack Demo

**Say:**
> "Let me demonstrate the DPI layer. I'll send SQL injection and command injection payloads through the gateway. Suricata inspects every packet and generates an alert."

**Do:**
```bash
python3 test_sqli.py
```

**Say (while it runs):**
> "Three SQLi payloads — OR bypass, comment-out, and UNION SELECT — all detected and blocked."

**Do:**
```bash
python3 test_cmdi.py
```

**Say:**
> "Two command injection attempts — both detected. Suricata blocks the source IP within 0.8 seconds."

---

### 1:30–2:00 — Dashboard

**Say:**
> "All detections appear in the dashboard in real time via Server-Sent Events."

**Do:** Open browser to `http://192.168.1.70:3000`, log in with `admin` / `Pass123!`

**Point to:**
- Blocked IPs panel
- Logs panel showing recent detections
- Real-time updates every 5 seconds

---

### 2:00–2:30 — ML Ensemble Demo

**Say:**
> "The ML ensemble detects behavioral anomalies that signature-based rules miss. It uses 5 models — Random Forest, XGBoost, Decision Tree, Logistic Regression, and CatBoost — with soft-voting. 83% accuracy on the CICIDS2017 test set."

**Do:**
```bash
python3 test_ml_api.py
```

**Say:**
> "Three scenarios: high-confidence attack flow triggers an automatic block, medium confidence triggers an alert, and low-confidence benign traffic is allowed."

---

### 2:30–3:00 — nftables Firewall

**Say:**
> "nftables provides packet filtering with dynamic IP blocking and TTL-based expiry. Blocks persist in both the kernel set and SQLite database."

**Do:**
```bash
python3 test_firewall.py
```

**Say:**
> "Block, unblock, and TTL-based auto-expiry all verified. SYN and UDP flood rate limiting is enforced at the kernel level."

---

### 3:00–3:30 — Malware Scanning

**Say:**
> "ClamAV scans uploaded files via the INSTREAM protocol. When malware is found, the source IP is automatically blocked."

**Do:**
```bash
python3 test_malware.py
```

**Say:**
> "The EICAR test file was detected in 42 milliseconds and the attacker was blocked."

---

### 3:30–4:00 — ML Behavioral Attacks

**Say:**
> "The ML ensemble also detects specific behavioral attack patterns: Slowloris DoS, DNS amplification, ICMP floods, ping sweeps, port scans, and behavioral brute-force."

**Do:**
```bash
python3 test_behavioral.py
```

**Say:**
> "All six scenarios detected with confidence scores exceeding 0.78, triggering automatic IP blocking."

---

### 4:00–4:30 — Summary & Wrap

**Say:**
> "In summary, this NGFW prototype provides four-layer threat detection — DPI, malware scanning, ML-based behavioral analysis, and rate limiting — with automated sub-second response, all on modest hardware. The full source code, documentation, and test suite are available in the project repository."

---

### 4:30–5:00 — Buffer for questions or quick live verification

**Optional:** Run `sudo nft list set inet firewall blocked_ips` to show blocked IPs live.

---

## Quick-Reference Command Cheat Sheet

```bash
# Run individual test
python3 test_sqli.py                    # ~10s
python3 test_cmdi.py                    # ~10s
python3 test_ml_api.py                  # ~5s
python3 test_firewall.py                # ~5s
python3 test_malware.py                 # ~5s
python3 test_behavioral.py              # ~15s

# Run ALL tests
python3 run_all.py                      # ~2-3 min

# Check blocked IPs
curl http://localhost:5001/api/list_blocks | python3 -m json.tool
sudo nft list set inet firewall blocked_ips

# Health checks
curl http://localhost:5001/api/health | python3 -m json.tool
curl http://localhost:5003/health | python3 -m json.tool

# Dashboard
cd /home/heroubuntu/Desktop/ngfw-prototype/ngfw-dashboard && npm run dev
# Login: admin / Pass123!
```

## Timing Summary

| Segment | Time | Action |
|---------|------|--------|
| Opening | 0:00–0:30 | Explain architecture |
| DPI Demo | 0:30–1:30 | test_sqli.py + test_cmdi.py |
| Dashboard | 1:30–2:00 | Show live updates |
| ML Ensemble | 2:00–2:30 | test_ml_api.py |
| nftables | 2:30–3:00 | test_firewall.py |
| Malware | 3:00–3:30 | test_malware.py |
| Behavioral | 3:30–4:00 | test_behavioral.py |
| Wrap | 4:00–4:30 | Summary |
| Buffer | 4:30–5:00 | Questions |

**Total: ~5 minutes**
