## 🧩 1. Overview of What Happens When a File Is Uploaded

Let’s trace the full journey of an uploaded file through your **Adaptive NGFW dual-VM setup**:

### ⚙️ Step-by-Step Data Flow (High-Level)

1. **A user uploads a file via the website (hosted on VM2)**

   * The browser sends an HTTP `POST /upload` request.
   * This traffic first goes through your **VM1 (firewall)**.

2. **VM1 (Firewall) handles the packet flow:**

   * **nftables** filters packets → allows HTTP traffic (TCP/80) through because of the DNAT rule:

     ```
     iif "enp0s3" oif "enp0s8" tcp dport 80 accept
     ```
   * The request is then forwarded to VM2 (`10.0.0.5`) through NAT.
   * **At this stage:** nftables and Suricata see and log the packets, but do **not alter** or buffer the payload — they just inspect and log.

3. **Suricata DPI (Deep Packet Inspection) runs on VM1**

   * Suricata mirrors the packets and may:

     * Log the flow and payload metadata.
     * Trigger a signature alert if the upload traffic matches known patterns (e.g., malware signatures, suspicious extensions).
   * **Suricata does not save the file** — it just analyzes packets and logs events.
   * If a known malware signature is detected, Suricata can signal your automation (ML/response engine) to **block the IP** or **drop the flow** mid-transfer.

4. **The file reaches VM2 (web server)**

   * nginx (reverse proxy) accepts the HTTP request and forwards it to the Flask app.
   * Flask receives the file via `request.files['file']`.

5. **At this point, the file exists temporarily in VM2’s memory or temp folder.**

   * Before saving it to `/uploads`, your Flask app calls the **Antivirus Service** (via PyClamd / ClamAV).

6. **File scanning with ClamAV (in VM2):**

   * Flask temporarily stores the file in a temp folder: `/tmp/uploads`.
   * PyClamd sends the file path or byte stream to ClamAV daemon (`clamd`) for scanning.
   * ClamAV checks:

     * File hash and signatures (virus database)
     * Compressed files (it can unpack archives)
     * Common malware patterns (macro, PE, etc.)

7. **Scan result determines what happens next:**

   * ✅ **If clean:**

     * File is moved from `/tmp/uploads` → `/uploads` (permanent storage).
     * A database record is created (`UploadedFile` model).
     * Success message returned to user.
     * Event logged: “Clean file uploaded successfully.”
   * ❌ **If infected:**

     * File is quarantined or deleted.
     * Result logged: `"Malware detected: Trojan.Generic..."`
     * Alert raised (can trigger auto-block in VM1 via API call).
     * User sees an error: “Upload failed — file infected.”
     * Optional: log details for ML later (source IP, filename, signature hit).

---

## 🧩 2. Architecture


| File                                | Purpose                                          | Where it runs | Notes                                                                      |
| ----------------------------------- | ------------------------------------------------ | ------------- | -------------------------------------------------------------------------- |
| `src/services/antivirus_service.py` | Service layer for antivirus operations           | VM2           | Called by Flask route handler                                              |
| PyClamd connection                  | Talks to local `clamd` daemon on same VM         | VM2           | Make sure `clamd` service is active (`sudo systemctl start clamav-daemon`) |
| File scanning function              | Sends temp file to ClamAV for scan               | VM2           | Use `scan_file()` or `instream()`                                          |
| Quarantine logic                    | Moves infected files to `/quarantine`            | VM2           | Log and restrict permissions                                               |
| Scan result logging                 | Records scan results (clean/infected, signature) | VM2           | For ML analysis later                                                      |
| Error handling                      | Catches PyClamd or socket errors                 | VM2           | Prevent crashes during high load                                           |

✅ This is perfect for the **Test Website’s application-layer defense**.
It doesn’t replace the NGFW’s DPI, but complements it beautifully.

---

## 🧩 3. How It All Fits Together (Summary Pipeline)

```
User → HTTP POST /upload → VM1 (Firewall) → Suricata (DPI logs + alerts)
     ↓
VM2 (nginx reverse proxy → Flask app)
     ↓
Flask saves temp file → antivirus_service.py scans file → result

If CLEAN:
  → move to /uploads/
  → log success
  → response 200 OK

If INFECTED:
  → move to /quarantine/
  → log detection
  → optionally notify VM1 (via API → nft add element blocked_ips)
  → response 400 “File infected”
```

---

## ⚙️ 4. VM2 → VM1 (Response Automation)

### 🔴 CRITICAL ARCHITECTURAL RULE

**VM2 must NEVER receive, extract, or be aware of real external client IPs.**

**Why:**
- VM1 is the firewall gateway with full visibility of real source IPs
- VM2 only receives traffic from VM1 through DNAT (all requests appear from 10.0.0.1)
- VM1 handles all IP correlation and blocking using its conntrack table
- Communication is **one-directional**: VM2 → VM1 (never VM1 → VM2 for IP data)

### Infected File Handling Workflow:

**Step 1: VM2 scans file with ClamAV**
```python
# VM2 antivirus_service.py
result = scan_file(filepath)

if result['status'] == 'infected':
    # VM2 does NOT try to identify client IP
    # Instead, send structured alert to VM1
```

**Step 2: VM2 sends alert to VM1 Firewall Control API**
```python
# VM2 → VM1 malware notification (NO IP ADDRESS)
import requests
import hashlib
from datetime import datetime

if result['status'] == 'infected':
    # Calculate file hash
    file_hash = hashlib.sha256(open(filepath, 'rb').read()).hexdigest()
    
    # Send alert to VM1 (10.0.0.1:5001)
    alert_payload = {
        'event_type': 'malware_detected',
        'filename': filename,
        'timestamp': datetime.utcnow().isoformat(),
        'result': 'infected',
        'file_hash': file_hash,
        'signature': result['signature'],
        'vm2_source': 'web_upload_scanner'
    }
    
    try:
        response = requests.post(
            'http://10.0.0.1:5001/api/malware_alert',
            json=alert_payload,
            timeout=5
        )
        
        # Log VM1's response
        if response.status_code == 200:
            vm1_response = response.json()
            logger.info(f"VM1 blocked IP: {vm1_response.get('blocked_ip')} - Reason: {vm1_response.get('reason')}")
        
    except Exception as e:
        logger.error(f"Failed to notify VM1: {str(e)}")
```

**Step 3: VM1 correlates event with conntrack and blocks IP**
```python
# VM1 Firewall Control API (10.0.0.1:5001)
@app.route('/api/malware_alert', methods=['POST'])
def malware_alert():
    data = request.json
    
    # Extract alert details
    filename = data['filename']
    file_hash = data['file_hash']
    signature = data['signature']
    timestamp = data['timestamp']
    
    # Correlate with conntrack to find real client IP
    # VM1 knows which external IP is currently connected to VM2
    client_ip = correlate_conntrack_to_vm2_connection()
    
    # Block the real client IP in nftables
    if client_ip and client_ip not in ['10.0.0.1', '127.0.0.1']:
        os.system(f"sudo nft add element inet firewall blocked_ips {{ {client_ip} timeout 1h }}")
        
        # Log the block
        logger.warning(f"Blocked IP {client_ip} - Malware upload: {signature}")
        
        # Return confirmation to VM2
        return jsonify({
            'status': 'blocked',
            'blocked_ip': client_ip,  # VM2 logs this but doesn't use it
            'reason': 'malware_upload',
            'signature': signature,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    return jsonify({'status': 'no_action', 'reason': 'could not identify client'})

def correlate_conntrack_to_vm2_connection():
    """
    Use conntrack to find the real source IP of the current connection to VM2
    
    Example conntrack entry:
    tcp 6 299 ESTABLISHED src=192.168.1.100 dst=10.0.2.15 sport=54321 dport=80 \
        src=10.0.0.5 dst=10.0.0.1 sport=5000 dport=12345
    
    This shows: External client 192.168.1.100 → VM1 → VM2 (10.0.0.5)
    """
    import subprocess
    
    # Get active connections to VM2
    result = subprocess.run(
        ['sudo', 'conntrack', '-L', '-d', '10.0.0.5'],
        capture_output=True,
        text=True
    )
    
    # Parse conntrack output to extract original source IP
    # Implementation depends on conntrack output format
    # Return the external IP that initiated the connection
    
    return parsed_client_ip
```

**Step 4: VM2 logs VM1's response (audit only)**
```python
# VM2 logs the block confirmation but does NOT perform blocking itself
logger.info(f"VM1 response: Blocked IP {vm1_response['blocked_ip']} for malware: {signature}")

# Store in database for audit trail
create_log_event(
    ip_address='10.0.0.1',  # VM2 only sees VM1's IP
    endpoint='/upload',
    method='POST',
    upload_result='infected',
    filename=filename,
    file_hash=file_hash,
    payload=f"Malware detected: {signature}. VM1 blocked attacker."
)
```

### Summary of Correct IP Flow:

```
1. Client (192.168.1.100) → VM1 (10.0.2.15)
   ↓
2. VM1 DNAT → VM2 (10.0.0.5) [VM2 sees source as 10.0.0.1]
   ↓
3. VM2 scans file → INFECTED
   ↓
4. VM2 → VM1 API: {filename, hash, signature, timestamp}
   (NO IP ADDRESS SENT)
   ↓
5. VM1 correlates with conntrack → finds 192.168.1.100
   ↓
6. VM1 blocks 192.168.1.100 in nftables
   ↓
7. VM1 → VM2: {"blocked_ip": "192.168.1.100", "status": "blocked"}
   ↓
8. VM2 logs confirmation (audit only, no action)
```

### Key Principles:
- **VM2 never extracts or uses real client IPs**
- **VM1 retains full IP visibility and control**
- **Communication is one-directional for alerts: VM2 → VM1**
- **VM1 uses conntrack for IP correlation**
- **VM2 only logs VM1's responses for audit purposes**

---

## ✅ 5. Summary Table

| Question                                     | Answer                                                          |
| -------------------------------------------- | --------------------------------------------------------------- |
| Where does scanning happen?                  | Inside VM2 (application layer, Flask)                           |
| Does scanning occur before file reaches VM2? | No, it happens *after* upload completes                         |
| Does this cause latency?                     | Slight (a few seconds post-upload) but not network latency      |
| Where are files stored?                      | Temp → scanned → clean to `/uploads`, infected to `/quarantine` |
| Is the AI agent’s ClamAV plan correct?       | Yes, perfectly matches architecture                             |
| Can scanning logs help ML?                   | Yes — infection logs can be fed to ML as labeled data           |
| Can infected uploads trigger blocking?       | Yes — via API call from VM2 to VM1                              |
