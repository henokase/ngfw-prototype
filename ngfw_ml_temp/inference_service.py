"""NGFW ML Inference Service (Phase 5).

Flask service that receives flow features from cicflowmeter, runs
5-model soft-voting ensemble (RF + XGB + DT + LR + CatBoost), and takes
action via the Decision Engine API.

Applies StandardScaler before prediction as specified in ensemble_config.
"""

import json
import warnings
import time
import requests
import joblib
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

warnings.filterwarnings("ignore")
import logging
logging.captureWarnings(True)
logging.getLogger("py.warnings").setLevel(logging.ERROR)

from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

app = Flask(__name__)
CORS(app)

BASE = "/opt/ngfw-ml/models"
DECISION_ENGINE_URL = "http://10.0.0.1:5001"

# ─── Load config ────────────────────────────────────────────────
with open("/opt/ngfw-ml/ensemble_config.json") as f:
    config = json.load(f)

MODEL_WEIGHTS = config["model_weights"]
THRESHOLD = config["threshold"]
MODEL_FILES = config["model_files"]
ACTION_POLICY = config["action_policy"]
FEATURE_COLUMNS = config["feature_columns"]

# ─── Load scaler ────────────────────────────────────────────────
scaler = joblib.load(f"{BASE}/{config['preprocessing']['scaler_file']}")

# ─── Load all models dynamically from config ────────────────────
MODELS = {}
for name, filename in MODEL_FILES.items():
    MODELS[name] = joblib.load(f"{BASE}/{filename}")
    print(f"[+] Loaded model: {name} ({type(MODELS[name]).__name__})")

N_MODELS = len(MODELS)
print(f"[*] Loaded {N_MODELS} models, scaler, {len(FEATURE_COLUMNS)} feature columns")

# Map config model names to API field names for storage
SCORE_MAP = {
    "random_forest": "rf_score",
    "xgboost": "xgb_score",
    "decision_tree": "decision_tree_score",
    "logistic_regression": "logistic_regression_score",
    "catboost": "catboost_score",
}

# ─── Field mapping: cicflowmeter output -> our feature columns ─
CIC_TO_FEATURE = {
    "dst_port": "Destination Port",
    "flow_duration": "Flow Duration",
    "tot_fwd_pkts": "Total Fwd Packets",
    "totlen_fwd_pkts": "Total Length of Fwd Packets",
    "fwd_pkt_len_max": "Fwd Packet Length Max",
    "fwd_pkt_len_min": "Fwd Packet Length Min",
    "fwd_pkt_len_mean": "Fwd Packet Length Mean",
    "fwd_pkt_len_std": "Fwd Packet Length Std",
    "bwd_pkt_len_max": "Bwd Packet Length Max",
    "bwd_pkt_len_min": "Bwd Packet Length Min",
    "bwd_pkt_len_mean": "Bwd Packet Length Mean",
    "bwd_pkt_len_std": "Bwd Packet Length Std",
    "flow_byts_s": "Flow Bytes/s",
    "flow_pkts_s": "Flow Packets/s",
    "flow_iat_mean": "Flow IAT Mean",
    "flow_iat_std": "Flow IAT Std",
    "flow_iat_max": "Flow IAT Max",
    "flow_iat_min": "Flow IAT Min",
    "fwd_iat_tot": "Fwd IAT Total",
    "fwd_iat_mean": "Fwd IAT Mean",
    "fwd_iat_std": "Fwd IAT Std",
    "fwd_iat_max": "Fwd IAT Max",
    "fwd_iat_min": "Fwd IAT Min",
    "bwd_iat_tot": "Bwd IAT Total",
    "bwd_iat_mean": "Bwd IAT Mean",
    "bwd_iat_std": "Bwd IAT Std",
    "bwd_iat_max": "Bwd IAT Max",
    "bwd_iat_min": "Bwd IAT Min",
    "fwd_header_len": "Fwd Header Length",
    "bwd_header_len": "Bwd Header Length",
    "fwd_pkts_s": "Fwd Packets/s",
    "bwd_pkts_s": "Bwd Packets/s",
    "pkt_len_min": "Min Packet Length",
    "pkt_len_max": "Max Packet Length",
    "pkt_len_mean": "Packet Length Mean",
    "pkt_len_std": "Packet Length Std",
    "pkt_len_var": "Packet Length Variance",
    "fin_flag_cnt": "FIN Flag Count",
    "psh_flag_cnt": "PSH Flag Count",
    "ack_flag_cnt": "ACK Flag Count",
    "pkt_size_avg": "Average Packet Size",
    "subflow_fwd_byts": "Subflow Fwd Bytes",
    "init_fwd_win_byts": "Init_Win_bytes_forward",
    "init_bwd_win_byts": "Init_Win_bytes_backward",
    "fwd_act_data_pkts": "act_data_pkt_fwd",
    "fwd_seg_size_min": "min_seg_size_forward",
    "active_mean": "Active Mean",
    "active_max": "Active Max",
    "active_min": "Active Min",
    "idle_mean": "Idle Mean",
    "idle_max": "Idle Max",
    "idle_min": "Idle Min",
}


def map_features(data):
    features = []
    missing = []
    for col in FEATURE_COLUMNS:
        cf_field = None
        for cf, feat in CIC_TO_FEATURE.items():
            if feat == col:
                cf_field = cf
                break
        if cf_field and cf_field in data:
            val = data[cf_field]
            features.append(float(val) if val not in (None, "") else 0.0)
        else:
            missing.append(col)
            features.append(0.0)
    return features, missing


def ensemble_predict(X_scaled):
    probas = {}
    for name, model in MODELS.items():
        p = float(model.predict_proba(X_scaled)[0, 1])
        probas[name] = p
    ensemble = sum(MODEL_WEIGHTS[name] * probas[name] for name in MODELS)
    return probas, ensemble


def action_from_confidence(p_ensemble):
    if p_ensemble >= 0.75:
        return "block"
    elif p_ensemble >= 0.50:
        return "alert"
    return "allow"


@app.route("/predict", methods=["POST"])
def predict():
    start = time.time()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    src_ip = data.get("src_ip", "unknown")
    dst_ip = data.get("dst_ip", "unknown")

    # Check if IP is already blocked
    try:
        check_resp = requests.get(f"{DECISION_ENGINE_URL}/api/list_blocks", timeout=2)
        if check_resp.status_code == 200:
            blocked_ips = [b.get("ip") for b in check_resp.json().get("blocks", [])]
            if src_ip in blocked_ips:
                print(f"[SKIP] src_ip={src_ip} already blocked")
                return jsonify({
                    "label": "Blocked", "confidence": 1.0, "action": "already_blocked",
                    "latency_ms": 0, "src_ip": src_ip, "dst_ip": dst_ip, "skipped": True
                }), 200
    except Exception as e:
        print(f"[WARN] Failed to check blocked IPs: {e}")

    features, missing = map_features(data)
    if missing:
        print(f"[WARN] Missing fields: {missing}")

    if len(features) != len(FEATURE_COLUMNS):
        return jsonify({"error": f"Expected {len(FEATURE_COLUMNS)} features, got {len(features)}"}), 400

    X_raw = np.array(features, dtype=np.float32).reshape(1, -1)
    X_scaled = scaler.transform(X_raw)

    probas, p_ensemble = ensemble_predict(X_scaled)
    action = action_from_confidence(p_ensemble)
    latency = time.time() - start

    result = {
        "label": "Attack" if p_ensemble >= THRESHOLD else "Normal Traffic",
        "confidence": round(p_ensemble, 4),
        "action": action,
        "latency_ms": round(latency * 1000, 2),
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "model_probas": {k: round(v, 4) for k, v in probas.items()},
    }

    probas_str = " ".join(f"{k}={round(v,4)}" for k, v in probas.items())
    print(f"[PREDICT] src={src_ip} dst={dst_ip} conf={result['confidence']} action={action} {probas_str}")

    # Store prediction in database
    try:
        payload = {
            "attack_type": "Real-time Flow",
            "source_ip": src_ip,
            "dest_ip": dst_ip,
            "confidence": result["confidence"],
            "ensemble_score": result["confidence"],
            "action": action,
            "features": features,
        }
        for model_name, score_field in SCORE_MAP.items():
            payload[score_field] = probas.get(model_name, 0.0)
        requests.post(f"{DECISION_ENGINE_URL}/api/ml_predictions", json=payload, timeout=3)
    except Exception as e:
        print(f"[WARN] Failed to store prediction: {e}")

    if action in ("alert", "block"):
        _take_action(action, src_ip, result)

    return jsonify(result)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "models_loaded": N_MODELS,
        "port": 5003,
        "models": list(MODELS.keys()),
        "features": len(FEATURE_COLUMNS),
        "threshold": THRESHOLD,
        "action_policy": ACTION_POLICY,
        "service_uptime": "active",
        "last_prediction": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


def _take_action(action, src_ip, result):
    if src_ip in ("unknown", "0.0.0.0"):
        return
    if action == "alert":
        try:
            requests.post(f"{DECISION_ENGINE_URL}/api/log_detection", json={
                "source": "ML",
                "event": "ML Anomaly Detected",
                "data": {
                    "src_ip": src_ip,
                    "confidence": result["confidence"],
                    "action": action,
                    "model_probas": result["model_probas"],
                    "latency_ms": result.get("latency_ms", 0),
                }
            }, timeout=2)
            print(f"[ALERT] src={src_ip} confidence={result['confidence']}")
        except Exception as e:
            print(f"[ERROR] Failed to log detection: {e}")
    elif action == "block":
        try:
            check_resp = requests.get(f"{DECISION_ENGINE_URL}/api/list_blocks", timeout=2)
            already_blocked = False
            if check_resp.status_code == 200:
                blocked_ips = [b.get("ip") for b in check_resp.json().get("blocks", [])]
                if src_ip in blocked_ips:
                    already_blocked = True
                    print(f"[SKIP] src={src_ip} already blocked")
            if not already_blocked:
                resp = requests.post(f"{DECISION_ENGINE_URL}/api/block_ip", json={
                    "ip": src_ip,
                    "reason": "ML Anomaly Detected",
                    "ttl": "1h",
                    "signature": "ML-Anomaly-Ensemble",
                    "source": "decision_engine",
                    "action": "ml_block",
                    "dst_ip": result.get("dst_ip", ""),
                    "attack_type": result.get("attack_type", "Unknown"),
                    "ml_confidence": result.get("confidence", 0),
                    "model_scores": result.get("model_probas", {}),
                }, timeout=2)
                print(f"[BLOCK] src={src_ip} confidence={result['confidence']} -> {resp.status_code}")
        except Exception as e:
            print(f"[ERROR] Failed to block IP: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=False)
