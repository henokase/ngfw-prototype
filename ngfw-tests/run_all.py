#!/usr/bin/env python3
import subprocess
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

SCRIPTS = [
    ("DPI - SQL Injection",          "test_sqli.py"),
    ("DPI - XSS",                    "test_xss.py"),
    ("DPI - Command Injection",      "test_cmdi.py"),
    ("DPI - Path Traversal",         "test_lfi.py"),
    ("DPI - XXE",                    "test_xxe.py"),
    ("DPI - Open Redirect",          "test_open_redirect.py"),
    ("Malware - EICAR Upload",       "test_malware.py"),
    ("ML - API Confidence Tests",    "test_ml_api.py"),
    ("ML - Behavioral Attacks",      "test_behavioral.py"),
    ("Firewall - nftables API",      "test_firewall.py"),
    ("Firewall - UDP Flood",         "test_udp_flood.py"),
    ("Dashboard - UI Tests",         "test_dashboard.py"),
]


def check_target():
    import requests
    try:
        r = requests.get(
            f"http://{config.TARGET}:{config.API_PORT}/api/health",
            timeout=3,
        )
        return r.status_code == 200
    except Exception:
        try:
            import subprocess
            r = subprocess.run(
                ["ping", "-c", "1", "-W", "2", config.TARGET],
                capture_output=True, text=True, timeout=5,
            )
            return r.returncode == 0
        except Exception:
            return False


def main():
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}  ADAPTIVE NGFW PROTOTYPE - TEST SUITE{RESET}")
    print(f"{BOLD}{BLUE}  Target: {config.TARGET}:{config.WEB_PORT}{RESET}")
    print(f"{BOLD}{BLUE}  API:    {config.TARGET}:{config.API_PORT}{RESET}")
    print(f"{BOLD}{BLUE}  ML:     {config.TARGET}:{config.ML_PORT}{RESET}")
    print(f"{BOLD}{BLUE}  Dash:   {config.TARGET}:{config.DASH_PORT}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

    print(f"{BOLD}Checking target reachability...{RESET}", end=" ")
    sys.stdout.flush()
    alive = check_target()
    if alive:
        print(f"{GREEN}✓ Target is reachable{RESET}\n")
    else:
        print(f"{YELLOW}⚠ Target not fully reachable (tests may show connection errors){RESET}\n")

    all_results = []
    script_dir = os.path.dirname(os.path.abspath(__file__))

    for category, script in SCRIPTS:
        script_path = os.path.join(script_dir, script)
        print(f"{BOLD}[{category}]{RESET} Running {script}...")
        sys.stdout.flush()

        try:
            r = subprocess.run(
                [sys.executable, script_path],
                capture_output=True, text=True, timeout=120,
            )
            output = r.stdout + r.stderr
            print(output)

            pass_count = output.count("PASS")
            fail_count = output.count("FAIL")
            # Count actual test lines (pattern: TC-XXXX)
            test_count = sum(1 for line in output.split('\n') if 'TC-' in line and ('PASS' in line or 'FAIL' in line))
            passed = fail_count == 0

            if passed:
                print(f"  {GREEN}✓ All {test_count or pass_count} test(s) passed{RESET}\n")
            else:
                print(f"  {RED}✗ {fail_count} test(s) failed out of {test_count or (pass_count + fail_count)}{RESET}\n")

            all_results.append((category, script, passed, test_count or (pass_count + fail_count),
                                fail_count, r.returncode))
        except subprocess.TimeoutExpired:
            print(f"  {RED}✗ TIMEOUT (120s exceeded){RESET}\n")
            all_results.append((category, script, False, 0, 0, -1))
        except Exception as e:
            print(f"  {RED}✗ Error: {e}{RESET}\n")
            all_results.append((category, script, False, 0, 0, -1))

    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}  FINAL SUMMARY{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{'Category':<30} {'Tests':<8} {'Failed':<8} {'Result':<10}{RESET}")
    print(f"{BOLD}{'-'*60}{RESET}")

    total_tests = 0
    total_failed = 0
    all_passed = True

    for category, script, passed, test_count, fail_count, rc in all_results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        symbol = "✓" if passed else "✗"
        print(f"{symbol:<2} {category:<28} {test_count:<8} {fail_count:<8} {status:<10}")
        total_tests += test_count
        total_failed += fail_count
        if not passed:
            all_passed = False

    print(f"{BOLD}{'-'*60}{RESET}")
    print(f"{BOLD}Total test cases: {total_tests}{RESET}")
    if total_failed > 0:
        print(f"{BOLD}Total failures:   {RED}{total_failed}{RESET}")
    else:
        print(f"{BOLD}Total failures:   0{RESET}")

    if all_passed:
        print(f"\n{GREEN}{BOLD}  ╔══════════════════════════════╗{RESET}")
        print(f"{GREEN}{BOLD}  ║   ALL TESTS PASSED ✓         ║{RESET}")
        print(f"{GREEN}{BOLD}  ╚══════════════════════════════╝{RESET}")
    else:
        print(f"\n{RED}{BOLD}  ╔══════════════════════════════╗{RESET}")
        print(f"{RED}{BOLD}  ║   SOME TESTS FAILED ✗        ║{RESET}")
        print(f"{RED}{BOLD}  ╚══════════════════════════════╝{RESET}")

    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
