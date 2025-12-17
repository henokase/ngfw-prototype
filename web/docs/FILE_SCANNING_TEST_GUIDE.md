# File Scanning Test Guide (VM2 ↔ ClamAV ↔ VM1)

This guide shows how to manually test the file scanning flow on **VM2** (web app) with both clean and infected files, and explains what happens under the hood in VM2 and in VM1's decision engine (`ngfw-control`).

---

## 1. Prerequisites

- VM2:
  - ClamAV daemon (`clamav-daemon`) running and able to detect EICAR (verified with `clamdscan /tmp/eicar.com`).
  - Web app running (Flask app in the `web` project).
- VM1:
  - `ngfw-control` service running and listening on `http://10.0.0.1:5001`.

The web app's `AntivirusService` is configured to use the ClamAV Unix socket (by default `/var/run/clamav/clamd.ctl`, or `CLAMAV_SOCKET` if set). If the socket is not available it falls back to TCP or simulation.

---

## 2. Quick Connectivity Test (CLI, VM2)

From the VM2 shell, using the same Python environment as the web app:

```bash
cd /path/to/ngfw-prototype/web
source venv/bin/activate  # if you use a venv
python -m tests.test_clamav_connection
```

Expected output:

- Clean file: status `clean`.
- EICAR file: status `infected` with a ClamAV signature (for example `Eicar-Test-Signature`).

If the infected file is reported as `infected`, the web app is correctly talking to ClamAV.

---

## 3. Manual Positive Test (Clean File via Web UI)

### Steps

1. On VM2, open the web app in a browser (through VM1):

   ```
   http://<vm1-ip>/upload
   ```

2. Choose a small **harmless** text file, e.g. `clean.txt` containing:

   ```text
   This is a clean test file.
   ```

3. Submit the form.

### Expected Result (User View)

- Response JSON (or page) indicates success:

  ```json
  {
    "status": "success",
    "message": "File uploaded successfully",
    "scan_result": "clean",
    "filename": "clean.txt",
    "file_hash": "..."
  }
  ```

- File appears under the safe uploads directory on VM2 (typically `uploads/safe/`).

### Underlying Process (System View)

On **VM2 (web)**:

1. `upload_routes.upload_file` saves the uploaded file to `/tmp/uploads/<filename>`.
2. It computes a SHA-256 hash for logging and DB.
3. It calls `get_antivirus_service()`, which now prefers the ClamAV Unix socket:
   - If `CLAMAV_SOCKET` env var is set, uses that path.
   - Else tries `/var/run/clamav/clamd.ctl`.
   - If the socket is missing, falls back to TCP or simulation mode.
4. `AntivirusService.scan_file` sends the file to `clamd`:
   - If ClamAV reports **no threats**, `status` is `clean`.
5. The file is moved from `/tmp/uploads` to `uploads/safe/`.
6. An `UploadedFile` DB record is created with `scan_result='clean'`.
7. Middleware logging (`request_logger`) records the request, including `g.upload_result='clean'`.

On **VM1 (ngfw-control)**:

- No action for clean files; no call to `/api/malware_alert` is made.

---

## 4. Manual Negative Test (Infected File via Web UI)

### Steps

1. On VM2, create the EICAR test file under `/tmp`:

   ```bash
   echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.com
   ```

2. Copy it to your local machine or make it downloadable to your browser, then upload it through the web app's `/upload` page.

3. Submit the form with `eicar.com`.

### Expected Result (User View)

- Response JSON indicates an error and quarantine:

  ```json
  {
    "status": "error",
    "message": "File is infected and has been quarantined",
    "filename": "eicar.com",
    "file_hash": "...",
    "scan_result": "infected",
    "signature": "Eicar-Test-Signature",
    "vm1_response": { ... or null ... }
  }
  ```

- The file is no longer in `/tmp/uploads`; it is moved under `uploads/quarantine/` on VM2.

### Underlying Process on VM2 (Web)

1. Upload is received and saved to `/tmp/uploads/eicar.com`.
2. The file hash is computed.
3. `AntivirusService.scan_file` sends the file to ClamAV via the Unix socket.
4. ClamAV detects EICAR and returns an `infected` status with a signature.
5. `upload_routes.upload_file`:
   - Moves the file to `uploads/quarantine/`.
   - Creates an `UploadedFile` DB record with `scan_result='infected'` and the AV signature.
   - Calls `notify_vm1_malware(filename, file_hash, signature)`.
6. `notify_vm1_malware` sends a POST request to VM1:

   ```http
   POST http://10.0.0.1:5001/api/malware_alert
   Content-Type: application/json

   {
     "event_type": "malware_detected",
     "filename": "eicar.com",
     "timestamp": "<vm2-detection-timestamp>",
     "result": "infected",
     "file_hash": "<sha256>",
     "signature": "Eicar-Test-Signature",
     "vm2_source": "web_upload_scanner"
   }
   ```

7. The upload route logs a critical security event including whether VM1 responded and any `blocked_ip` it reports (future phases).

### Underlying Process on VM1 (ngfw-control)

1. `/api/malware_alert` receives the JSON payload.
2. It validates required fields.
3. It creates a `MalwareAlert` record in SQLite (`ngfw.db`), storing:
   - `filename`, `file_hash`, `signature`.
   - `vm2_timestamp` (from the payload) and `vm1_timestamp` (when received).
   - `vm2_source` and an initial `action_taken="pending_correlation"`.
4. It logs the event into the `logs` table via `log_event("vm2", "malware_alert", ...)`.
5. It writes a critical log entry via `security_logger` (e.g. `ngfw-security.log`) with details about the alert.
6. It returns a JSON response to VM2 with:

   ```json
   {
     "success": true,
     "alert_id": <id>,
     "correlation_results": {
       "candidate_ips": [],
       "selected_ip": null,
       "confidence_score": null,
       "correlation_method": null
     },
     "action_taken": {
       "decision": "pending_correlation",
       "blocked_ip": null,
       "block_duration": null,
       "reason": null,
       "block_id": null
     }
   }
   ```

At this stage (Phase 1 of the malware integration plan), no automatic IP blocking is performed yet. The alert is stored and logged for future correlation and decision-engine processing.

---

## 5. Summary of Expected Behaviors

- **Clean file**:
  - Stored under `uploads/safe/` on VM2.
  - Recorded as `scan_result='clean'` in VM2 DB.
  - No call to VM1.

- **Infected file (EICAR)**:
  - Quarantined under `uploads/quarantine/` on VM2.
  - Recorded as `scan_result='infected'` with AV signature in VM2 DB.
  - Malware alert sent to VM1 `/api/malware_alert`.
  - VM1 stores a `MalwareAlert` record and logs the event; decision engine currently marks it as `pending_correlation`.

This gives you a complete manual test loop to verify ClamAV integration, VM2 upload handling, and VM1 malware alert ingestion.
