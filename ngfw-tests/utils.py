import sys
import json
import requests
import subprocess
import time

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

results = []


def log_test(tc_id, description, passed, detail=""):
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    icon = "✓" if passed else "✗"
    print(f"  {icon} {BOLD}{tc_id}{RESET}: {description}  [{status}]")
    if detail:
        print(f"    {CYAN}{detail}{RESET}")
    results.append((tc_id, description, passed, detail))


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")


def print_summary():
    passed = sum(1 for r in results if r[2])
    total = len(results)
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}RESULTS: {passed}/{total} passed{RESET}")
    if passed == total:
        print(f"{GREEN}{BOLD}ALL TESTS PASSED{RESET}")
    else:
        print(f"{RED}{BOLD}{total - passed} TEST(S) FAILED{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")
    return passed == total


def check_api_alive():
    try:
        r = requests.get(
            f"http://{__import__('config').TARGET}:{__import__('config').API_PORT}/api/health",
            timeout=3,
        )
        return r.status_code == 200
    except Exception:
        return False


def reset_results():
    results.clear()
