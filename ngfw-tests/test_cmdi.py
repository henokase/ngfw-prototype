#!/usr/bin/env python3
import sys
import os
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_test, print_header, print_summary, reset_results
import config


def run():
    print_header("DPI: Command Injection Tests (TC-CMDI-01, TC-CMDI-02)")

    tests = [
        ("TC-CMDI-01", "System command: id",
         {"command": "id"}, ["uid=", "gid=", "groups="]),
        ("TC-CMDI-02", "File read: /etc/passwd",
         {"command": "cat /etc/passwd"}, ["root:x:0:0:"]),
    ]

    for tc_id, desc, payload, patterns in tests:
        try:
            r = requests.post(
                f"{config.WEB_BASE}/cmd",
                json=payload,
                timeout=config.REQUEST_TIMEOUT,
            )
            passed = False
            detail = f"HTTP {r.status_code}"
            try:
                body = r.json()
                body_str = json.dumps(body)
            except Exception:
                body_str = r.text
            for pat in patterns:
                if pat in body_str:
                    passed = True
                    detail += f" contains '{pat}'"
                    break
            if not passed:
                detail += " - no expected pattern in response"
                detail += f" ({body_str[:200]})"
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
