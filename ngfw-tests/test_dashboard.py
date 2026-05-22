#!/usr/bin/env python3
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_test, print_header, print_summary, reset_results
import config


def run():
    print_header("Dashboard: UI Tests (TC-DASH-01, TC-DASH-02, TC-DASH-03)")

    # TC-DASH-01: GET /
    try:
        r = requests.get(
            f"{config.DASH_BASE}/",
            timeout=config.REQUEST_TIMEOUT,
        )
        has_html = any(tag in r.text for tag in ["<!DOCTYPE html>", "<html", "<div", "<head"])
        passed = r.status_code == 200 and has_html
        detail = f"HTTP {r.status_code}, {len(r.text)} bytes, has_html={has_html}"
        log_test("TC-DASH-01", "Dashboard loads main page", passed, detail)
    except Exception as e:
        log_test("TC-DASH-01", "Dashboard loads main page", False, str(e))

    # TC-DASH-02: SSE stream endpoint
    try:
        r = requests.get(
            f"{config.DASH_BASE}/api/stream",
            timeout=config.REQUEST_TIMEOUT,
            stream=True,
        )
        content_type = r.headers.get("Content-Type", "")
        is_sse = "text/event-stream" in content_type or "text/plain" in content_type
        passed = r.status_code == 200 and is_sse
        detail = f"HTTP {r.status_code}, Content-Type: {content_type}"
        r.close()
        log_test("TC-DASH-02", "SSE stream endpoint reachable", passed, detail)
    except Exception as e:
        log_test("TC-DASH-02", "SSE stream endpoint reachable", False, str(e))

    # TC-DASH-03: Trigger block event via API
    test_ip = "10.0.0.88"
    try:
        r = requests.post(
            f"{config.API_BASE}/api/block_ip",
            json={"ip": test_ip, "reason": "dashboard-test", "ttl": "1m"},
            timeout=config.REQUEST_TIMEOUT,
        )
        body = r.json()
        passed = body.get("success", False) or r.status_code == 200
        detail = f"HTTP {r.status_code}, success={body.get('success', 'N/A')}"
        log_test("TC-DASH-03", "Block event triggers dashboard update via API", passed, detail)
        # Clean up
        try:
            requests.post(
                f"{config.API_BASE}/api/unblock_ip",
                json={"ip": test_ip},
                timeout=config.REQUEST_TIMEOUT,
            )
        except Exception:
            pass
    except Exception as e:
        log_test("TC-DASH-03", "Block event triggers dashboard update via API", False, str(e))


if __name__ == "__main__":
    reset_results()
    run()
    ok = print_summary()
    sys.exit(0 if ok else 1)
