# Attack Payload Collections

This directory contains organized collections of attack payloads for testing web application vulnerabilities.

## ⚠️ WARNING

**These payloads are for AUTHORIZED TESTING ONLY!**

- Only use on systems you own or have explicit permission to test
- Never use these payloads against production systems without authorization
- Unauthorized testing is illegal and unethical
- These payloads can cause damage or data loss

## 📁 Payload Files

### `sql_injection.txt`
SQL injection payloads for testing database vulnerabilities:
- Authentication bypass
- Union-based injection
- Time-based blind injection
- Error-based injection
- Boolean-based blind injection
- Stacked queries

**Target Endpoints:**
- `/login` - Login form
- `/feedback?search=` - Search functionality
- Any database query input

### `xss.txt`
Cross-Site Scripting (XSS) payloads:
- Basic script tags
- Image tag XSS
- SVG XSS
- Event handlers
- Filter bypass techniques
- Encoding variations
- Context breaking
- DOM-based XSS

**Target Endpoints:**
- `/feedback` - Stored XSS (feedback form)
- `/feedback?search=` - Reflected XSS (search)
- Any user input that's displayed

### `lfi.txt`
Path Traversal / Local File Inclusion payloads:
- Linux file paths
- Windows file paths
- URL encoding
- Double encoding
- Null byte injection
- Filter bypass techniques
- Interesting system files

**Target Endpoints:**
- `/file` - File viewer
- Any file path parameter

### `xxe.txt`
XML External Entity (XXE) payloads:
- File disclosure (Linux/Windows)
- SSRF (Server-Side Request Forgery)
- Blind XXE
- Billion laughs attack (DoS)
- PHP wrappers
- Data exfiltration

**Target Endpoints:**
- `/api/xml` - XML parser
- Any XML input

### `redirect.txt`
Open redirect payloads:
- External redirects
- Protocol-relative URLs
- Filter bypass techniques
- JavaScript/Data protocols
- Encoding variations

**Target Endpoints:**
- `/redirect` - Redirect function
- Any URL parameter

### `command_injection.txt`
Command injection payloads:
- Command chaining (Linux/Windows)
- Pipe operators
- AND/OR operators
- Backtick execution
- Command substitution
- Filter bypass techniques
- Time-based detection
- Reverse shells

**Target Endpoints:**
- `/cmd` - Command execution
- Any system command input

## 🔧 Usage

### Manual Testing

1. Choose appropriate payload file for the vulnerability type
2. Copy a payload from the file
3. Paste into the target input field
4. Submit and observe the response

### Automated Testing

Use the test scripts:

```bash
# Test with attack payloads
python tests/test_attack_payloads.py

# Generate normal traffic
python tests/test_normal_requests.py
```

### Custom Scripts

Load payloads programmatically:

```python
# Load SQL injection payloads
with open('tests/payloads/sql_injection.txt', 'r') as f:
    payloads = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Test each payload
for payload in payloads:
    # Your testing code here
    pass
```

## 📊 Payload Statistics

| File | Payloads | Vulnerability Type |
|------|----------|-------------------|
| `sql_injection.txt` | 50+ | SQL Injection |
| `xss.txt` | 60+ | Cross-Site Scripting |
| `lfi.txt` | 70+ | Path Traversal / LFI |
| `xxe.txt` | 40+ | XML External Entity |
| `redirect.txt` | 80+ | Open Redirect |
| `command_injection.txt` | 100+ | Command Injection |

## 🎯 Testing Strategy

### 1. Start with Basic Payloads
Begin with simple, well-known payloads to confirm vulnerability exists.

### 2. Test Filter Bypass
If basic payloads are blocked, try encoding and bypass techniques.

### 3. Verify Exploitation
Confirm that the payload actually exploits the vulnerability (don't just check for error messages).

### 4. Document Results
Record which payloads work and which are blocked for NGFW analysis.

## 🔍 Detection Indicators

These payloads should trigger alerts in:
- **Suricata IDS** - Signature-based detection
- **ML Anomaly Detection** - Behavioral analysis
- **Application Logs** - Security event logging
- **WAF Rules** - Web Application Firewall

## 📝 Notes

- Payloads are organized by difficulty (basic → advanced)
- Comments start with `#` and explain payload purpose
- Some payloads are platform-specific (Linux vs Windows)
- Encoding variations help test filter bypass
- Time-based payloads useful for blind vulnerabilities

## 🚀 Next Steps

After testing with these payloads:

1. **Analyze Results** - Which payloads succeeded?
2. **Check NGFW Logs** - Were attacks detected?
3. **Review ML Model** - Did anomaly detection trigger?
4. **Update Signatures** - Add new detection rules
5. **Improve Defenses** - Patch vulnerabilities or enhance detection

## 📚 Resources

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings)
- [HackTricks](https://book.hacktricks.xyz/)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security)

## ⚖️ Legal Disclaimer

These payloads are provided for educational and authorized security testing purposes only. The authors are not responsible for any misuse or damage caused by these payloads. Always obtain proper authorization before testing any system.
