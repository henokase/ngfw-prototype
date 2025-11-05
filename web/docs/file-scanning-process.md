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

Add a small API endpoint on VM1 (Flask or FastAPI microservice) to handle automatic IP blocking from VM2 when a malicious file is uploaded:

**Example (VM2 → VM1)**:

```python
# VM2 antivirus_service.py
if result == "FOUND":
    requests.post("http://10.0.0.1:5000/api/block_ip", json={"ip": uploader_ip})
```

**Example (VM1 auto-block API)**:

```python
# VM1 (ngfw control service)
@app.route('/api/block_ip', methods=['POST'])
def block_ip():
    ip = request.json['ip']
    os.system(f"sudo nft add element inet firewall blocked_ips {{ {ip} timeout 1h }}")
    return jsonify({"status": "blocked", "ip": ip})
```

This creates **cross-VM adaptivity** — the moment a file is flagged on VM2, its source IP is dynamically blocked in VM1.

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
