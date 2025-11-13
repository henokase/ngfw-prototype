# NGFW Test Website - Testing Suite

This directory contains automated testing scripts and attack payload collections for validating the NGFW Test Website vulnerabilities and generating traffic for NGFW analysis.

## 📁 Directory Structure

```
tests/
├── README.md                      # This file
├── test_normal_requests.py        # Normal traffic generator
├── test_attack_payloads.py        # Attack payload tester
├── payloads/                      # Attack payload collections
│   ├── README.md
│   ├── sql_injection.txt
│   ├── xss.txt
│   ├── lfi.txt
│   ├── xxe.txt
│   ├── redirect.txt
│   └── command_injection.txt
└── logs/                          # Test results (generated)
    ├── normal_traffic.csv
    └── attack_traffic.csv
```

## 🎯 Purpose

### 1. Validate Vulnerabilities
Confirm that all intentional vulnerabilities are exploitable and working as designed.

### 2. Generate Test Traffic
Create both normal and malicious traffic patterns for:
- NGFW detection testing
- ML model training (baseline and anomaly)
- Suricata rule validation
- Log analysis

### 3. Establish Baselines
Generate legitimate user behavior patterns for ML anomaly detection training.

### 4. Test NGFW Integration
Verify that attacks are detected and logged by the NGFW system.

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure Flask app is running
cd /opt/testsite/web
flask run --host=127.0.0.1 --port=5000

# Or if testing through NGFW
# Update BASE_URL in test scripts to VM2 IP
```

### Run Normal Traffic Tests

```bash
python tests/test_normal_requests.py
```

**Output:**
- Console: Real-time test progress
- CSV: `tests/logs/normal_traffic.csv`
- Summary: Request statistics

**What it does:**
- Simulates legitimate user behavior
- Registers users, logs in
- Browses pages normally
- Submits safe forms
- Uploads clean files
- Generates 50+ normal requests

### Run Attack Payload Tests

```bash
python tests/test_attack_payloads.py
```

**Output:**
- Console: Exploitation results
- CSV: `tests/logs/attack_traffic.csv`
- Summary: Vulnerability breakdown

**What it tests:**
- SQL Injection (10+ payloads)
- Stored XSS (10+ payloads)
- Reflected XSS (5+ payloads)
- Command Injection (10+ payloads)
- Path Traversal (8+ payloads)
- XXE (4+ payloads)
- Open Redirect (5+ payloads)
- IDOR (5+ payloads)

## 📊 Test Scripts

### `test_normal_requests.py`

**Purpose:** Generate legitimate user traffic for ML baseline training

**Features:**
- User registration and login
- Safe file uploads
- Regular browsing patterns
- Form submissions
- API interactions
- Random delays (1-5 seconds)
- User agent rotation
- Response time tracking

**Configuration:**
```python
BASE_URL = "http://127.0.0.1:5000"  # Change for NGFW testing
```

**Output Fields:**
- timestamp
- test_name
- method
- endpoint
- status_code
- response_time_ms
- success

### `test_attack_payloads.py`

**Purpose:** Automated vulnerability testing with malicious payloads

**Features:**
- Tests all vulnerability types
- Verifies successful exploitation
- Tracks detection rates
- Detailed logging
- Exploitation confirmation

**Configuration:**
```python
BASE_URL = "http://127.0.0.1:5000"  # Change for NGFW testing
```

**Output Fields:**
- timestamp
- test_number
- vulnerability
- payload
- endpoint
- status_code
- exploited
- details

## 📁 Payload Collections

See `payloads/README.md` for detailed information.

**Available Payloads:**
- **SQL Injection:** 50+ payloads
- **XSS:** 60+ payloads
- **Path Traversal:** 70+ payloads
- **XXE:** 40+ payloads
- **Open Redirect:** 80+ payloads
- **Command Injection:** 100+ payloads

## 📈 Usage Scenarios

### Scenario 1: Local Development Testing

```bash
# Test locally before deployment
python tests/test_normal_requests.py
python tests/test_attack_payloads.py
```

### Scenario 2: NGFW Integration Testing

```bash
# Update BASE_URL to VM2 IP (through NGFW)
# In test scripts, change:
BASE_URL = "http://10.0.0.5"  # VM2 IP

# Run tests
python tests/test_normal_requests.py
python tests/test_attack_payloads.py

# Check NGFW logs
sudo tail -f /var/log/suricata/eve.json
```

### Scenario 3: ML Model Training

```bash
# Generate normal traffic baseline (run multiple times)
for i in {1..10}; do
    python tests/test_normal_requests.py
    sleep 60
done

# Generate attack traffic for anomaly detection
python tests/test_attack_payloads.py
```

### Scenario 4: Manual Payload Testing

```bash
# Load specific payloads
cat tests/payloads/sql_injection.txt

# Copy and test manually in browser or with curl
curl -X POST http://127.0.0.1:5000/login \
  -d "username=' OR '1'='1'--&password=anything"
```

## 🔍 Analyzing Results

### Normal Traffic Results

```bash
# View CSV
cat tests/logs/normal_traffic.csv

# Count successful requests
grep "True" tests/logs/normal_traffic.csv | wc -l

# Average response time
awk -F',' 'NR>1 {sum+=$6; count++} END {print sum/count}' tests/logs/normal_traffic.csv
```

### Attack Traffic Results

```bash
# View CSV
cat tests/logs/attack_traffic.csv

# Count exploited vulnerabilities
grep "True" tests/logs/attack_traffic.csv | wc -l

# Breakdown by vulnerability type
awk -F',' 'NR>1 {print $3}' tests/logs/attack_traffic.csv | sort | uniq -c
```

## 🎯 Expected Results

### Normal Traffic
- **Success Rate:** >95%
- **Avg Response Time:** <500ms
- **Status Codes:** Mostly 200, some 302 (redirects)
- **No Errors:** Clean execution

### Attack Traffic
- **Exploitation Rate:** >80% (intentionally vulnerable)
- **SQL Injection:** Should succeed (bypass login)
- **XSS:** Should be stored/reflected
- **Command Injection:** Should execute commands
- **Path Traversal:** Should read files
- **XXE:** Should process entities
- **Open Redirect:** Should redirect
- **IDOR:** Should access other users' data

## 🔧 Customization

### Add New Test Scenarios

Edit `test_normal_requests.py`:

```python
def test_new_scenario(self):
    """Test 9: New test scenario"""
    print("\n[Test 9] New Scenario")
    # Your test code here
```

### Add New Attack Tests

Edit `test_attack_payloads.py`:

```python
def test_new_vulnerability(self):
    """Test 9: New Vulnerability"""
    print("\n" + "="*60)
    print("[TEST 9] NEW VULNERABILITY")
    print("="*60)
    # Your test code here
```

### Add New Payloads

Create new file in `payloads/`:

```bash
# Create new payload file
nano tests/payloads/new_vulnerability.txt

# Add payloads (one per line, # for comments)
```

## 📊 Integration with NGFW

### Check Suricata Alerts

```bash
# View real-time alerts
sudo tail -f /var/log/suricata/eve.json | jq 'select(.event_type=="alert")'

# Count alerts by signature
sudo cat /var/log/suricata/eve.json | jq -r 'select(.event_type=="alert") | .alert.signature' | sort | uniq -c
```

### Check Application Logs

```bash
# View security events
tail -f logs/security.log

# Count attack attempts
grep "SQL injection" logs/security.log | wc -l
```

### Check NGFW Blocking

```bash
# On VM1, check blocked IPs
sudo nft list set inet firewall blocked_ips
```

## ⚠️ Important Notes

### Testing Through NGFW

When testing through the NGFW (VM1 → VM2):
- Update `BASE_URL` to VM2's IP
- Attacks should be detected by Suricata
- Some attacks may be blocked
- Check VM1 logs for detection

### Rate Limiting

The application has rate limiting:
- 100 requests/minute per user
- 50 requests/second global
- Tests include delays to avoid limits

### File Uploads

For file upload tests:
- ClamAV must be running on VM2
- EICAR test file will be quarantined
- Infected files trigger IP blocking

## 🚀 Next Steps

After running tests:

1. **Analyze Results**
   - Review CSV logs
   - Check exploitation rates
   - Identify blocked attacks

2. **Verify NGFW Detection**
   - Check Suricata alerts
   - Review ML model predictions
   - Verify IP blocking

3. **Tune Detection**
   - Update Suricata rules
   - Retrain ML model
   - Adjust thresholds

4. **Document Findings**
   - Create test report
   - List detected vs. missed attacks
   - Provide recommendations

## 📚 Resources

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Suricata Documentation](https://suricata.readthedocs.io/)
- [Python Requests Library](https://requests.readthedocs.io/)

## ⚖️ Legal Disclaimer

These tests are for authorized security testing only. Only use on systems you own or have explicit permission to test. Unauthorized testing is illegal.
