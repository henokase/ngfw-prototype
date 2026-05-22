#!/usr/bin/env python3
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_test, print_header, print_summary, reset_results
import config


def run():
    print_header("DPI: Open Redirect Test (TC-OR-01)")

    try:
        r = requests.get(
            f"{config.WEB_BASE}/redirect",
            params={"url": "http://evil.com"},
            timeout=config.REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        location = r.headers.get("Location", "")
        passed = r.status_code == 302 and "http://evil.com" in location
        detail = f"HTTP {r.status_code}, Location: {location}"
        log_test("TC-OR-01", "Open redirect to external URL", passed, detail)
    except requests.exceptions.ConnectionError:
        log_test("TC-OR-01", "Open redirect to external URL", False,
                 f"Connection refused to {config.WEB_BASE}")
    except Exception as e:
        log_test("TC-OR-01", "Open redirect to external URL", False, str(e))


if __name__ == "__main__":
    reset_results()
    run()
    ok = print_summary()
    sys.exit(0 if ok else 1)
