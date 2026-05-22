#!/usr/bin/env python3
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_test, print_header, print_summary, reset_results
import config


def build_feature_vector(base_values=None):
    fv = {}
    feature_names = [
        "flow_duration", "fwd_packet_length_mean", "bwd_packet_length_mean",
        "flow_packets_per_sec", "flow_bytes_per_sec", "fwd_iat_mean", "bwd_iat_mean",
        "init_fwd_win_bytes", "init_bwd_win_bytes", "fwd_seg_size_min",
        "active_mean", "idle_mean",
    ]
    for i in range(13, 53):
        feature_names.append(f"feature_{i}")
    for i, name in enumerate(feature_names):
        if base_values and name in base_values:
            fv[name] = float(base_values[name])
        else:
            fv[name] = 0.0
    return fv


def run():
    print_header("ML: API Confidence Tests (TC-ML-01, TC-ML-02, TC-ML-03)")

    test_cases = [
        ("TC-ML-01", "High-confidence attack flow → block", {
            "flow_duration": 10000000,
            "fwd_packet_length_mean": 500.0,
            "bwd_packet_length_mean": 800.0,
            "flow_packets_per_sec": 5000.0,
            "flow_bytes_per_sec": 10000000.0,
            "fwd_iat_mean": 10.0,
            "bwd_iat_mean": 15.0,
            "init_fwd_win_bytes": 8192.0,
            "init_bwd_win_bytes": 4096.0,
            "fwd_seg_size_min": 100.0,
            "active_mean": 5000.0,
            "idle_mean": 10.0,
        }, ["block"]),
        ("TC-ML-02", "Mid-confidence suspicious flow → alert", {
            "flow_duration": 5000000,
            "fwd_packet_length_mean": 200.0,
            "bwd_packet_length_mean": 300.0,
            "flow_packets_per_sec": 500.0,
            "flow_bytes_per_sec": 500000.0,
            "fwd_iat_mean": 100.0,
            "bwd_iat_mean": 150.0,
            "init_fwd_win_bytes": 65535.0,
            "init_bwd_win_bytes": 32768.0,
            "fwd_seg_size_min": 50.0,
            "active_mean": 1000.0,
            "idle_mean": 100.0,
        }, ["alert", "monitor", "log"]),
        ("TC-ML-03", "Low-confidence benign flow → allow", {
            "flow_duration": 1000,
            "fwd_packet_length_mean": 40.0,
            "bwd_packet_length_mean": 40.0,
            "flow_packets_per_sec": 1.0,
            "flow_bytes_per_sec": 500.0,
            "fwd_iat_mean": 5000.0,
            "bwd_iat_mean": 5000.0,
            "init_fwd_win_bytes": 65535.0,
            "init_bwd_win_bytes": 65535.0,
            "fwd_seg_size_min": 20.0,
            "active_mean": 100.0,
            "idle_mean": 5000.0,
        }, ["allow", "pass", "permit"]),
    ]

    for tc_id, desc, base_values, expected_actions in test_cases:
        try:
            fv = build_feature_vector(base_values)
            r = requests.post(
                f"{config.ML_BASE}/predict",
                json=fv,
                timeout=config.REQUEST_TIMEOUT,
            )
            passed = False
            detail = f"HTTP {r.status_code}"
            if r.status_code == 200:
                try:
                    body = r.json()
                    action = body.get("action", body.get("prediction", "")).lower()
                    detail += f", action='{action}'"
                    for ea in expected_actions:
                        if ea in action or ea == action:
                            passed = True
                            break
                    if not passed:
                        detail += f" (expected one of {expected_actions})"
                except Exception:
                    detail += f", body: {r.text[:200]}"
            else:
                detail += f", body: {r.text[:200]}"
            log_test(tc_id, desc, passed, detail)
        except requests.exceptions.ConnectionError:
            log_test(tc_id, desc, False, f"Connection refused to {config.ML_BASE}")
        except Exception as e:
            log_test(tc_id, desc, False, str(e))


if __name__ == "__main__":
    reset_results()
    run()
    ok = print_summary()
    sys.exit(0 if ok else 1)
