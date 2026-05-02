from typing import Any, Dict
import json

from flask import Flask, request, jsonify

from config import config
from logger import get_app_logger, get_security_logger
from database import (
    init_db,
    add_block,
    get_blocks,
    log_event,
    remove_block,
)
from firewall_service import add_block as fw_add_block, remove_block as fw_remove_block

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

app_logger = get_app_logger()
security_logger = get_security_logger()

# Initialize DB at import/startup (Flask 3 removed before_first_request)
try:
    init_db()
    app_logger.info("NGFW control DB initialized")
except Exception as exc:  # noqa: BLE001
    app_logger.error(f"Failed to initialize DB at startup: {exc}")


def _normalize_ttl(ttl_val: Any) -> str:
    """Normalize TTL to string form accepted by nft (e.g. '1h', '300s')."""
    if ttl_val is None:
        return config.DEFAULT_TTL
    if isinstance(ttl_val, (int, float)):
        return f"{int(ttl_val)}s"
    return str(ttl_val)


@app.route("/api/block_ip", methods=["POST"])
def api_block_ip():
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    ip = data.get("ip")
    reason = data.get("reason", "unknown")
    ttl_in = data.get("ttl")
    signature = data.get("signature")

    if not ip:
        return jsonify({"success": False, "error": "ip is required"}), 400

    ttl_str = _normalize_ttl(ttl_in)

    fw_ok, fw_msg = fw_add_block(ip, ttl_str)
    if not fw_ok:
        app_logger.error(f"Failed to add nftables block for {ip}: {fw_msg}")
        return jsonify({"success": False, "error": fw_msg}), 500

    # For DB, store TTL as seconds when possible (simple heuristic)
    ttl_seconds = None
    if isinstance(ttl_in, (int, float)):
        ttl_seconds = int(ttl_in)

    blk = add_block(ip=ip, reason=reason, ttl_seconds=ttl_seconds)

    event_payload = {
        "ip": ip,
        "reason": reason,
        "ttl": ttl_str,
        "signature": signature,
    }
    log_event("api", "block_ip", json.dumps(event_payload))
    security_logger.warning(
        f"Blocked IP {ip} via API", extra={"ip": ip, "reason": reason, "signature": signature}
    )

    return jsonify({"success": True, "blocked_ip": ip, "ttl": ttl_str, "db_id": blk.id})


@app.route("/api/unblock_ip", methods=["POST"])
def api_unblock_ip():
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    ip = data.get("ip")

    if not ip:
        return jsonify({"success": False, "error": "ip is required"}), 400

    fw_ok, fw_msg = fw_remove_block(ip)
    if not fw_ok:
        app_logger.error(f"Failed to remove nftables block for {ip}: {fw_msg}")
        return jsonify({"success": False, "error": fw_msg}), 500

    removed = remove_block(ip)
    log_event("api", "unblock_ip", json.dumps({"ip": ip, "rows_deleted": removed}))

    return jsonify({"success": True, "unblocked_ip": ip, "rows_deleted": removed})


@app.route("/api/log_detection", methods=["POST"])
def api_log_detection():
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    source = data.get("source") or "unknown"
    event = data.get("event") or "detection"
    details = data.get("data")

    try:
        serialized = json.dumps(details) if details is not None else None
    except (TypeError, ValueError):
        serialized = str(details)

    entry = log_event(source, event, serialized)
    security_logger.info(
        f"Detection log from {source}: {event}", extra={"source": source, "event": event}
    )

    return jsonify({"success": True, "log_id": entry.id})


@app.route("/api/list_blocks", methods=["GET"])
def api_list_blocks():
    rows = get_blocks()
    payload = [
        {
            "id": r.id,
            "ip": r.ip,
            "reason": r.reason,
            "timestamp": r.timestamp,
            "ttl": r.ttl,
        }
        for r in rows
    ]
    return jsonify({"success": True, "blocks": payload})


@app.route("/api/health", methods=["GET"])
def api_health():
    # Simple health probe: if we can run a quick DB init without error, we consider it ok
    try:
        init_db()
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001
        app_logger.error(f"DB health check failed: {exc}")
        db_status = "error"

    return jsonify({
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
    })


if __name__ == "__main__":
    init_db()
    app_logger.info(
        f"Starting NGFW control API on {config.BIND_HOST}:{config.BIND_PORT}"
    )
    app.run(host=config.BIND_HOST, port=config.BIND_PORT)
