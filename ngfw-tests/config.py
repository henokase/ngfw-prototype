import os

TARGET = os.environ.get("TARGET", "192.168.1.70")
WEB_PORT = int(os.environ.get("WEB_PORT", 80))
API_PORT = int(os.environ.get("API_PORT", 5001))
ML_PORT = int(os.environ.get("ML_PORT", 5003))
DASH_PORT = int(os.environ.get("DASH_PORT", 3000))

WEB_BASE = f"http://{TARGET}:{WEB_PORT}"
API_BASE = f"http://{TARGET}:{API_PORT}"
ML_BASE = f"http://{TARGET}:{ML_PORT}"
DASH_BASE = f"http://{TARGET}:{DASH_PORT}"

WAIT = 1
LONG_WAIT = 3
REQUEST_TIMEOUT = 5
