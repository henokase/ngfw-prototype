"""cicflowmeter bridge for NGFW ML anomaly detection.

Runs cicflowmeter to sniff packets on enp0s3,
extract CICFlowMeter-compatible features, and POST them to the
ML inference service for classification.

"""

import sys
import time
import requests

# ─── Configuration ──────────────────────────────────────────────
INTERFACE = "enp0s3"
ML_SERVICE_URL = "http://localhost:5003/predict"

# All cicflowmeter field names that get_data() produces.
CFM_FIELDS = [
    "src_ip", "dst_ip", "src_port", "dst_port", "protocol",
    "timestamp", "flow_duration", "flow_byts_s", "flow_pkts_s",
    "fwd_pkts_s", "bwd_pkts_s", "tot_fwd_pkts", "tot_bwd_pkts",
    "totlen_fwd_pkts", "totlen_bwd_pkts",
    "fwd_pkt_len_max", "fwd_pkt_len_min", "fwd_pkt_len_mean", "fwd_pkt_len_std",
    "bwd_pkt_len_max", "bwd_pkt_len_min", "bwd_pkt_len_mean", "bwd_pkt_len_std",
    "pkt_len_max", "pkt_len_min", "pkt_len_mean", "pkt_len_std", "pkt_len_var",
    "fwd_header_len", "bwd_header_len", "fwd_seg_size_min", "fwd_act_data_pkts",
    "flow_iat_mean", "flow_iat_max", "flow_iat_min", "flow_iat_std",
    "fwd_iat_tot", "fwd_iat_max", "fwd_iat_min", "fwd_iat_mean", "fwd_iat_std",
    "bwd_iat_tot", "bwd_iat_max", "bwd_iat_min", "bwd_iat_mean", "bwd_iat_std",
    "fin_flag_cnt", "syn_flag_cnt", "rst_flag_cnt", "psh_flag_cnt", "ack_flag_cnt",
    "urg_flag_cnt", "ece_flag_cnt",
    "down_up_ratio", "pkt_size_avg",
    "init_fwd_win_byts", "init_bwd_win_byts",
    "active_max", "active_min", "active_mean", "active_std",
    "idle_max", "idle_min", "idle_mean", "idle_std",
    "fwd_byts_b_avg", "fwd_pkts_b_avg", "bwd_byts_b_avg", "bwd_pkts_b_avg",
    "fwd_blk_rate_avg", "bwd_blk_rate_avg",
    "fwd_seg_size_avg", "bwd_seg_size_avg", "cwr_flag_count",
    "subflow_fwd_pkts", "subflow_bwd_pkts",
    "subflow_fwd_byts", "subflow_bwd_byts",
]


def wait_for_ml_service(timeout=30):
    """Wait for ML inference service to be ready."""
    url = "http://localhost:5003/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                print("[*] ML inference service is ready")
                return True
        except Exception:
            pass
        time.sleep(1)
    print(f"[!] ML inference service not available after {timeout}s")
    return False


def main():
    print(f"[*] cicflowmeter bridge starting")
    print(f"[*] Interface: {INTERFACE}")
    print(f"[*] ML Service: {ML_SERVICE_URL}")
    print(f"[*] Fields: {len(CFM_FIELDS)} cicflowmeter fields")

    if not wait_for_ml_service():
        print("[!] Exiting - ML service not available")
        sys.exit(1)

    from cicflowmeter.sniffer import create_sniffer

    print(f"[*] Starting packet capture on {INTERFACE}")
    print(f"[*] POSTing completed flows to {ML_SERVICE_URL}")

    # Create sniffer using keyword arguments
    sniffer, session = create_sniffer(
        input_file=None,
        input_interface=INTERFACE,
        output_mode="url",
        output=ML_SERVICE_URL,
        input_directory=None,
        fields=",".join(CFM_FIELDS),
        verbose=False,
    )

    sniffer.start()

    try:
        sniffer.join()
    except KeyboardInterrupt:
        print("\n[*] Shutting down cicflowmeter bridge...")
        sniffer.stop()
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
