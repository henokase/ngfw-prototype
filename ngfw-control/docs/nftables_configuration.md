# VM1 nftables Firewall Configuration

## System Environment

| Component | Value |
|-----------|-------|
| VM Role | NGFW Gateway (VM1) |
| OS | Ubuntu Desktop |
| nftables Version | v1.0.9 |
| Kernel | 6.14.0-37-generic |
| IP Forwarding | Enabled (`net.ipv4.ip_forward = 1`) |

## Network Topology

| Interface | Name in Config | IP Address | CIDR | Role |
|-----------|----------------|------------|------|------|
| External (Bridged) | `enp0s3` | `192.168.1.3` (changes with WiFi) | `/24` | Faces host network / internet |
| Internal (NAT) | `enp0s8` | `10.0.0.1` | `/24` | Internal network (`ngfw-net`) — connects to VM2 |
| Loopback | `lo` | `127.0.0.1` | `/8` | Local communication |

**Protected Server (VM2):** `10.0.0.5` (Ubuntu Server, connected via `enp0s8`)

**SSH Access (VM2):** `ubuntuhero` / `ubuntuhero4433`

---

## Configuration File Location

- **Live ruleset source:** `/etc/nftables.conf`
- **Apply command:** `sudo nft -f /etc/nftables.conf`
- **Verify command:** `sudo nft list ruleset`

---

## Key Directories & Config Files

### Critical Paths (VM1 - Gateway)

| Purpose | Path |
|---------|------|
| **nftables config** | `/etc/nftables.conf` |
| **Suricata config** | `/etc/suricata/suricata.yaml` |
| **Suricata rules** | `/var/lib/suricata/rules/` |
| **Custom rules** | `/var/lib/suricata/rules/custom-rules.rules` |
| **Suricata logs** | `/var/log/suricata/eve.json`, `/var/log/suricata/fast.log` |
| **Filestore (extracted files)** | `/var/log/suricata/filestore/` |
| **ClamAV daemon socket** | `/var/run/clamav/clamd.ctl` |
| **NGFW Control API** | `/opt/ngfw-control/app.py` |
| **Processor script** | `/opt/ngfw-control/suri_clam_processor.py` |
| **Processor service** | `/etc/systemd/system/suri-clam.service` |
| **NGFW Database** | `/opt/ngfw-control/ngfw.db` |
| **Project docs** | `/home/heroubuntu/Desktop/ngfw-control/docs/` |

### Critical Paths (VM2 - Test Website)

| Purpose | Path |
|---------|------|
| **Flask app** | `/home/ubuntuhero/ngfw-prototype/ngfw-control/app.py` |
| **nginx config** | `/etc/nginx/sites-available/default` |
| **Upload directory** | `/var/www/html/uploads/` (or similar) |

---

## Essential Commands

### Check Service Status

```bash
# VM1 (Gateway)
ps aux | grep -E "suricata|clamd|suri_clam|app.py" | grep -v grep

# Specific services
systemctl status suricata
systemctl status suri-clam
systemctl status ngfw-control
systemctl status clamav-daemon
```

### Restart Services

```bash
sudo systemctl restart suricata
sudo systemctl restart suri-clam
sudo systemctl restart ngfw-control
```

### Verify nftables Rules

```bash
sudo nft list table inet firewall
sudo nft list set inet firewall blocked_ips
```

### Test the System

```bash
# Test SQLi detection
curl -X POST http://10.0.0.5/login -d "username=admin' OR '1'='1'--&password=test"

# Test file upload (clean)
curl -X POST -F "file=@/tmp/clean.txt" http://10.0.0.5/upload

# Test file upload (malware - EICAR test)
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.com
curl -X POST -F "file=@/tmp/eicar.com" http://10.0.0.5/upload

# Check if IP is blocked
sudo nft list set inet firewall blocked_ips

# Monitor logs
sudo journalctl -u suri-clam -f
sudo tail -f /var/log/suricata/fast.log
```

---

## Complete Ruleset (Current Implementation)

> **Last Updated:** May 1, 2026
> **Changes:** Added `size 65536` to `blocked_ips`, added SSH (port 22) to forward chain

```nft
#!/usr/sbin/nft -f

flush ruleset;

table inet firewall {
    set blocked_ips {
        type ipv4_addr;
        flags timeout;
        size 65536;  # Prevents memory exhaustion
    }

    chain input {
        type filter hook input priority filter; policy drop;

        iifname "lo" accept;
        ct state established,related accept;
        ip saddr @blocked_ips counter packets 0 bytes 0 drop;

        tcp dport 22 accept;  # SSH always allowed
        tcp dport { 53, 80, 443 } accept;
        icmp type echo-request accept;
        ip saddr 10.0.0.5 tcp dport 5001 accept;  # VM2 → API
    }

    chain forward {
        type filter hook forward priority filter; policy drop;

        ip saddr @blocked_ips drop;
        ct state established,related accept;

        iifname "enp0s8" oifname "enp0s3" accept;  # VM2 → Internet
        iifname "enp0s3" oifname "enp0s8" tcp dport { 22, 80 } ct state new accept;  # SSH + HTTP to VM2

        ct state new tcp flags syn limit rate 40/second burst 100 packets accept;
        tcp flags syn drop;

        icmp type { echo-reply, destination-unreachable, echo-request, time-exceeded } accept;

        meta l4proto udp ct state new limit rate 100/second burst 50 packets accept;
        meta l4proto udp drop;
    }
}

table ip nat {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;

        iifname "enp0s3" tcp dport 80 dnat to 10.0.0.5:80;  # Port forwarding
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;

        oifname "enp0s3" masquerade;  # VM2 outbound NAT
    }
}
```

### Key Changes from Original:
1. **`size 65536`** added to `blocked_ips` set (prevents memory exhaustion)
2. **SSH port 22** added to `input` chain (always allowed for administration)
3. **SSH port 22** added to `forward` chain: `tcp dport { 22, 80 }` (allows SSH to VM2)
4. Changed `iif`/`oif` to `iifname`/`oifname` (proper nftables syntax)

---

## Rule-by-Rule Explanation

### Table: `inet firewall`

Uses the `inet` family, which handles **both IPv4 and IPv6** in a single table. This is the primary filtering table.

#### Set: `blocked_ips`

```nft
set blocked_ips {
    type ipv4_addr
    flags timeout
}
```

| Property | Meaning |
|----------|---------|
| `type ipv4_addr` | Stores IPv4 addresses |
| `flags timeout` | Each entry auto-expires after a TTL duration. This prevents permanent lockouts. The TTL is specified when adding an element (e.g., `timeout 1h`) |

This set is populated dynamically by the **Decision Engine API** (`/api/block_ip`) via `firewall_service.py`. When Suricata or ClamAV detects a threat, the Decision Engine runs:
```
nft add element inet firewall blocked_ips { <attacker_ip> timeout 1h }
```

#### Chain: `input`

Filters traffic **destined for VM1 itself** (the firewall host).

```nft
type filter hook input priority filter; policy drop;
```
- **Hook:** `input` — applies to packets whose destination is this machine.
- **Policy:** `drop` — **default deny**. Any packet not explicitly accepted is silently dropped.

| # | Rule | Explanation |
|---|------|-------------|
| 1 | `iif "lo" accept` | Allow all traffic on the loopback interface (`127.0.0.0/8`). Required for local services (Flask API, database, etc.) to communicate internally. |
| 2 | `ct state established,related accept` | Allow packets belonging to **already-established connections** or related to them (e.g., FTP data connections, ICMP errors). This is the core of **stateful filtering** — if VM1 initiated an outbound connection, its return traffic is allowed. |
| 3 | `ip saddr @blocked_ips counter packets 0 bytes 0 drop` | **Drop all traffic** from IPs in the dynamic `blocked_ips` set. The `counter` tracks how many packets/bytes have been dropped from blocked sources. This rule sits **after** `established,related` to avoid breaking existing connections retroactively, but **before** service ports so blocked IPs cannot open new connections. |
| 4 | `tcp dport { 22, 53, 80, 443 } accept` | Allow inbound TCP on **SSH (22)**, **DNS (53)**, **HTTP (80)**, and **HTTPS (443)**. SSH for remote management; DNS for potential local resolver; HTTP/HTTPS for the web application traffic that terminates or passes through. |
| 5 | `icmp type echo-request accept` | Allow **ping** (ICMP echo request) directed at VM1. Useful for connectivity testing and network diagnostics. |
| 6 | `ip saddr 10.0.0.5 tcp dport 5001 accept` | Allow **only VM2** (`10.0.0.5`) to reach the **Decision Engine API** on port `5001`. This is the internal communication channel where VM2 sends malware alerts. No external host can access this API. |

#### Chain: `forward`

Filters traffic **passing through VM1** (routed between `enp0s3` and `enp0s8`).

```nft
type filter hook forward priority filter; policy drop;
```
- **Hook:** `forward` — applies to packets being routed through this machine.
- **Policy:** `drop` — **default deny**. No traffic is forwarded unless explicitly permitted.

| # | Rule | Explanation |
|---|------|-------------|
| 1 | `ip saddr @blocked_ips drop` | Drop forwarded traffic from blocked IPs. This is the **primary enforcement point** — even if an attacker's packet reaches the forward chain, it is dropped here before any forwarding occurs. Note: no `counter` here (lighter weight), and no `ct state` check since blocked IPs should never establish anything. |
| 2 | `ct state established,related accept` | Allow return traffic for **connections initiated by VM2**. When VM2 makes an outbound request (e.g., `apt update`, DNS query), the reply packets from the internet are allowed back through. This is critical for VM2's internet access. |
| 3 | `iif "enp0s8" oif "enp0s3" accept` | Allow **all outbound traffic** from the internal network (`enp0s8`) to the external network (`enp0s3`). VM2 can reach any destination on the internet. In production, this would be restricted to specific ports, but for the prototype it is permissive to allow `apt`, `curl`, etc. |
| 4 | `iif "enp0s3" oif "enp0s8" tcp dport 80 ct state new accept` | Allow **new inbound HTTP connections** from the internet (`enp0s3`) to VM2 (`enp0s8`) on port 80. This is the **only** inbound service exposed to the internet. The `ct state new` ensures only new connection attempts match (established ones are caught by rule 2). |
| 5 | `ct state new tcp flags syn limit rate 40/second burst 100 packets accept` | **SYN flood protection**: Allow new TCP SYN packets at a maximum rate of **40 per second** with a burst allowance of 100 packets. This mitigates TCP SYN flood attacks by rate-limiting new connection attempts. |
| 6 | `tcp flags syn drop` | Drop any TCP SYN packets that **exceeded the rate limit** in rule 5. This silently discards excess connection attempts, protecting VM1 and VM2 from resource exhaustion. |
| 7 | `icmp type {echo-reply, destination-unreachable, echo-request, time-exceeded} accept` | Allow essential ICMP types for forwarded traffic: echo-reply (ping responses), destination-unreachable (path MTU discovery), echo-request (ping through), and time-exceeded (traceroute). |
| 8 | `meta l4proto udp ct state new limit rate 100/second burst 50 packets accept` | Allow new UDP connections at **100 per second** with a burst of 50. This controls DNS and other UDP-based services while preventing UDP flood attacks. |
| 9 | `meta l4proto udp drop` | Drop any UDP traffic that exceeded the rate limit in rule 8. |

#### Table: `ip nat`

Uses the `ip` family (IPv4 only) for **Network Address Translation** rules.

#### Chain: `prerouting`

```nft
type nat hook prerouting priority dstnat; policy accept;
```
- **Hook:** `prerouting` — applies to packets **before** routing decisions are made.
- **Priority:** `dstnat` — destination NAT.

| # | Rule | Explanation |
|---|------|-------------|
| 1 | `iif "enp0s3" tcp dport 80 dnat to 10.0.0.5:80` | **DNAT (Port Forwarding):** Any TCP traffic arriving on the external interface (`enp0s3`) destined for port 80 is **redirected** to VM2 at `10.0.0.5:80`. This makes the internal web server accessible from the internet through VM1's public IP. The `iif` restriction ensures this only applies to external traffic, not internal. |

#### Chain: `postrouting`

```nft
type nat hook postrouting priority srcnat; policy accept;
```
- **Hook:** `postrouting` — applies to packets **after** routing, just before they leave the machine.
- **Priority:** `srcnat` — source NAT.

| # | Rule | Explanation |
|---|------|-------------|
| 1 | `oif "enp0s3" masquerade` | **SNAT (Masquerading):** All traffic leaving through the external interface (`enp0s3`) has its **source IP replaced** with VM1's external IP. This allows VM2 (`10.0.0.5`) to access the internet while appearing to come from VM1 (`192.168.1.10`). The kernel automatically tracks these mappings via `conntrack` so return traffic is correctly translated back. |

---

## Traffic Flow Diagram

```
                         Internet
                            │
                            ▼
                    ┌───────────────┐
                    │    enp0s3     │  ← 192.168.1.10 (External)
                    │  [PREROUTING] │  DNAT: 80 → 10.0.0.5:80
                    │    [INPUT]    │  Filter: SSH, DNS, HTTP, HTTPS, ICMP, API
                    │   [FORWARD]   │  Filter: Blocked IPs, stateful, rate limits
                    │   [POSTROUTE] │  SNAT: masquerade outbound
                    └───────┬───────┘
                            │ ngfw-net
                            ▼
                    ┌───────────────┐
                    │    enp0s8     │  ← 10.0.0.1 (Internal Gateway)
                    └───────┬───────┘
                            ▼
                    ┌───────────────┐
                    │   VM2 Server  │  ← 10.0.0.5 (Web App)
                    └───────────────┘
```

### Inbound Web Request (External → VM2)
1. Packet arrives at `enp0s3` with `dst=192.168.1.10:80`
2. **PREROUTING:** DNAT changes `dst` to `10.0.0.5:80`
3. **FORWARD chain:** Passes through `input` → `forward` → allowed by `iif enp0s3 oif enp0s8 tcp dport 80 ct state new`
4. Packet forwarded to VM2 via `enp0s8`

### Outbound Request (VM2 → Internet)
1. VM2 sends packet with `src=10.0.0.5`
2. Packet arrives at VM1 `enp0s8`, routed to `enp0s3`
3. **FORWARD chain:** Allowed by `iif enp0s8 oif enp0s3 accept` and `ct state established,related` for return traffic
4. **POSTROUTING:** Masquerade changes `src` to `192.168.1.10`
5. Packet exits to internet with VM1's IP

**Architecture Note:** VM1 handles all threat detection and IP blocking independently. VM2 does NOT communicate with VM1. All traffic is inspected by Suricata on VM1 before being forwarded to VM2.

---

## Essential nftables Commands

### Viewing Rules

| Command | Purpose |
|---------|---------|
| `sudo nft list ruleset` | Display the complete active ruleset |
| `sudo nft list table inet firewall` | Show only the firewall filtering table |
| `sudo nft list table ip nat` | Show only the NAT table |
| `sudo nft list set inet firewall blocked_ips` | List currently blocked IPs and their remaining TTL |
| `sudo nft list ruleset -a` | Show ruleset with **rule handles** (numeric IDs needed for deletion) |
| `sudo nft list ruleset -j` | Output ruleset in **JSON format** (for programmatic parsing) |
| `sudo nft monitor` | Live monitor of nftables events (packet counters, new elements, etc.) |

### Managing the Blocked IPs Set

| Command | Purpose |
|---------|---------|
| `sudo nft add element inet firewall blocked_ips { 192.168.1.50 }` | Block IP with default TTL |
| `sudo nft add element inet firewall blocked_ips { 192.168.1.50 timeout 30m }` | Block IP for 30 minutes |
| `sudo nft add element inet firewall blocked_ips { 192.168.1.50 timeout 24h }` | Block IP for 24 hours |
| `sudo nft delete element inet firewall blocked_ips { 192.168.1.50 }` | Manually unblock IP before TTL expires |
| `sudo nft flush set inet firewall blocked_ips` | **Emergency:** remove all blocks immediately |

### Applying and Persisting Rules

| Command | Purpose |
|---------|---------|
| `sudo nft -f /etc/nftables.conf` | Load rules from config file |
| `sudo nft -c -f /etc/nftables.conf` | **Dry-run:** validate config without applying |
| `sudo nft flush ruleset` | Remove all rules (⚠️ may lock you out if SSH rule is missing) |
| `sudo systemctl restart nftables` | Restart the nftables systemd service |
| `sudo systemctl enable nftables` | Enable nftables to start on boot |
| `sudo systemctl status nftables` | Check service status |

### Debugging and Troubleshooting

| Command | Purpose |
|---------|---------|
| `sudo conntrack -L` | List all active connection tracking entries (NAT mappings) |
| `sudo conntrack -L --orig-src 192.168.1.50` | Find connections from a specific IP |
| `sudo conntrack -L -p tcp --dport 80` | Find connections to port 80 |
| `sudo nft add rule inet firewall forward counter` | Add a packet counter for debugging (insert at desired position) |
| `sudo nft delete rule inet firewall forward handle <N>` | Delete a specific rule by handle number |
| `dmesg \| grep -i nft` | Check kernel messages for nftables errors |

---

## How to Recreate This Configuration from Scratch

### Step 1: Enable IP Forwarding

The kernel must be told to route packets between interfaces.

```bash
# Enable immediately
sudo sysctl -w net.ipv4.ip_forward=1

# Make persistent across reboots
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.d/99-ipforward.conf
sudo sysctl -p /etc/sysctl.d/99-ipforward.conf
```

Verify:
```bash
sysctl net.ipv4.ip_forward
# Expected output: net.ipv4.ip_forward = 1
```

### Step 2: Identify Network Interfaces

```bash
ip -br addr show
```

Note the interface names:
- **External interface** (bridged/NAT adapter): e.g., `enp0s3`
- **Internal interface** (internal network adapter): e.g., `enp0s8`

Update all rules in the configuration below to match your actual interface names.

### Step 3: Write the Configuration File

```bash
sudo nano /etc/nftables.conf
```

Paste the complete ruleset (from the "Complete Ruleset" section above), adjusting:
- Interface names (`enp0s3`, `enp0s8`) to match your system
- VM2 IP (`10.0.0.5`) if different
- External subnet if different

### Step 4: Validate the Configuration

```bash
sudo nft -c -f /etc/nftables.conf
```

If no errors are printed, the configuration is syntactically valid.

### Step 5: Apply the Configuration

```bash
sudo nft -f /etc/nftables.conf
```

### Step 6: Verify the Active Ruleset

```bash
sudo nft list ruleset
```

Compare the output with your configuration file to confirm everything loaded correctly.

### Step 7: Test Connectivity

```bash
# From VM2, test outbound internet access
curl -I https://www.google.com

# From VM2, test that port 80 is reachable through VM1
curl http://192.168.1.10

# From external host, test web access through VM1
curl http://192.168.1.10

# From external host, test that SSH to VM2 is blocked
ssh 192.168.1.10 -p 22  # Should connect to VM1, not VM2
ssh 10.0.0.5 -p 22      # Should timeout (not routable from outside)
```

### Step 8: Test Dynamic Blocking

```bash
# Block a test IP
sudo nft add element inet firewall blocked_ips { 192.168.1.99 timeout 5m }

# Verify it appears in the set
sudo nft list set inet firewall blocked_ips

# Test that the IP cannot reach VM1 or VM2
# (from 192.168.1.99, ping and curl should fail)

# Wait 5 minutes and verify auto-expiry, or manually remove:
sudo nft delete element inet firewall blocked_ips { 192.168.1.99 }
```

### Step 9: Enable nftables on Boot

```bash
sudo systemctl enable nftables
sudo systemctl start nftables
```

The `nftables.service` on Ubuntu automatically loads `/etc/nftables.conf` at boot. The `flush ruleset` directive at the top of the file ensures a clean state before applying rules.

---

## 🚨 Current Issues & Fixes (As of May 2, 2026)

**Architecture Note:** VM1 handles all threat detection and IP blocking independently. VM2 does NOT communicate with VM1. Suricata on VM1 sees real source IPs directly (no NAT correlation needed).

### Issue #1: Malware Upload Blocking

**Symptom:** When uploading EICAR test file, malware is detected and uploader's IP IS blocked.

**Fix Implemented:**
- Removed unnecessary conntrack correlation code from `suri_clam_processor.py`
- VM1 sees real `src_ip` directly from Suricata events
- `process_fileinfo_event()` uses `src_ip` from event to block attacker
- Blocks uploader's IP for 24h via `/api/block_ip`

**Status:** ✅ Working

---

### Issue #2: False Blocks from Legitimate Traffic

**Symptom:** Host IP (192.168.1.9) blocked when visiting Notion.so or uploading clean JSON files.

**Root Causes Fixed:**
1. **ET INFO rules** (SID 2038646) now skipped via `severity_to_block_action()`
2. **`/upload` endpoint** has `pass` rule in Suricata (SID 1000000)
3. **Clean JSON uploads** only scanned by ClamAV, not custom SQLi rules

**Status:** ✅ Fixed

---

### Issue #3: SSH to VM2 Not Working

**Symptom:** SSH connection to `10.0.0.5:22` failing with `Permission denied`.

**Root Cause:** Missing `sshpass` package + incorrect assumption about credentials.

**Fix Implemented:**
- Installed `sshpass` on VM1
- Verified credentials: `ubuntuhero` / `ubuntuhero4433`
- Added SSH port 22 to nftables forward chain

**Status:** ✅ Working. Test with:
```bash
sshpass -p 'ubuntuhero4433' ssh -o StrictHostKeyChecking=no ubuntuhero@10.0.0.5
```

---

## Security Posture Summary

| Principle | Status | Implementation |
|-----------|--------|----------------|
| Default Deny | ✅ | `policy drop` on both `input` and `forward` chains |
| Stateful Filtering | ✅ | `ct state established,related accept` on all chains |
| Dynamic Blocking | ✅ | `blocked_ips` set with TTL-based auto-expiry |
| SYN Flood Protection | ✅ | Rate limit 40 SYN/sec with burst of 100 |
| UDP Flood Protection | ✅ | Rate limit 100 UDP/sec with burst of 50 |
| Interface Binding | ✅ | `iif`/`oif` rules bind traffic to correct interfaces, preventing spoofing |
| Least Exposure | ✅ | Only port 80 inbound to VM2; no other forwarded services |
| API Isolation | ✅ | Decision Engine API (5001) accessible only from VM2 (`10.0.0.5`) |
| NAT Transparency | ✅ | Masquerade for outbound; DNAT for inbound HTTP only |

---

## Important Notes

1. **Interface Names May Differ:** The interface names `enp0s3` and `enp0s8` are specific to this VM1 instance. On a different system, they may be `eth0`/`eth1`, `ens33`/`ens34`, etc. Always verify with `ip link` before applying rules.

2. **The `flush ruleset` Directive:** The first line of `/etc/nftables.conf` is `flush ruleset`. This **deletes all existing nftables rules** before applying the new configuration. If you have other nftables-managed services (e.g., Docker, libvirt), this will interfere with them. In such cases, replace `flush ruleset` with targeted table deletions.

3. **SSH Access Warning:** The `input` chain allows SSH (port 22) from **any source**. If you apply this configuration remotely and your SSH port is not 22, or if a rule mistake blocks your connection, you will be locked out. Always test with a fallback access method (console access, secondary SSH port, or cron-based rule revert).

4. **IPv6:** The `inet firewall` table supports both IPv4 and IPv6, but the rules primarily target IPv4 (`ip saddr`, `type ipv4_addr`). IPv6-specific rules may need to be added for production use.

5. **Outbound Traffic from VM2:** The forward chain allows **all outbound traffic** from VM2 to the internet (`iif "enp0s8" oif "enp0s3" accept`). In a production environment, this should be restricted to specific protocols (HTTP/HTTPS/DNS only) to prevent data exfiltration.
