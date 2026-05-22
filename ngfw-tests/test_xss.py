#!/usr/bin/env python3
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_test, print_header, print_summary, reset_results
import config


def run():
    print_header("DPI: Reflected XSS Test (TC-XSS-01)")

    payload = "<script>alert('XSS')</script>"
    try:
        r = requests.get(
            f"{config.WEB_BASE}/feedback",
            params={"q": payload},
            timeout=config.REQUEST_TIMEOUT,
        )
        passed = payload in r.text
        detail = f"HTTP {r.status_code}, payload {'found' if passed else 'NOT found'} in response ({len(r.text)} bytes)"
        log_test("TC-XSS-01", "Reflected XSS via feedback endpoint", passed, detail)
    except requests.exceptions.ConnectionError:
        log_test("TC-XSS-01", "Reflected XSS via feedback endpoint", False,
                 f"Connection refused to {config.WEB_BASE}")
    except Exception as e:
        log_test("TC-XSS-01", "Reflected XSS via feedback endpoint", False, str(e))


if __name__ == "__main__":
    reset_results()
    run()
    ok = print_summary()
    sys.exit(0 if ok else 1)
