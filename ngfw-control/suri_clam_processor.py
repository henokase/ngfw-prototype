"""Suricata → ClamAV processor for NGFW decision engine (VM1).

This script tails the Suricata EVE JSON log and reacts to two types of events:

1. **fileinfo events** (existing behavior):
   - Locates the file in the Suricata filestore (/var/log/suricata/filestore).
   - Scans it with ClamAV via clamd.
   - On malware detection, sends events to the NGFW control API
     (/api/log_detection and /api/block_ip).

2. **alert events** (NEW behavior):
   - Extracts alert metadata (severity, signature, SID, category).
   - Uses severity-based decision logic to determine if IP should be blocked.
   - Sends detection and block requests to the NGFW control API.

The goal is to provide comprehensive coverage for both file-based
malware detection (via DPI file extraction) and attack detection (via Suricata
signature alerts for SQLi, XSS, command injection, etc.).

Usage (on VM1):

    python3 suri_clam_processor.py

Environment variables (all optional):
    SURICATA_EVE_LOG         - EVE JSON log path (default: /var/log/suricata/eve.json)
    SURICATA_FILESTORE_DIR    - Filestore base dir (default: /var/log/suricata/filestore)
    NGFW_API_URL             - NGFW control API base URL (default: http://127.0.0.1:5001)
    CLAMD_UNIX_SOCKET        - ClamAV Unix socket (default: /var/run/clamav/clamd.ctl)
    CLAMD_HOST              - ClamAV TCP host (default: 127.0.0.1)
    CLAMD_PORT              - ClamAV TCP port (default: 3310)
    SURICATA_FILE_WAIT_INTERVAL  - Seconds between file existence checks (default: 0.5)
    SURICATA_FILE_WAIT_TIMEOUT  - Max seconds to wait for file (default: 10)
    SURICATA_TAIL_SLEEP       - Seconds between tail iterations (default: 0.5)
    SURICATA_SCAN_CACHE_TTL - Seconds to cache scanned hashes (default: 3600)
    ALERT_CACHE_TTL          - Seconds to deduplicate alerts (default: 5)
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class Settings:
    """Runtime configuration for the Suricata/ClamAV processor."""

    # Suricata EVE log file (JSON, one event per line)
    eve_log_path: str = os.environ.get("SURI_EVE_LOG", "/var/log/suricata/eve.json")

    # Suricata filestore base directory (version 2 filestore layout)
    filestore_dir: str = os.environ.get("SURI_FILESTORE_DIR", "/var/log/suricata/filestore")

    # NGFW decision engine API base URL (this script runs on VM1)
    api_base_url: str = os.environ.get("NGFW_API_URL", "http://127.0.0.1:5001")

    # ClamAV clamd socket (Unix domain socket is preferred)
    clamd_unix_socket: str = os.environ.get("CLAMD_UNIX_SOCKET", "/var/run/clamav/clamd.ctl")

    # Optional TCP fallback for clamd
    clamd_host: str = os.environ.get("CLAMD_HOST", "127.0.0.1")
    clamd_port: int = int(os.environ.get("CLAMD_PORT", "3310"))

    # How long to wait between file existence checks (seconds)
    file_wait_interval: float = float(os.environ.get("SURI_FILE_WAIT_INTERVAL", "0.5"))

    file_wait_timeout: float = float(os.environ.get("SURI_FILE_WAIT_TIMEOUT", "10"))

    # Sleep between tail iterations (seconds)
    tail_sleep: float = float(os.environ.get("SURI_TAIL_SLEEP", "0.5"))

    # Simple rate-limit / dedup: how long to remember scanned hashes (seconds)
    # Changed from 3600 to 7 - was caching too long, preventing re-blocks
    scan_cache_ttl: float = float(os.environ.get("SURI_SCAN_CACHE_TTL", "7"))

    # Alert dedup: how long to remember alert (src_ip, sid) pairs (seconds)
    alert_cache_ttl: float = float(os.environ.get("ALERT_CACHE_TTL", "5"))


settings = Settings()


# ---------------------------------------------------------------------------
# Utility: simple logger
# ---------------------------------------------------------------------------


class SimpleLogger:
    def info(self, msg: str) -> None:
        sys.stdout.write(f"[INFO] {msg}\n")
        sys.stdout.flush()

    def warning(self, msg: str) -> None:
        sys.stdout.write(f"[WARN] {msg}\n")
        sys.stdout.flush()

    def error(self, msg: str) -> None:
        sys.stderr.write(f"[ERROR] {msg}\n")
        sys.stderr.flush()


log = SimpleLogger()


# ---------------------------------------------------------------------------
# ClamAV client (minimal, no external dependency)
# ---------------------------------------------------------------------------


class ClamAVClient:
    """Very small clamd client supporting INSTREAM via Unix or TCP socket.

    Uses the INSTREAM protocol so we can send file content directly.
    """

    def __init__(self, unix_socket: str, host: str, port: int) -> None:
        self.unix_socket = unix_socket
        self.host = host
        self.port = port

    def _connect_unix(self) -> Optional[socket.socket]:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.unix_socket)
            return s
        except OSError:
            return None

    def _connect_tcp(self) -> Optional[socket.socket]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, self.port))
            return s
        except OSError:
            return None

    def scan_file(self, path: str) -> Dict[str, Any]:
        """Scan a file with clamd.

        Returns a dict of the form:
            {"status": "clean" | "infected" | "error", "signature": str | None, "raw": str}
        """
        if not os.path.exists(path):
            return {"status": "error", "signature": None, "raw": "file_not_found"}

        # Prefer Unix socket
        sock = self._connect_unix()
        if sock is None:
            sock = self._connect_tcp()
        if sock is None:
            return {"status": "error", "signature": None, "raw": "clamd_unreachable"}

        try:
            # INSTREAM command
            sock.sendall(b"zINSTREAM\0")
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    size = len(chunk).to_bytes(4, byteorder="big")
                    sock.sendall(size + chunk)
            # Send zero-length chunk to terminate
            sock.sendall((0).to_bytes(4, byteorder="big"))

            # Read response
            data = b""
            while True:
                part = sock.recv(4096)
                if not part:
                    break
                data += part
            raw = data.decode(errors="replace").strip()
        finally:
            try:
                sock.close()
            except Exception:
                pass

        # Typical clamd response: "stream: OK" or "stream: Eicar-Test-Signature FOUND"
        status = "error"
        signature: Optional[str] = None
        if "OK" in raw and "FOUND" not in raw:
            status = "clean"
        elif "FOUND" in raw:
            status = "infected"
            # Extract signature between ": " and " FOUND"
            try:
                if ": " in raw:
                    sig_part = raw.split(": ", 1)[1]
                else:
                    sig_part = raw
                signature = sig_part.split(" FOUND", 1)[0].strip()
            except Exception:
                signature = None
        else:
            status = "error"

        return {"status": status, "signature": signature, "raw": raw}


clamav_client = ClamAVClient(
    unix_socket=settings.clamd_unix_socket,
    host=settings.clamd_host,
    port=settings.clamd_port,
)


# ---------------------------------------------------------------------------
# Alert cache (deduplication)
# ---------------------------------------------------------------------------


class AlertCache:
    """Prevent blocking the same IP multiple times for the same alert."""

    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._entries: Dict[str, float] = {}

    def cleanup(self) -> None:
        now = time.time()
        expired: Set[str] = {k for k, v in self._entries.items() if now - v > self.ttl}
        for k in expired:
            self._entries.pop(k, None)

    def is_duplicate(self, src_ip: str, sid: int) -> bool:
        self.cleanup()
        key = f"{src_ip}:{sid}"
        if key in self._entries:
            return True
        self._entries[key] = time.time()
        return False


alert_cache = AlertCache(ttl=settings.alert_cache_ttl)


# ---------------------------------------------------------------------------
# IP Whitelist (never block these)
# ---------------------------------------------------------------------------

import socket


def get_local_ips() -> set:
    """Dynamically get all IP addresses of this machine (VM1)."""
    ips = set()
    # Use socket.gethostbyname_ex as primary (more reliable)
    try:
        hostname = socket.gethostname()
        _, _, ipaddrlist = socket.gethostbyname_ex(hostname)
        ips.update(ipaddrlist)
    except Exception:
        pass

    # Try netifaces as additional source (if available)
    try:
        import netifaces
        ifaces = netifaces.interfaces()
        for iface in ifaces:
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr.get('addr')
                    if ip:
                        ips.add(ip)
    except Exception:
        pass  # netifaces not available, already have socket results

    return ips


# Static whitelist: servers that should NEVER be blocked
STATIC_WHITELIST = {
    "127.0.0.1",      # Localhost
    "10.0.0.5",      # VM2 web server (the protected server)
}


def is_ip_whitelisted(ip: str) -> bool:
    """Check if an IP is whitelisted (server, infrastructure, etc.).

    Uses dynamic detection of local IPs + static whitelist.
    """
    # Check static whitelist first (VM2, localhost)
    if ip in STATIC_WHITELIST:
        return True

    # Dynamically check if this IP belongs to VM1 (the gateway itself)
    # This handles the bridged adapter IP changes (192.168.1.8 → .10 → .3 → ...)
    local_ips = get_local_ips()
    if ip in local_ips:
        return True

    return False


def is_server_ip(ip: str) -> bool:
    """Check if the IP belongs to a known server (not an attacker)."""
    # Only whitelist VM2 (the web server we're protecting)
    # Do NOT whitelist VM1's bridged IP (attackers could be in 192.168.1.x too!)
    return ip in {
        "10.0.0.5",      # VM2 web server
        "127.0.0.1",      # Localhost
    }


def is_ip_whitelisted(ip: str) -> bool:
    """Check if an IP is whitelisted (server, infrastructure, etc.).

    Uses dynamic detection of local IPs + static whitelist.
    """
    # Check static whitelist first (VM2, localhost)
    if ip in STATIC_WHITELIST:
        return True

    # Dynamically check if this IP belongs to VM1 (the gateway itself)
    # This handles the bridged adapter IP changes (192.168.1.8 → .10 → .3 → ...)
    local_ips = get_local_ips()
    if ip in local_ips:
        return True

    return False


def is_server_ip(ip: str) -> bool:
    """Check if the IP belongs to a known server (not an attacker)."""
    # Only whitelist VM2 (the web server we're protecting)
    # Do NOT whitelist VM1's bridged IP (attackers could be in 192.168.1.x too!)
    return ip in {
        "10.0.0.5",      # VM2 web server
        "127.0.0.1",      # Localhost
    }

# Private IP ranges that should typically not be blocked (broad check)
PRIVATE_IP_PREFIXES = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.3")


def is_ip_whitelisted(ip: str) -> bool:
    """Check if an IP is whitelisted (server, infrastructure, etc.).

    Uses dynamic detection of local IPs + static whitelist.
    """
    # Check static whitelist first (VM2, localhost)
    if ip in STATIC_WHITELIST:
        return True

    # Dynamically check if this IP belongs to VM1 (the gateway itself)
    # This handles the bridged adapter IP changes (192.168.1.8 → .10 → .3 → ...)
    local_ips = get_local_ips()
    if ip in local_ips:
        return True

    return False


def is_server_ip(ip: str) -> bool:
    """Check if the IP belongs to a known server (not an attacker)."""
    return ip in {
        "10.0.0.5",      # VM2 web server
        "192.168.1.70",   # VM1 bridged
    }


# ---------------------------------------------------------------------------
# Severity to Block Action Mapping
# ---------------------------------------------------------------------------


def severity_to_block_action(severity: int, sid: int, category: str = "", signature: str = "") -> tuple[bool, Optional[str]]:
    """Determine whether to block based on Suricata alert severity and SID.

    Suricata severity levels (from classification.config):
        1 = High (critical attacks)
        2 = Medium-High
        3 = Medium (informational)
        4 = Low (benign anomalies)

    Returns (should_block, ttl_string_or_None).
    """
    # Never block Suricata internal protocol anomalies (stream errors, etc.)
    if sid >= 2210000:
        return False, None

    # NEVER block these categories (informational only, not attacks)
    if category in {"Not Suspicious Traffic", "Unknown Traffic", "Informational"}:
        return False, None

    # These are informational alerts, not actual attacks (e.g., Notion.so, Cloudflare, etc.)
    if signature.startswith("ET INFO"):
        return False, None

    if 2013500 <= sid <= 2013600:
        return False, None

    # SID 2014xxx, 2015xxx, 2016xxx, 2017xxx, 2018xxx are mostly INFO
    if sid >= 2014000 and sid <= 2019999:
        if "exploit" not in category.lower() and "attack" not in category.lower():
            return False, None

    # Block high and medium-high severity alerts (severity 1-2)
    if severity <= 2:
        return True, "24h"  # Block for 24 hours

    # For medium severity (3), only block if it's a known attack category
    if severity == 3:
        if sid >= 1000000:
            return True, "1h"

       
        if "web-application-attack" in category.lower():
            return True, "1h"

        if "exploit" in category.lower():
            return True, "1h"

        return False, None

    # Low severity (4) or anything else: log only, don't block
    return False, None


# ---------------------------------------------------------------------------
# Scan cache (file scanning dedup)
# ---------------------------------------------------------------------------


@dataclass
class ScanCacheEntry:
    first_seen: float
    status: str
    signature: Optional[str]


class ScanCache:
    """In-memory cache of scanned file hashes to avoid rescanning."""

    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._entries: Dict[str, ScanCacheEntry] = {}

    def cleanup(self) -> None:
        now = time.time()
        expired: Set[str] = {h for h, entry in self._entries.items() if now - entry.first_seen > self.ttl}
        for h in expired:
            self._entries.pop(h, None)

    def has(self, file_hash: str) -> bool:
        self.cleanup()
        return file_hash in self._entries

    def add(self, file_hash: str, status: str, signature: Optional[str]) -> None:
        self._entries[file_hash] = ScanCacheEntry(first_seen=time.time(), status=status, signature=signature)


scan_cache = ScanCache(ttl=settings.scan_cache_ttl)


# ---------------------------------------------------------------------------
# EVE log tailing
# ---------------------------------------------------------------------------


def tail_eve(path: str):
    """Generator that yields new JSON lines appended to the EVE log.

    Handles Suricata restarts and log rotation by detecting file changes.
    """
    f = None
    last_inode = None
    last_size = 0
    restart_delay = 2

    while True:
        try:
            # Check if file exists
            if not os.path.exists(path):
                log.warning(f"EVE log not found, waiting... ({path})")
                time.sleep(restart_delay)
                continue

            # Get current file stats
            stat = os.stat(path)
            current_inode = stat.st_ino
            current_size = stat.st_size

            # Open or reopen if file changed (rotation or restart)
            if f is None or current_inode != last_inode:
                if f:
                    f.close()
                log.info(f"Opening EVE log: {path} (inode={current_inode}, size={current_size})")
                f = open(path, "r", encoding="utf-8")
                last_inode = current_inode
                last_size = current_size
                # Seek to end to only read new events
                f.seek(0, os.SEEK_END)

            # Handle file truncation (suricata restart often resets log)
            if current_size < last_size:
                log.info("EVE log truncated (Suricata restart detected), seeking to new end")
                f.seek(0, os.SEEK_END)
                last_size = current_size

            # Read new lines
            line = f.readline()
            if not line:
                # Update size for next iteration
                try:
                    last_size = os.path.getsize(path)
                except:
                    pass
                time.sleep(settings.tail_sleep)
                continue

            last_size = f.tell()
            line = line.strip()
            if not line:
                continue
            yield line

        except Exception as e:
            log.error(f"Error in tail_eve: {e}")
            if f:
                f.close()
                f = None
            time.sleep(restart_delay)
            continue


# ---------------------------------------------------------------------------
# Fileinfo event helpers
# ---------------------------------------------------------------------------


def find_filestore_path(fileinfo: Dict[str, Any]) -> Optional[str]:
    """Compute the expected filestore path from a Suricata fileinfo event.

    For filestore version 2, files are stored as:
        /var/log/suricata/files/<first2>/<sha256>

    where <sha256> is the file hash.
    """
    sha256 = fileinfo.get("sha256")
    if not sha256:
        return None

    subdir = sha256[:2]
    candidate = os.path.join(settings.filestore_dir, subdir, sha256)
    return candidate


def wait_for_file(path: str) -> bool:
    """Wait for Suricata to finish writing the file up to a timeout."""
    deadline = time.time() + settings.file_wait_timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(settings.file_wait_interval)
    return False


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def send_detection_to_api(
    src_ip: Optional[str],
    dest_ip: Optional[str],
    event: Dict[str, Any],
    action: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Send detection log to the NGFW control API."""
    base = settings.api_base_url.rstrip("/")

    log_data = {
        "source": "decision_engine",
        "action": action,
        "src_ip": src_ip,
        "dest_ip": dest_ip,
    }

    if extra_data:
        log_data.update(extra_data)

    if action.startswith("alert_"):
        alert_name = action.replace("alert_", "")
        if alert_name.startswith("CUSTOM "):
            alert_name = alert_name[7:]  # Remove "CUSTOM " prefix
        log_data["alert_name"] = alert_name
        alert = event.get("alert", {})
        if alert:
            log_data["category"] = alert.get("category", "unknown")
            log_data["signature"] = alert.get("signature", "unknown")
            log_data["sid"] = alert.get("signature_id", 0)
            log_data["severity"] = alert.get("severity", 3)

    if action == "malware_file_detected":
        fileinfo = event.get("fileinfo", {})
        log_data["filename"] = fileinfo.get("filename", "unknown")
        log_data["file_size"] = fileinfo.get("size", 0)
        log_data["file_magic"] = fileinfo.get("magic", "unknown")

    try:
        r = requests.post(f"{base}/api/log_detection", json=log_data, timeout=5)
        r.raise_for_status()
        log.info(
            f"Logged detection: action={action}, src_ip={src_ip} "
            f"to decision engine (log_id={r.json().get('log_id')})"
        )
    except Exception as exc:
        log.error(f"Failed to post detection to decision engine: {exc}")


# ---------------------------------------------------------------------------
# Alert event handler (NEW)
# ---------------------------------------------------------------------------


def process_alert_event(event: Dict[str, Any]) -> None:
    """Handle Suricata alert events and trigger IP blocking based on severity."""

    alert = event.get("alert", {})
    if not alert:
        return

    severity = alert.get("severity", 3)  # Default to medium (3)
    signature = alert.get("signature", "unknown")
    sid = alert.get("signature_id", 0)
    category = alert.get("category", "unknown")

    # Extract source IP (VM1 sees real IPs directly - no NAT correlation needed)
    src_ip = event.get("src_ip")
    dest_ip = event.get("dest_ip")

    # CRITICAL: If src_ip is a server, this is likely a response → ignore
    if src_ip and is_server_ip(src_ip):
        log.info(f"Ignoring alert: src_ip={src_ip} is a server (not attacker)")
        return

    if not src_ip:
        log.warning(f"Alert without source IP, cannot block: sid={sid}, sig={signature}")
        return

    # Check whitelist FIRST (before any processing)
    if is_ip_whitelisted(src_ip):
        log.info(f"Skipping whitelisted IP: src_ip={src_ip}, sid={sid}")
        return

    # Check alert dedup cache
    if alert_cache.is_duplicate(src_ip, sid):
        log.info(f"Duplicate alert skipped: src_ip={src_ip}, sid={sid}")
        return

    # Severity-based decision logic (now includes category and signature check)
    block, ttl = severity_to_block_action(severity, sid, category, signature)

    if not block:
        log.info(
            f"Alert below blocking threshold: sid={sid}, severity={severity}, "
            f"src={src_ip}, sig={signature}"
        )
        return

    # Deduplicate alert logging - only log once per IP within 60 seconds
    alert_log_key = f"{src_ip}:block"
    current_time = time.time()
    if hasattr(process_alert_event, '_last_log_time'):
        last_time = getattr(process_alert_event, '_last_log_time', {})
        if alert_log_key in last_time and (current_time - last_time[alert_log_key]) < 60:
            log.info(f"Skipping duplicate alert log for src_ip={src_ip} (logged within 60s)")
        else:
            last_time[alert_log_key] = current_time
            setattr(process_alert_event, '_last_log_time', last_time)
            send_detection_to_api(
                src_ip=src_ip,
                dest_ip=dest_ip,
                event=event,
                action=f"alert_{signature}",
            )
    else:
        setattr(process_alert_event, '_last_log_time', {alert_log_key: current_time})
        send_detection_to_api(
            src_ip=src_ip,
            dest_ip=dest_ip,
            event=event,
            action=f"alert_{signature}",
        )

    # Block the IP with the determined TTL (for non-ML forwarded attacks)
    block_payload = {
        "ip": src_ip,
        "reason": signature,
        "signature": signature,
        "ttl": ttl,
    }

    try:
        r2 = requests.post(
            f"{settings.api_base_url}/api/block_ip",
            json=block_payload,
            timeout=5,
        )
        if r2.status_code == 200:
            body = r2.json()
            log.info(
                f"Blocked src_ip={src_ip} for alert sid={sid}, "
                f"success={body.get('success')}, ttl={ttl}, db_id={body.get('db_id')}"
            )
        else:
            log.error(f"block_ip returned status {r2.status_code} for alert sid={sid}: {r2.text}")
    except Exception as exc:
        log.error(f"Failed to block_ip for alert sid={sid}, src_ip={src_ip}: {exc}")


# ---------------------------------------------------------------------------
# Fileinfo event handler (existing, updated)
# ---------------------------------------------------------------------------


def process_fileinfo_event(event: Dict[str, Any]) -> None:
    """Handle Suricata fileinfo events (file extraction + ClamAV scan)."""
    fileinfo = event.get("fileinfo", {})
    if not isinstance(fileinfo, dict):
        return

    file_hash = fileinfo.get("sha256")
    if not file_hash:
        return

    if scan_cache.has(file_hash):
        return

    filestore_path = find_filestore_path(fileinfo)
    if not filestore_path:
        return

    if not wait_for_file(filestore_path):
        log.warning(f"File not found in filestore within timeout: {filestore_path}")
        return

    log.info(f"Scanning filestore file: sha256={file_hash}, path={filestore_path}")
    result = clamav_client.scan_file(filestore_path)
    status = result.get("status")
    signature = result.get("signature")
    raw = result.get("raw")

    scan_cache.add(file_hash, status=status or "error", signature=signature)

    if status == "infected":
        log.warning(f"Malware detected by ClamAV for sha256={file_hash}: signature={signature}, raw={raw}")
        src_ip = event.get("src_ip")
        if not src_ip:
            log.warning(f"Fileinfo event without source IP, cannot block: file_hash={file_hash}")
            return
        dest_ip = event.get("dest_ip")

        # Log the detection for malware
        send_detection_to_api(
            src_ip=src_ip,
            dest_ip=dest_ip,
            event=event,
            action="malware_file_detected",
            extra_data={"file_hash": file_hash, "clamav_signature": signature},
        )

        # Store malware alert in database
        try:
            fileinfo = event.get("fileinfo", {})
            filename = fileinfo.get("filename", "unknown")
            r = requests.post(
                f"{settings.api_base_url}/api/malware_alert",
                json={
                    "filename": filename,
                    "file_hash": file_hash,
                    "signature": signature,
                    "source_ip": src_ip,
                    "action": "blocked",
                    "confidence": 1.0,
                },
                timeout=5,
            )
            if r.status_code == 200:
                log.info(f"Stored malware alert for {filename}, sig={signature}")
        except Exception as e:
            log.error(f"Failed to store malware alert: {e}")

        # Block the IP immediately if not whitelisted
        if src_ip and not is_ip_whitelisted(src_ip):
            block_payload = {
                "ip": src_ip,
                "reason": "Malware Signature Detected",
                "signature": signature,
                "ttl": "24h",
            }
            try:
                r = requests.post(
                    f"{settings.api_base_url}/api/block_ip",
                    json=block_payload,
                    timeout=5,
                )
                if r.status_code == 200:
                    body = r.json()
                    log.info(
                        f"Blocked src_ip={src_ip} for malware {signature}, "
                        f"success={body.get('success')}, ttl=24h, db_id={body.get('db_id')}"
                    )
                else:
                    log.error(f"block_ip returned status {r.status_code} for malware: {r.text}")
            except Exception as exc:
                log.error(f"Failed to block_ip for malware {signature}, src_ip={src_ip}: {exc}")
        else:
            log.info(f"Skipping block for whitelisted IP: src_ip={src_ip}")
    elif status == "clean":
        log.info(f"File clean according to ClamAV: sha256={file_hash}")
    else:
        log.error(f"Error scanning file sha256={file_hash}: raw={raw}")


# ---------------------------------------------------------------------------
# Main event dispatcher
# ---------------------------------------------------------------------------


def process_eve_event(event: Dict[str, Any]) -> None:
    """Handle a single EVE JSON event.

    We handle:
    - event_type == 'fileinfo' → ClamAV scan → block if infected (existing)
    - event_type == 'alert' → severity check → block if threshold met (new)
    - http/tls events that contain a 'fileinfo' object (existing)
    """
    event_type = event.get("event_type")

    # --- Fileinfo events (existing behavior) ---
    if event_type == "fileinfo":
        process_fileinfo_event(event)
        return

    # Some HTTP events may embed fileinfo
    if event_type in {"http", "tls"} and "fileinfo" in event:
        process_fileinfo_event(event)
        return

    # --- Alert events (NEW behavior) ---
    if event_type == "alert":
        process_alert_event(event)
        return

    # Ignore all other event types
    return


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    log.info("Starting Suricata → ClamAV processor (with alert handling)")
    log.info(f"Using EVE log: {settings.eve_log_path}")
    log.info(f"Using filestore dir: {settings.filestore_dir}")
    log.info(f"NGFW API base URL: {settings.api_base_url}")
    log.info(f"ClamAV Unix socket: {settings.clamd_unix_socket}, TCP: {settings.clamd_host}:{settings.clamd_port}")
    log.info(f"Scan cache TTL: {settings.scan_cache_ttl}s, Alert cache TTL: {settings.alert_cache_ttl}s")

    if not os.path.exists(settings.eve_log_path):
        log.error(f"EVE log file does not exist: {settings.eve_log_path}")
        sys.exit(1)

    try:
        for line in tail_eve(settings.eve_log_path):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue
            try:
                process_eve_event(event)
            except Exception as exc:
                log.error(f"Error processing EVE event: {exc}")
    except KeyboardInterrupt:
        log.info("Interrupted by user, exiting.")


if __name__ == "__main__":
    main()
