"""
Normal Traffic Test Script
Generates legitimate user behavior patterns for ML baseline training

This script simulates normal user activities:
- User registration and login
- Safe file uploads
- Regular browsing patterns
- Form submissions
- API interactions

Usage:
    python tests/test_normal_requests.py

Output:
    - Console output with test results
    - CSV log: tests/logs/normal_traffic.csv
    - Summary statistics
"""

import requests
import random
import time
import csv
import os
from datetime import datetime
from pathlib import Path

# Configuration
BASE_URL = "http://127.0.0.1:8081"  # Change to VM2 IP when testing through NGFW
OUTPUT_DIR = Path(__file__).parent / "logs"
OUTPUT_FILE = OUTPUT_DIR / "normal_traffic.csv"

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
]

# Test data
TEST_USERS = [
    {"username": f"testuser{i}", "password": f"TestPass{i}!", "email": f"test{i}@example.com"}
    for i in range(1, 6)
]

NORMAL_FEEDBACK = [
    "Great website! Very informative.",
    "I found this resource helpful for learning about security.",
    "Thanks for providing this testing platform.",
    "The interface is user-friendly and easy to navigate.",
    "Excellent documentation and examples.",
]

NORMAL_SEARCH_QUERIES = [
    "security",
    "testing",
    "vulnerability",
    "help",
    "documentation",
]

NORMAL_FILES = [
    ("test.txt", "This is a test file for upload testing.", "text/plain"),
    ("document.txt", "Sample document content for testing purposes.", "text/plain"),
]


class NormalTrafficGenerator:
    """Generate normal user traffic patterns"""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        self.request_count = 0
        
        # Create output directory
        OUTPUT_DIR.mkdir(exist_ok=True)
        
    def get_random_user_agent(self):
        """Get random user agent"""
        return random.choice(USER_AGENTS)
    
    def random_delay(self, min_sec=1, max_sec=5):
        """Random delay between requests (normal user behavior)"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def log_request(self, test_name, method, endpoint, status_code, response_time, success):
        """Log request details"""
        self.request_count += 1
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_time_ms": round(response_time * 1000, 2),
            "success": success,
        }
        self.results.append(result)
        
        status = "✓" if success else "✗"
        print(f"{status} [{self.request_count}] {test_name}: {method} {endpoint} -> {status_code} ({result['response_time_ms']}ms)")
    
    def test_homepage_browsing(self):
        """Test 1: Browse homepage and navigation"""
        print("\n[Test 1] Homepage Browsing")
        
        pages = ["/", "/about", "/help", "/stats"]
        
        for page in pages:
            try:
                headers = {"User-Agent": self.get_random_user_agent()}
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{page}", headers=headers, timeout=10)
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                self.log_request("Homepage Browsing", "GET", page, response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error accessing {page}: {e}")
                self.log_request("Homepage Browsing", "GET", page, 0, 0, False)
    
    def test_user_registration(self):
        """Test 2: User registration with valid credentials"""
        print("\n[Test 2] User Registration")
        
        for user in TEST_USERS[:3]:  # Register 3 users
            try:
                headers = {"User-Agent": self.get_random_user_agent()}
                data = {
                    "username": user["username"],
                    "password": user["password"],
                    "email": user["email"]
                }
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/register",
                    data=data,
                    headers=headers,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                # Success if 200 or 302 (redirect) or user already exists
                success = response.status_code in [200, 302] or "already exists" in response.text.lower()
                self.log_request("User Registration", "POST", "/register", response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error registering {user['username']}: {e}")
                self.log_request("User Registration", "POST", "/register", 0, 0, False)
    
    def test_user_login(self):
        """Test 3: User login with correct credentials"""
        print("\n[Test 3] User Login")
        
        for user in TEST_USERS[:3]:
            try:
                headers = {"User-Agent": self.get_random_user_agent()}
                data = {
                    "username": user["username"],
                    "password": user["password"]
                }
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/login",
                    data=data,
                    headers=headers,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                success = response.status_code in [200, 302]
                self.log_request("User Login", "POST", "/login", response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error logging in {user['username']}: {e}")
                self.log_request("User Login", "POST", "/login", 0, 0, False)
    
    def test_feedback_submission(self):
        """Test 4: Submit normal feedback"""
        print("\n[Test 4] Feedback Submission")
        
        for i, feedback_text in enumerate(NORMAL_FEEDBACK):
            try:
                headers = {"User-Agent": self.get_random_user_agent()}
                data = {
                    "name": f"User{i+1}",
                    "message": feedback_text
                }
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/feedback",
                    data=data,
                    headers=headers,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                success = response.status_code in [200, 302]
                self.log_request("Feedback Submission", "POST", "/feedback", response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error submitting feedback: {e}")
                self.log_request("Feedback Submission", "POST", "/feedback", 0, 0, False)
    
    def test_search_functionality(self):
        """Test 5: Use search with normal queries"""
        print("\n[Test 5] Search Functionality")
        
        for query in NORMAL_SEARCH_QUERIES:
            try:
                headers = {"User-Agent": self.get_random_user_agent()}
                params = {"search": query}
                
                start_time = time.time()
                response = self.session.get(
                    f"{self.base_url}/feedback",
                    params=params,
                    headers=headers,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                self.log_request("Search Functionality", "GET", f"/feedback?search={query}", response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error searching for '{query}': {e}")
                self.log_request("Search Functionality", "GET", f"/feedback?search={query}", 0, 0, False)
    
    def test_file_viewing(self):
        """Test 6: View files with valid paths"""
        print("\n[Test 6] File Viewing")
        
        # Test with safe, existing files
        safe_files = [
            "README.md",
            "requirements.txt",
        ]
        
        for filename in safe_files:
            try:
                headers = {
                    "User-Agent": self.get_random_user_agent(),
                    "Content-Type": "application/json"
                }
                data = {"filename": filename}
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/file",
                    json=data,
                    headers=headers,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                # Success if file found or permission denied (both are normal responses)
                success = response.status_code == 200
                self.log_request("File Viewing", "POST", "/file", response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error viewing file '{filename}': {e}")
                self.log_request("File Viewing", "POST", "/file", 0, 0, False)
    
    def test_command_execution(self):
        """Test 7: Execute safe commands"""
        print("\n[Test 7] Command Execution")
        
        # Safe ping hosts
        safe_hosts = [
            "8.8.8.8",
            "1.1.1.1", 
            "127.0.0.1",
        ]
        
        for host in safe_hosts:
            try:
                headers = {
                    "User-Agent": self.get_random_user_agent(),
                    "Content-Type": "application/json"
                }
                data = {"host": host}
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/cmd",
                    json=data,
                    headers=headers,
                    timeout=15
                )
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                self.log_request("Command Execution", "POST", "/cmd", response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error executing command: {e}")
                self.log_request("Command Execution", "POST", "/cmd", 0, 0, False)
    
    def test_xml_parsing(self):
        """Test 8: Parse normal XML"""
        print("\n[Test 8] XML Parsing")
        
        normal_xml_samples = [
            "<user><name>John</name><email>john@example.com</email></user>",
            "<data><item>Test Item</item><value>123</value></data>",
            "<message><from>User</from><text>Hello World</text></message>",
        ]
        
        for xml_data in normal_xml_samples:
            try:
                headers = {
                    "User-Agent": self.get_random_user_agent(),
                    "Content-Type": "application/json"
                }
                data = {"xml": xml_data}
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/api/xml",
                    json=data,
                    headers=headers,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                self.log_request("XML Parsing", "POST", "/api/xml", response.status_code, response_time, success)
                
                self.random_delay()
            except Exception as e:
                print(f"✗ Error parsing XML: {e}")
                self.log_request("XML Parsing", "POST", "/api/xml", 0, 0, False)
    
    def save_results(self):
        """Save results to CSV"""
        print(f"\n[Saving Results] Writing to {OUTPUT_FILE}")
        
        with open(OUTPUT_FILE, 'w', newline='') as csvfile:
            if self.results:
                fieldnames = self.results[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
        
        print(f"✓ Results saved to {OUTPUT_FILE}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("NORMAL TRAFFIC TEST SUMMARY")
        print("="*60)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful
        
        if total > 0:
            success_rate = (successful / total) * 100
            avg_response_time = sum(r["response_time_ms"] for r in self.results) / total
            
            print(f"Total Requests:     {total}")
            print(f"Successful:         {successful} ({success_rate:.1f}%)")
            print(f"Failed:             {failed}")
            print(f"Avg Response Time:  {avg_response_time:.2f}ms")
            
            # Response time statistics
            response_times = [r["response_time_ms"] for r in self.results if r["success"]]
            if response_times:
                print(f"Min Response Time:  {min(response_times):.2f}ms")
                print(f"Max Response Time:  {max(response_times):.2f}ms")
        
        print("="*60)
    
    def run_all_tests(self):
        """Run all normal traffic tests"""
        print("="*60)
        print("NORMAL TRAFFIC GENERATOR")
        print("="*60)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Run all test scenarios
        self.test_homepage_browsing()
        self.test_user_registration()
        self.test_user_login()
        self.test_feedback_submission()
        self.test_search_functionality()
        self.test_file_viewing()
        self.test_command_execution()
        self.test_xml_parsing()
        
        # Save results and print summary
        self.save_results()
        self.print_summary()


def main():
    """Main function"""
    generator = NormalTrafficGenerator()
    generator.run_all_tests()


if __name__ == "__main__":
    main()
