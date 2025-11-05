# Implementation Plan Updates - File Scanning Integration

## Summary of Changes

The implementation plan has been updated to fully integrate the detailed file scanning and cross-VM adaptive blocking workflow documented in `file-scanning-process.md`.

---

## 🔄 Major Updates

### 1. **Added Critical Architecture Section**
- Complete data flow diagram for file uploads
- Step-by-step workflow from user upload to adaptive blocking
- Key implementation points highlighted upfront

### 2. **Enhanced Phase 3.3: Antivirus Service**
**New requirements:**
- Temp file storage in `/tmp/uploads/` before scanning
- Use `scan_file()` or `instream()` methods
- Quarantine logic to move infected files
- Log scan results with signature names and source IPs
- Function to notify VM1 API when malware detected
- ML-ready logging format

### 3. **Enhanced Phase 5.2: File Upload Routes**
**New requirements:**
- Extract client IP from `X-Real-IP` header (nginx)
- Implement dual-path workflow:
  - **Clean files**: `/tmp/uploads` → `/uploads/safe/` + DB record
  - **Infected files**: `/tmp/uploads` → `/uploads/quarantine/` + VM1 API call
- Handle ClamAV errors gracefully
- Extended test payloads (EICAR, compressed archives, webshells)

### 4. **New Phase 11: VM1-VM2 Cross-Communication API**
**Purpose:** Enable adaptive response across VMs

**Step 11.1 - VM1 Blocking API:**
- Create Flask/FastAPI service on VM1
- `/api/block_ip` endpoint
- Execute nftables commands to add IPs to blocked_ips set
- Timeout-based blocking (1 hour default)
- API authentication for security

**Step 11.2 - VM2 Integration:**
- Add VM1 API endpoint to config
- Call VM1 API from `antivirus_service.py` on malware detection
- Send uploader IP for blocking
- Retry logic and error handling
- Log all cross-VM communications

### 5. **Updated Phase 12: Integration & Deployment**
**Enhanced ClamAV setup:**
- Detailed installation commands
- Service verification steps
- EICAR test file validation
- Quarantine folder checks

### 6. **Updated Phase 13: NGFW Integration Testing**
**New Step 13.3 - ClamAV Integration & Adaptive Blocking:**
- Upload EICAR test file
- Verify ClamAV detection
- Check quarantine folder
- **Verify VM2 → VM1 API call**
- **Check nftables blocked_ips set**
- **Test blocking effectiveness**
- Validate cross-VM communication logs

### 7. **Enhanced Database Model**
**UploadedFile model additions:**
- `scan_result` - Clean/Infected status
- `signature_name` - Malware signature detected
- `uploader_ip` - Source IP address

### 8. **Updated Directory Structure**
**New folder:**
- `/tmp/uploads/` - Temporary storage for pre-scan files

### 9. **Updated Success Criteria**
**New validation points:**
- ClamAV scanning works on VM2
- Infected files moved to quarantine
- VM2 successfully calls VM1 API
- VM1 dynamically blocks IPs via nftables
- Cross-VM communication validated

### 10. **Updated Timeline**
- **Old:** 18-27 hours across 13 phases
- **New:** 22-33 hours across 14 phases
- Added Phase 11 (VM1-VM2 API) - 2-3 hours

---

## 🎯 Key Architectural Insights Integrated

### File Scanning Workflow
1. **Pre-scan temp storage** prevents infected files from reaching permanent storage
2. **Dual destinations** (safe vs quarantine) based on scan results
3. **Cross-VM communication** enables adaptive response
4. **IP extraction** from nginx headers for blocking
5. **ML-ready logging** captures all scan results for training data

### Adaptive Blocking Pipeline
```
Malware Upload → ClamAV Detection → VM2 logs event → 
VM2 calls VM1 API → VM1 adds IP to nftables → 
Future requests from IP blocked
```

### Integration Points
- **VM1 ↔ VM2**: API-based communication for blocking
- **Flask ↔ ClamAV**: PyClamd for file scanning
- **nginx ↔ Flask**: X-Real-IP header forwarding
- **Database ↔ ML**: Structured logging for anomaly detection

---

## 📋 Implementation Priorities

### Critical Path Items
1. **Phase 3.3** - Antivirus service with VM1 API integration
2. **Phase 5.2** - File upload routes with dual-path logic
3. **Phase 11** - VM1-VM2 cross-communication API
4. **Phase 13.3** - End-to-end adaptive blocking validation

### Dependencies
- Phase 11 depends on Phase 3.3 (antivirus service design)
- Phase 13.3 depends on Phase 11 (API must exist)
- All file upload testing depends on ClamAV setup (Phase 12.4)

---

## 🔍 Testing Validation Checklist

### File Upload Testing
- [ ] Upload clean file → moves to `/uploads/safe/`
- [ ] Upload EICAR → moves to `/uploads/quarantine/`
- [ ] Upload EICAR → VM1 API called with uploader IP
- [ ] Check nftables: IP added to blocked_ips set
- [ ] Attempt second upload from blocked IP → request denied
- [ ] Verify logs show complete workflow

### Cross-VM Communication
- [ ] VM1 API responds to block requests
- [ ] VM2 handles API failures gracefully
- [ ] Timeout-based blocking works (IP unblocked after 1 hour)
- [ ] Multiple IPs can be blocked simultaneously
- [ ] Dashboard shows blocked IPs in real-time

---

## 📚 Documentation References

All updates align with:
- **`file-scanning-process.md`** - Complete workflow documentation
- **`Requirements.ms`** - Original project requirements
- **`Project-structure.md`** - Folder structure specification

---

## ✅ Next Steps

1. Review updated `IMPLEMENTATION_PLAN.md`
2. Begin Phase 1 - Project Foundation
3. Pay special attention to Phase 3.3, 5.2, and 11
4. Test file scanning workflow thoroughly in Phase 13.3
5. Document all findings in Phase 14

---

**Updated:** Based on detailed file scanning process analysis
**Status:** Ready for implementation
