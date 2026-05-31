from typing import Any, Dict, Optional
import json
import subprocess
import re
import csv
import io
from datetime import datetime

from flask import Flask, request, jsonify, Response
try:
    from flask_cors import CORS
except ImportError:
    CORS = None, Response
import time

from config import config
from logger import get_app_logger, get_security_logger
from database import (
    init_db,
    add_block,
    get_blocks,
    log_event,
    remove_block,
    remove_all_blocks,
    get_logs,
    get_logs_today_count,
    get_active_threats_count,
    get_ml_predictions,
    get_malware_alerts,
    add_ml_prediction,
    add_malware_alert,
    clear_malware_alerts,
)
from firewall_service import add_block as fw_add_block, remove_block as fw_remove_block, clear_all_blocks as fw_clear_all_blocks

app = Flask(__name__)
if CORS:
    CORS(app)
app.config["SECRET_KEY"] = config.SECRET_KEY

app_logger = get_app_logger()
security_logger = get_security_logger()

try:
    init_db()
    app_logger.info("NGFW control DB initialized")
except Exception as exc:
    app_logger.error(f"Failed to initialize DB at startup: {exc}")


def _normalize_ttl(ttl_val: Any) -> str:
    if ttl_val is None:
        return config.DEFAULT_TTL
    if isinstance(ttl_val, (int, float)):
        return f"{int(ttl_val)}s"
    return str(ttl_val)


def _run_command(cmd: list) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


# ─── Block Management ───────────────────────────────────────────────────────

def _is_ip_blocked(ip: str) -> bool:
    """Check if IP is already blocked in nftables."""
    ok, output = _run_command(["nft", "list", "set", "inet", "firewall", "blocked_ips"])
    if ok:
        import re
        ip_pattern = r'\b' + re.escape(ip) + r'\b'
        if re.search(ip_pattern, output):
            return True
    return False


@app.route("/api/block_ip", methods=["POST"])
def api_block_ip():
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    ip = data.get("ip")
    reason = data.get("reason", "unknown")
    ttl_in = data.get("ttl")
    signature = data.get("signature")

    if not ip:
        return jsonify({"success": False, "error": "ip is required"}), 400

    # Check if already blocked (in nftables or database)
    if _is_ip_blocked(ip):
        app_logger.info(f"IP {ip} already blocked in nftables, skipping")
        return jsonify({"success": True, "blocked_ip": ip, "skipped": True, "reason": "already_blocked"})

    # Also check database
    from database import get_blocks
    existing_blocks = get_blocks()
    if any(b.ip == ip for b in existing_blocks):
        app_logger.info(f"IP {ip} already in database, skipping")
        return jsonify({"success": True, "blocked_ip": ip, "skipped": True, "reason": "already_blocked"})

    ttl_str = _normalize_ttl(ttl_in)

    # Convert TTL to seconds for database storage
    ttl_seconds = None
    if ttl_str:
        ttl_seconds_map = {
            "1h": 3600,
            "6h": 21600,
            "24h": 86400,
            "7d": 604800,
            "permanent": None,
        }
        ttl_seconds = ttl_seconds_map.get(ttl_str)

    fw_ok, fw_msg = fw_add_block(ip, ttl_str)
    if not fw_ok:
        app_logger.error(f"Failed to add nftables block for {ip}: {fw_msg}")
        return jsonify({"success": False, "error": fw_msg}), 500

    blk = add_block(ip=ip, reason=reason, ttl_seconds=ttl_seconds)

    source = data.get("source", "decision_engine")
    log_payload = {
        "source": source,
        "action": "block_ip",
        "ip": ip,
        "reason": reason,
        "ttl": ttl_str,
        "signature": signature,
    }
    log_event(json.dumps(log_payload))
    security_logger.warning(f"Blocked IP {ip} via API", extra={"ip": ip, "reason": reason, "signature": signature})

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
    log_payload = {
        "source": "Admin",
        "action": "unblock_ip",
        "ip": ip,
        "rows_deleted": removed,
    }
    log_event(json.dumps(log_payload))

    return jsonify({"success": True, "unblocked_ip": ip, "rows_deleted": removed})


@app.route("/api/clear_all_blocks", methods=["POST"])
def api_clear_all_blocks():
    fw_ok, fw_msg = fw_clear_all_blocks()
    if not fw_ok:
        app_logger.error(f"Failed to flush nftables blocked set: {fw_msg}")
        return jsonify({"success": False, "error": fw_msg}), 500

    removed = remove_all_blocks()
    log_payload = {
        "source": "Admin",
        "action": "clear_all_blocks",
        "rows_deleted": removed,
    }
    log_event(json.dumps(log_payload))

    return jsonify({"success": True, "rows_deleted": removed})


@app.route("/api/list_blocks", methods=["GET"])
def api_list_blocks():
    rows = get_blocks()
    payload = [{"id": r.id, "ip": r.ip, "reason": r.reason, "timestamp": r.timestamp, "ttl": r.ttl} for r in rows]
    return jsonify({"success": True, "blocks": payload, "total": len(payload)})


# ─── Detection Logs ─────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def api_logs():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    search = request.args.get("search", None)

    if limit > 200:
        limit = 200

    logs, total = get_logs(limit=limit, offset=offset, search=search)

    payload = []
    for log in logs:
        try:
            data_obj = json.loads(log.data)
        except:
            data_obj = {"raw": log.data}

        payload.append({
            "id": log.id,
            "timestamp": log.timestamp,
            "data": data_obj,
        })

    return jsonify({
        "success": True,
        "logs": payload,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


# ─── ML Predictions ─────────────────────────────────────────────────────────

@app.route("/api/ml_predictions", methods=["GET"])
def api_ml_predictions():
    limit = request.args.get("limit", 100, type=int)

    if limit > 200:
        limit = 200

    predictions = get_ml_predictions(limit=limit)

    payload = []
    for pred in predictions:
        payload.append({
            "id": pred.id,
            "timestamp": pred.timestamp,
            "attack_type": pred.attack_type or "Unknown",
            "source_ip": pred.source_ip or "-",
            "dest_ip": pred.dest_ip or "-",
            "confidence": pred.confidence or 0.0,
            "ensemble_score": pred.ensemble_score or 0.0,
            "models": {
                "rf": pred.rf_score or 0.0,
                "xgb": pred.xgb_score or 0.0,
                "decision_tree": pred.decision_tree_score or 0.0,
                "logistic_regression": pred.logistic_regression_score or 0.0,
                "catboost": pred.catboost_score or 0.0,
            },
            "action": pred.action or "detected",
        })

    return jsonify({"success": True, "predictions": payload, "total": len(payload)})


@app.route("/api/ml_predictions", methods=["POST"])
def api_add_ml_prediction():
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    try:
        features = data.get("features")
        pred = add_ml_prediction(
            attack_type=data.get("attack_type", "Unknown"),
            source_ip=data.get("source_ip"),
            dest_ip=data.get("dest_ip"),
            confidence=data.get("confidence", 0.0),
            ensemble_score=data.get("ensemble_score", 0.0),
            rf_score=data.get("rf_score", 0.0),
            xgb_score=data.get("xgb_score", 0.0),
            action=data.get("action", "detected"),
            decision_tree_score=data.get("decision_tree_score", 0.0),
            logistic_regression_score=data.get("logistic_regression_score", 0.0),
            catboost_score=data.get("catboost_score", 0.0),
            lgb_score=data.get("lgb_score", 0.0),
            mlp_score=data.get("mlp_score", 0.0),
            features=features,
        )
        return jsonify({"success": True, "id": pred.id})
    except Exception as exc:
        app_logger.error(f"Failed to store ML prediction: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


# ─── Malware Alerts ─────────────────────────────────────────────────────────

@app.route("/api/malware_alerts", methods=["GET"])
def api_malware_alerts():
    limit = request.args.get("limit", 100, type=int)
    search = request.args.get("search", None)

    if limit > 200:
        limit = 200

    alerts, total = get_malware_alerts(limit=limit, search=search)

    return jsonify({"success": True, "alerts": alerts, "total": total})


@app.route("/api/malware_alert", methods=["POST"])
def api_add_malware_alert():
    """Add a malware alert when malware is detected."""
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    filename = data.get("filename", "unknown")
    file_hash = data.get("file_hash", "")
    signature = data.get("signature", "unknown")
    source_ip = data.get("source_ip", "unknown")
    action = data.get("action", "blocked")
    confidence = data.get("confidence", 1.0)

    alert_id = add_malware_alert(
        filename=filename,
        file_hash=file_hash,
        signature=signature,
        source_ip=source_ip,
        action=action,
        confidence=confidence
    )

    if alert_id:
        return jsonify({"success": True, "alert_id": alert_id})
    else:
        return jsonify({"success": False, "error": "Failed to store alert"}), 500


@app.route("/api/malware_alerts/clear", methods=["POST"])
def api_clear_malware_alerts():
    """Clear all malware alerts."""
    count = clear_malware_alerts()
    return jsonify({"success": True, "deleted": count})


@app.route("/api/logs/clear", methods=["POST"])
def api_clear_logs():
    """Clear all logs from main table (not backup)."""
    from database import clear_logs
    count = clear_logs()
    return jsonify({"success": True, "deleted": count})


@app.route("/api/ml_predictions/clear", methods=["POST"])
def api_clear_ml_predictions():
    """Clear all ML predictions from main table (not backup)."""
    from database import clear_ml_predictions
    count = clear_ml_predictions()
    return jsonify({"success": True, "deleted": count})


# ─── System Stats ───────────────────────────────────────────────────────────

@app.route("/api/system/stats", methods=["GET"])
def api_system_stats():
    stats = {}

    ok, cpu_out = _run_command(["cat", "/proc/loadavg"])
    if ok:
        stats["cpu_load"] = float(cpu_out.split()[0]) if cpu_out else 0.0

    ok, mem_out = _run_command(["free", "-b"])
    if ok:
        lines = mem_out.split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 2:
                total_mem = int(parts[1])
                used_mem = int(parts[2])
                stats["memory_total"] = total_mem
                stats["memory_used"] = used_mem
                stats["memory_percent"] = round((used_mem / total_mem) * 100, 1) if total_mem > 0 else 0

    ok, uptime_out = _run_command(["uptime", "-s"])
    if ok and uptime_out:
        try:
            boot_time = datetime.strptime(uptime_out, "%Y-%m-%d %H:%M:%S")
            uptime_seconds = (datetime.now() - boot_time).total_seconds()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            stats["uptime"] = f"{days}d {hours}h"
            stats["uptime_seconds"] = int(uptime_seconds)
        except:
            stats["uptime"] = "unknown"

    stats["events_today"] = get_logs_today_count()
    stats["active_threats"] = get_active_threats_count()

    return jsonify({"success": True, "stats": stats})


# ─── Network Stats ─────────────────────────────────────────────────────────

@app.route("/api/network/stats", methods=["GET"])
def api_network_stats():
    stats = {}

    ok, out = _run_command(["cat", "/proc/net/dev"])
    if ok:
        lines = out.split("\n")
        packets_in = 0
        packets_out = 0
        bytes_in = 0
        bytes_out = 0

        for line in lines[2:]:
            if "enp" in line or "eth" in line or "lo" in line:
                parts = line.split()
                if len(parts) >= 17:
                    try:
                        bytes_in += int(parts[1])
                        packets_in += int(parts[2])
                        bytes_out += int(parts[9])
                        packets_out += int(parts[10])
                    except:
                        pass

        stats["packets_in"] = packets_in
        stats["packets_out"] = packets_out
        stats["bytes_in"] = bytes_in
        stats["bytes_out"] = bytes_out
        stats["connections"] = 0

    ok, conn_out = _run_command(["ss", "-tun"])
    if ok:
        stats["connections"] = len([l for l in conn_out.split("\n") if l.strip() and "State" not in l])

    ok, if_out = _run_command(["ip", "addr", "show"])
    if ok:
        interfaces = []
        current_if = {}

        for line in if_out.split("\n"):
            if re.match(r'^\d+:', line):
                if current_if:
                    interfaces.append(current_if)
                name = line.split(':')[1].strip()
                current_if = {"name": name, "ip": "", "status": "down", "mac": ""}
                if "state UP" in line or "state UNKNOWN" in line:
                    current_if["status"] = "up"
            elif "inet " in line and current_if:
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/\d+', line)
                if ip_match:
                    current_if["ip"] = ip_match.group(1)
            elif "link/ether" in line and current_if:
                mac_match = re.search(r'link/ether ([0-9a-f:]+)', line)
                if mac_match:
                    current_if["mac"] = mac_match.group(1)

        if current_if:
            interfaces.append(current_if)

        stats["interfaces"] = interfaces

    return jsonify({"success": True, "stats": stats})


# ─── Firewall Rules ─────────────────────────────────────────────────────────

@app.route("/api/firewall/rules", methods=["GET"])
def api_firewall_rules():
    rules = {"input": 0, "output": 0, "forward": 0}

    ok, out = _run_command(["nft", "list", "ruleset"])
    if ok:
        rules["input"] = len([l for l in out.split("\n") if "input" in l and "chain" not in l])
        rules["output"] = len([l for l in out.split("\n") if "output" in l and "chain" not in l])
        rules["forward"] = len([l for l in out.split("\n") if "forward" in l and "chain" not in l])

    return jsonify({"success": True, "rules": rules})


# ─── Service Control ─────────────────────────────────────────────────────────

@app.route("/api/service", methods=["POST"])
def api_service_control_json():
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    service_name = data.get("service")
    action = data.get("action")
    return _handle_service_control(service_name, action)


@app.route("/api/service/<service_name>/<action>", methods=["POST"])
def api_service_control(service_name: Optional[str], action: Optional[str]):
    return _handle_service_control(service_name, action)


def _handle_service_control(service_name: Optional[str], action: Optional[str]):
    if not service_name or not action:
        return jsonify({"success": False, "error": "service and action are required"}), 400

    if not service_name or not action:
        return jsonify({"success": False, "error": "service and action are required"}), 400

    # Prevent stopping/restarting the API itself via dashboard to avoid lockout
    protected_services = ["ngfw-control", "ngfw-control.service"]
    if service_name in protected_services and action in ["stop", "restart"]:
        return jsonify({"success": False, "error": "Cannot stop/restart ngfw-control service via API. Use CLI on server console."}), 403

    valid_actions = ["start", "stop", "restart", "status"]
    if action not in valid_actions:
        return jsonify({"success": False, "error": f"action must be one of: {valid_actions}"}), 400

    service_map = {
        "suricata": "suricata.service",
        "suricata-ips": "suricata-ips.service",
        "ngfw-control": "ngfw-control.service",
        "ngfw-ml": "ngfw-ml.service",
        "ngfw-flowmeter": "ngfw-flowmeter.service",
        "suri-clam": "suri-clam.service",
        "clamav-daemon": "clamav-daemon.service",
    }

    service_file = service_map.get(service_name)
    if not service_file:
        return jsonify({"success": False, "error": f"unknown service: {service_name}"}), 400

    import time

    ok, output = _run_command(["systemctl", action, service_file])

    # Wait for service to reach stable state (active/inactive/failed)
    if action in ["start", "restart"]:
        max_wait = 15
        for i in range(max_wait):
            time.sleep(1)
            check_ok, state = _run_command(["systemctl", "is-active", service_file])
            if check_ok and state.strip() in ["active", "inactive", "failed"]:
                break

    # For ML service, also wait for port to be ready
    if service_name == "ngfw-ml" and action in ["start", "restart"]:
        port = 5003
        for _ in range(15):
            time.sleep(1)
            check_ok, _ = _run_command(["sh", "-c", f"ss -tln | grep -q ':{port} '"])
            if check_ok:
                break

    # Manage nftables IPS chain when suricata-ips is toggled
    if service_name == "suricata-ips" and ok:
        if action in ["start", "restart"]:
            _run_command(["nft", "flush", "chain", "inet", "firewall", "IPS"])
            _run_command(["nft", "add", "rule", "inet", "firewall", "IPS", "iif", "enp0s3", "oif", "enp0s8", "counter", "queue", "to", "1"])
            _run_command(["nft", "add", "rule", "inet", "firewall", "IPS", "iif", "enp0s8", "oif", "enp0s3", "counter", "queue", "to", "1"])
        elif action == "stop":
            _run_command(["nft", "flush", "chain", "inet", "firewall", "IPS"])

    log_payload = {
        "source": "Admin",
        "action": f"service_{action}",
        "service": service_name,
        "service_file": service_file,
        "result": output if ok else f"Failed: {output}",
        "success": ok,
    }
    log_event(json.dumps(log_payload))

    return jsonify({
        "success": ok,
        "service": service_name,
        "action": action,
        "output": output if ok else f"Failed: {output}",
    })


@app.route("/api/services", methods=["GET"])
def api_services_list():
    services = [
        {"name": "suricata-ips", "displayName": "DPI Engine", "port": None},
        {"name": "ngfw-control", "displayName": "NGFW Control API", "port": 5001},
        {"name": "ngfw-ml", "displayName": "ML Inference Service", "port": 5003},
        {"name": "ngfw-flowmeter", "displayName": "Flow Meter", "port": None},
        {"name": "suri-clam", "displayName": "Suricata-ClamAV", "port": None},
        {"name": "clamav-daemon", "displayName": "ClamAV Daemon", "port": None},
    ]

    result = []
    for svc in services:
        ok, out = _run_command(["systemctl", "is-active", f"{svc['name']}.service"])
        state = out.strip()
        # Map all possible states: active, inactive, activating, deactivating, failed, unknown
        if ok and state == "active":
            status = "active"
        elif ok and state in ["inactive", "failed", "activating", "deactivating"]:
            status = "inactive"
        else:
            status = "inactive"
        result.append({**svc, "status": status})

    return jsonify({"success": True, "services": result})


# ─── Health Check ───────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def api_health():
    try:
        init_db()
        db_status = "ok"
    except Exception as exc:
        app_logger.error(f"DB health check failed: {exc}")
        db_status = "error"

    events_today = get_logs_today_count()
    active_threats = get_active_threats_count()
    blocks = get_blocks()

    return jsonify({
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "total_events_today": events_today,
        "active_threats": active_threats,
        "total_blocked_ips": len(blocks),
    })


# ─── SSE Stream ─────────────────────────────────────────────────────────────────

@app.route("/api/stream")
def api_stream():
    def generate():
        while True:
            try:
                blocks = get_blocks()
                blocks_payload = [{"id": r.id, "ip": r.ip, "reason": r.reason, "ttl": r.ttl, "timestamp": r.timestamp} for r in blocks]
                
                events_today = get_logs_today_count()
                active_threats = get_active_threats_count()
                
                ok, cpu_out = _run_command(["cat", "/proc/loadavg"])
                cpu_load = float(cpu_out.split()[0]) if ok and cpu_out else 0.0
                
                ok, mem_out = _run_command(["free", "-b"])
                memory_percent = 0.0
                if ok and mem_out:
                    lines = mem_out.split("\n")
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        if len(parts) >= 3:
                            total_mem = int(parts[1])
                            used_mem = int(parts[2])
                            memory_percent = round((used_mem / total_mem) * 100, 1) if total_mem > 0 else 0
                
                services_list = [
                    {"name": "suricata-ips", "displayName": "DPI Engine", "port": None},
                    {"name": "ngfw-control", "displayName": "NGFW Control API", "port": 5001},
                    {"name": "ngfw-ml", "displayName": "ML Inference Service", "port": 5003},
                    {"name": "ngfw-flowmeter", "displayName": "Flow Meter", "port": None},
                    {"name": "suri-clam", "displayName": "Suricata-ClamAV", "port": None},
                    {"name": "clamav-daemon", "displayName": "ClamAV Daemon", "port": None},
                ]
                
                services_status = []
                for svc in services_list:
                    ok_svc, out_svc = _run_command(["systemctl", "is-active", f"{svc['name']}.service"])
                    status = "active" if ok_svc and out_svc == "active" else "inactive"
                    services_status.append({"name": svc['name'], "status": status})
                
                ok_net, net_out = _run_command(["cat", "/proc/net/dev"])
                packets_in = 0
                packets_out = 0
                bytes_in = 0
                bytes_out = 0
                if ok_net:
                    lines = net_out.split("\n")
                    for line in lines[2:]:
                        if "enp" in line or "eth" in line:
                            parts = line.split()
                            if len(parts) >= 10:
                                try:
                                    packets_in += int(parts[1])
                                    packets_out += int(parts[9])
                                    bytes_in += int(parts[0].split(":")[1])
                                    bytes_out += int(parts[8])
                                except:
                                    pass
                
                ok_conn, conn_out = _run_command(["ss", "-tun"])
                connections = 0
                if ok_conn:
                    connections = len([l for l in conn_out.split("\n") if l.strip() and "State" not in l])
                
                data = {
                    "type": "system_update",
                    "services": services_status,
                    "blocks": blocks_payload,
                    "stats": {
                        "cpu_load": cpu_load,
                        "memory_percent": memory_percent,
                        "events_today": events_today,
                        "active_threats": active_threats,
                    },
                    "connections": connections,
                    "packets_in": packets_in,
                    "packets_out": packets_out,
                    "bytes_in": bytes_in,
                    "bytes_out": bytes_out,
                }
                
                yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                app_logger.error(f"SSE error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            
            time.sleep(5)
    
    return Response(generate(), mimetype="text/event-stream")


# ─── Legacy Endpoints ──────────────────────────────────────────────────────

@app.route("/api/log_detection", methods=["POST"])
def api_log_detection():
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}

    entry = log_event(json.dumps(data))
    security_logger.info(f"Detection log: {data.get('action', 'unknown')}", extra={"source": data.get("source", "unknown")})

    return jsonify({"success": True, "log_id": entry.id})


# ─── Export Endpoints ───────────────────────────────────────────────────────

@app.route("/api/export/logs", methods=["GET"])
def api_export_logs():
    """Export logs in JSON or CSV format."""
    format_type = request.args.get("format", "json").lower()
    limit = request.args.get("limit", 10000, type=int)
    
    from database import get_backup_logs
    logs = get_backup_logs(limit=limit)
    
    if format_type == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "data"])
        for log in logs:
            try:
                data_obj = json.loads(log.data)
            except:
                data_obj = {"raw": log.data}
            writer.writerow([log.id, log.timestamp, json.dumps(data_obj)])
        output.seek(0)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=logs_export.csv"})
    else:
        payload = []
        for log in logs:
            try:
                data_obj = json.loads(log.data)
            except:
                data_obj = {"raw": log.data}
            payload.append({
                "id": log.id,
                "timestamp": log.timestamp,
                "data": data_obj,
            })
        return jsonify({"success": True, "logs": payload, "total": len(payload)})


@app.route("/api/export/ml_predictions", methods=["GET"])
def api_export_ml_predictions():
    """Export ML predictions in JSON or CSV format."""
    format_type = request.args.get("format", "json").lower()
    limit = request.args.get("limit", 10000, type=int)
    
    from database import get_backup_ml_predictions
    predictions = get_backup_ml_predictions(limit=limit)
    
    if format_type == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "predicted_label", "features"])
        for pred in predictions:
            writer.writerow([pred.id, pred.timestamp, pred.predicted_label, pred.features])
        output.seek(0)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=ml_predictions_export.csv"})
    else:
        payload = []
        for pred in predictions:
            features_list = json.loads(pred.features) if pred.features else []
            payload.append({
                "id": pred.id,
                "timestamp": pred.timestamp,
                "predicted_label": pred.predicted_label,
                "features": features_list,
            })
        return jsonify({"success": True, "predictions": payload, "total": len(payload)})


@app.route("/api/export/malware_alerts", methods=["GET"])
def api_export_malware_alerts():
    """Export malware alerts in JSON or CSV format."""
    format_type = request.args.get("format", "json").lower()
    limit = request.args.get("limit", 10000, type=int)
    
    from database import get_backup_malware_alerts
    alerts = get_backup_malware_alerts(limit=limit)
    
    if format_type == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "filename", "file_hash", "signature", "source_ip", "action", "confidence"])
        for alert in alerts:
            writer.writerow([alert.id, alert.timestamp, alert.filename, alert.file_hash, alert.signature, alert.source_ip, alert.action, alert.confidence])
        output.seek(0)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=malware_alerts_export.csv"})
    else:
        payload = []
        for alert in alerts:
            payload.append({
                "id": alert.id,
                "timestamp": alert.timestamp,
                "filename": alert.filename,
                "file_hash": alert.file_hash,
                "signature": alert.signature,
                "source_ip": alert.source_ip,
                "action": alert.action,
                "confidence": alert.confidence,
            })
        return jsonify({"success": True, "alerts": payload, "total": len(payload)})


if __name__ == "__main__":
    init_db()
    app_logger.info(f"Starting NGFW control API on {config.BIND_HOST}:{config.BIND_PORT}")
    app.run(host=config.BIND_HOST, port=config.BIND_PORT)