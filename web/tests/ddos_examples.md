# 🚀 DDoS Simulation Script - Usage Examples

This guide provides practical examples for using the DDoS simulation script to test rate limiting and NGFW response.

---

## 🎯 Quick Start

### 1. Basic HTTP Flood Test
```bash
python tests/payloads/ddos_script.py --attack http_flood --rate 10 --duration 30
```
**Expected:** 300 requests over 30 seconds, mostly successful

### 2. Basic POST Flood Test
```bash
python tests/payloads/ddos_script.py --attack post_flood --rate 5 --duration 20
```
**Expected:** 100 POST requests with large payloads

### 3. Basic Slowloris Test
```bash
python tests/payloads/ddos_script.py --attack slowloris --connections 10 --duration 30
```
**Expected:** 10 persistent connections for 30 seconds

---

## 📊 Progressive Testing (Recommended Approach)

### Phase 1: Low Intensity (Baseline)
```bash
# Test 1: Gentle HTTP flood
python tests/payloads/ddos_script.py --attack http_flood --rate 10 --duration 30 --threads 2

# Test 2: Gentle POST flood  
python tests/payloads/ddos_script.py --attack post_flood --rate 5 --duration 20 --threads 2

# Test 3: Few connections Slowloris
python tests/payloads/ddos_script.py --attack slowloris --connections 5 --duration 30
```

### Phase 2: Medium Intensity (Rate Limiting)
```bash
# Test 4: Moderate HTTP flood (should trigger rate limiting)
python tests/payloads/ddos_script.py --attack http_flood --rate 50 --duration 60 --threads 5

# Test 5: Moderate POST flood
python tests/payloads/ddos_script.py --attack post_flood --rate 25 --duration 45 --threads 3

# Test 6: More connections Slowloris
python tests/payloads/ddos_script.py --attack slowloris --connections 25 --duration 60
```

### Phase 3: High Intensity (Stress Testing)
```bash
# Test 7: High HTTP flood (heavy rate limiting expected)
python tests/payloads/ddos_script.py --attack http_flood --rate 200 --duration 90 --threads 10

# Test 8: High POST flood
python tests/payloads/ddos_script.py --attack post_flood --rate 100 --duration 60 --threads 8

# Test 9: Maximum connections Slowloris
python tests/payloads/ddos_script.py --attack slowloris --connections 100 --duration 120
```

---

## 🎯 Target-Specific Examples

### Local Testing (Flask Development Server)
```bash
# Default target (127.0.0.1:8081)
python tests/payloads/ddos_script.py --attack http_flood --rate 20 --duration 30
```

### Testing Through NGFW (VM2)
```bash
# Replace with actual VM2 IP
python tests/payloads/ddos_script.py --attack http_flood --rate 50 --duration 60 --target http://192.168.1.100:5000
```

### Testing External Server
```bash
# Test against external server (use responsibly!)
python tests/payloads/ddos_script.py --attack http_flood --rate 10 --duration 20 --target http://example.com
```

---

## 📈 Expected Results by Attack Type

### HTTP Flood Results
| Rate (req/sec) | Expected Behavior | Status Codes |
|----------------|-------------------|--------------|
| 1-10 | All successful | 200 |
| 11-50 | Mostly successful | 200, few 429 |
| 51-100 | Mixed results | 200, 429 |
| 100+ | Heavy rate limiting | Many 429, timeouts |

### POST Flood Results
| Rate (req/sec) | Expected Behavior | Server Impact |
|----------------|-------------------|---------------|
| 1-5 | All successful | Low |
| 6-25 | Rate limiting starts | Medium |
| 26-50 | Heavy rate limiting | High |
| 50+ | Server stress | Very High |

### Slowloris Results
| Connections | Expected Behavior | Impact |
|-------------|-------------------|--------|
| 1-10 | Minimal impact | Low |
| 11-50 | Connection pool usage | Medium |
| 51-100 | Potential exhaustion | High |
| 100+ | Server stress | Critical |

---

## 🔍 Monitoring During Tests

### 1. Watch Flask Logs
```bash
# In another terminal
tail -f logs/app.log | grep -E "(rate limit|429|error)"
```

### 2. Monitor Server Resources
```bash
# CPU and memory usage
top
# or
htop

# Network connections
netstat -an | grep :8081 | wc -l
```

### 3. Check Rate Limiting
```bash
# Look for rate limit responses
curl -s http://127.0.0.1:8081/ -w "%{http_code}\n" -o /dev/null
```

---

## 🚨 Safety Guidelines

### ⚠️ Important Rules
1. **Only test your own systems**
2. **Start with low intensity**
3. **Monitor server health**
4. **Have a kill switch ready (Ctrl+C)**
5. **Test locally before testing through NGFW**

### 🛡️ Rate Limiting Expectations
- **Flask middleware:** 100 req/min per user
- **Global limit:** 50 req/sec
- **429 status codes** when limits are hit
- **Temporary IP blocking** for persistent abuse

### 📊 Success Criteria
- ✅ Script runs without errors
- ✅ Requests are sent at configured rate
- ✅ Statistics are accurate
- ✅ Rate limiting is triggered appropriately
- ✅ Server remains responsive (doesn't crash)

---

## 🧪 Verification Commands

### Test Script Functionality
```bash
# Run the test suite
python tests/test_ddos_script.py
```

### Manual Verification
```bash
# Check if server is responsive after attack
curl -s http://127.0.0.1:8081/ -w "Response time: %{time_total}s\n"

# Check server status
curl -s http://127.0.0.1:8081/stats
```

---

## 📋 Troubleshooting

### Common Issues

#### 1. "Connection refused" errors
```bash
# Check if Flask server is running
curl http://127.0.0.1:8081/
# If not running, start it:
flask run --host=127.0.0.1 --port=8081
```

#### 2. All requests timing out
```bash
# Reduce rate and check server health
python tests/payloads/ddos_script.py --attack http_flood --rate 5 --duration 10
```

#### 3. No rate limiting triggered
```bash
# Increase rate to trigger limits
python tests/payloads/ddos_script.py --attack http_flood --rate 100 --duration 30
```

#### 4. Slowloris not connecting
```bash
# Check if port is correct and accessible
telnet 127.0.0.1 8081
```

---

## 🎯 NGFW Testing Workflow

### Step 1: Local Testing
```bash
# Verify script works locally
python tests/test_ddos_script.py
```

### Step 2: NGFW Testing
```bash
# Test through NGFW (replace IP)
python tests/payloads/ddos_script.py --attack http_flood --rate 50 --duration 60 --target http://VM2_IP:5000
```

### Step 3: Check NGFW Logs
```bash
# On VM1, check Suricata alerts
sudo tail -f /var/log/suricata/eve.json | jq 'select(.event_type=="alert")'

# Check blocked IPs
sudo nft list set inet firewall blocked_ips
```

### Step 4: Analyze Results
- Compare attack success rates
- Check detection accuracy
- Verify adaptive blocking
- Document findings

---

## 📊 Sample Output

### Successful HTTP Flood
```
[HTTP FLOOD] Starting attack...
Target: http://127.0.0.1:8081
Rate: 50 req/sec
Duration: 30 seconds
Threads: 5
Requests per thread: 10
------------------------------------------------------------
[30s] Sent: 1500 | Success: 1200 | Blocked: 250 | Failed: 50

ATTACK STATISTICS
============================================================
Total Requests Sent:    1500
Successful (200):       1200
Blocked (429):          250
Failed/Timeout:         50

Success Rate:           80.00%
Block Rate:             16.67%
Avg Response Time:      45.23ms

Status Code Breakdown:
  200: 1200
  429: 250
  500: 50
============================================================
```

---

**Ready to test! Start with low-intensity attacks and gradually increase to test rate limiting and NGFW detection.**
