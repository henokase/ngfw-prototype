import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.antivirus_service import get_antivirus_service


def main() -> None:
    """Simple script to verify ClamAV connectivity from the Flask environment.

    It creates two temporary files under /tmp:
    - a clean file (should be reported as clean)
    - an EICAR test file (should be reported as infected when ClamAV is active)

    Run this on VM2 with the same virtualenv used for the web app.
    """

    temp_dir = Path("/tmp")

    clean_path = temp_dir / "ngfw_clean_test.txt"
    infected_path = temp_dir / "ngfw_eicar_test.com"

    clean_path.write_text("This is a harmless test file for NGFW ClamAV connectivity.\n")

    # Standard EICAR test string (single line, no newline at end required)
    infected_path.write_text(
        "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
    )

    av_service = get_antivirus_service()

    print("[+] Scanning clean file:", clean_path)
    clean_result = av_service.scan_file(str(clean_path))
    print("    Result:", clean_result)

    print("[+] Scanning EICAR test file:", infected_path)
    infected_result = av_service.scan_file(str(infected_path))
    print("    Result:", infected_result)

    print("\nSummary:")
    print("  Clean file status   :", clean_result.get("status"))
    print("  Infected file status:", infected_result.get("status"))

    print("\nIf ClamAV is correctly wired:")
    print("  - Clean file should be 'clean'.")
    print("  - EICAR file should be 'infected' with an appropriate signature.")


if __name__ == "__main__":
    main()
