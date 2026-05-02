# NGFW Control - Documentation

This folder contains the **essential documentation** for the NGFW (Next-Generation Firewall) project.

## 📚 Essential Documents (5 Files)

These 5 files provide **complete context** for understanding the project. For AI agents or new developers, read in this order:

| # | File | Purpose | Read Time |
|---|------|---------|-----------|
| 1 | `NGFW_PROJECT_OVERVIEW.md` | **START HERE** - Project overview, architecture, what's implemented, key paths | 5 min |
| 2 | `api_documentation.md` | API reference - All 5 endpoints, request/response examples | 10 min |
| 3 | `nftables_configuration.md` | Firewall config - nftables rules, commands, current state | 10 min |
| 4 | `suricata_configuration.md` | IDS config - Suricata rules, custom rules, current issues | 10 min |
| 5 | `alert_processor_implementation_and_testing.md` | Processor logic - How suri_clam_processor.py works | 15 min |

**Total read time: ~50 minutes for complete understanding**

---

## 🏗️ Architecture (Simplified)

```
External Client (Real IP: 192.168.1.x)
        │
        ▼
┌───────────────────────────────────┐
│  VM1 - Gateway (10.0.0.1)       │
│                                   │
│  • Suricata DPI (sees real IPs)  │
│  • ClamAV (malware scanning)      │
│  • nftables (IP blocking)         │
│  • NGFW Control API (port 5001) │
│  • suri_clam_processor.py        │
└───────────────┬───────────────────┘
                │ DNAT (source = 10.0.0.1)
                ▼
┌───────────────────────────────────┐
│  VM2 - Test Website (10.0.0.5)   │
│                                   │
│  • Flask web app (port 5001)     │
│  • nginx reverse proxy (port 80)  │
│  • Local ClamAV (quarantine only) │
└───────────────────────────────────┘
```

**Key Points:**
- VM1 handles ALL threat detection and blocking independently
- VM2 does NOT communicate with VM1 (no `/api/malware_alert`)
- VM1 sees real source IPs directly (no NAT correlation needed)
- Conntrack correlation code has been removed (unnecessary)

---

## 🔑 Key Facts

| Item | Value |
|------|-------|
| **VM1 (Gateway)** | 10.0.0.1 (internal), 192.168.1.3 (bridged) |
| **VM2 (Web Server)** | 10.0.0.5 |
| **API Base URL** | `http://192.168.1.3:5001` |
| **SSH to VM2** | `ubuntuhero` / `ubuntuhero4433` |
| **Suricata Rules** | 47,309 + 13 custom rules |
| **Database** | SQLite (`/opt/ngfw-control/ngfw.db`) |
| **Tables** | `blocks`, `logs` (no `malware_alerts`) |

---

## 📖 For AI Agents

If you're an AI agent (e.g., opencode, Claude, GPT), reading these 5 files will give you:

✅ Complete system architecture understanding  
✅ How the firewall (nftables) is configured  
✅ How the IDS (Suricata) detects threats  
✅ How the processor correlates events and blocks IPs  
✅ API endpoints for integration  
✅ Current issues and their fixes  
✅ Key file paths and commands  

**No other documentation is needed.**

---

## 🗑️ Archived Files

32 redundant/historical files were deleted from this folder (May 2, 2026):

- **20 Historical Files** - Old plans, phase roadmaps, implementation fix logs
- **12 Redundant Files** - Duplicates of the 5 essential files

The deleted files contained development history that is no longer relevant to understanding the current system.

---

**Documentation Updated:** May 2, 2026  
**Project Status:** Implementation Complete ✅
