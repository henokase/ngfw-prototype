### *Packet Filtering + NAT + Decision Engine API + System Hardening + Automation Scripts*

---

# 🔰 **PHASE 3 OBJECTIVE**

Turn VM1 into a *fully functional filtering gateway* with:

1. **Hardened nftables firewall**
2. **NAT forwarding to VM2**
3. **Dynamic blocklist with TTL**
4. **Decision Engine Control API (Flask service)**
5. **Logging system (SQLite or MongoDB)**
6. **Automation scripts for block/unblock/list**
7. **Kernel-level protections (SYN cookies, conntrack hardening)**
8. **Rate-limiting rules**

This foundation is required before adding Suricata (Phase 4) and ML (Phase 5).

---

# 🚀 **PHASE 3 DETAILED WORKFLOW**

---

# **STEP 1 — Confirm and Polish nftables Ruleset**

🟢 You already have NAT + filtering.

🔴 But you need to **polish/harden** it.

---

## ✔ **1.1 Validate Interfaces**

You must know:

- `enp0s3` = NAT interface (to host/internet)
- `enp0s8` = LAN interface (to VM2)

Check:

```bash
ip a
```

---

## ✔ **1.2 Ensure Default DROP**

This is already done, but confirm:

```
chain input { ... policy drop; }
chain forward { ... policy drop; }
```

---

## ✔ **1.3 Improve SYN Flood Protection**

Add this rule inside `forward`:

```
tcp flags syn ct state new limit rate 40/second burst 100 accept
tcp flags syn drop

```

---

## ✔ **1.4 Rate-limit ICMP (Ping Flood Protection)**

```
icmp type echo-request limit rate 10/second burst 20 accept
icmp type echo-request drop

```

---

## ✔ **1.5 Add Generic UDP Flood Protection**

```
udp ct state new limit rate 100/second accept
udp drop

```

---

### 🔒 Result:

Your firewall now has **basic DoS protection** BEFORE packets hit VM2.

---

# **STEP 2 — Enable Kernel-Level Protections (Sysctl Hardening)**

Create/edit:

```
sudo nano /etc/sysctl.d/99-ngfw.conf

```

Add:

```
# SYN Flood Protection
net.ipv4.tcp_syncookies = 1

# Reduce TCP backlog abuse
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 3

# Disable IP forwarding by default (already enabled manually)
net.ipv4.ip_forward = 1

# Reverse path filtering (anti-IP spoofing)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
```

Apply:

```bash
sudo sysctl --system
```

---

# **STEP 3 — Create Directory Structure for Decision Engine**

Create folder:

```
sudo mkdir -p /opt/ngfw-control
cd /opt/ngfw-control
```

Inside, you will have:

```
/opt/ngfw-control
│── app.py                  # Main Flask API
│── firewall_service.py     # Wrapper for nftables operations
│── database.py             # SQLite helper
│── logger.py               # Logging manager
│── requirements.txt
│── ngfw.db                 # SQLite DB (auto-created)

```

---

# **STEP 4 — Implement the SQLite Database Layer**

### 4.1 Create schema

SQLite stores:

- blocked IPs
- reason
- TTL
- log messages (optional)

Schema (conceptual):

```
Table: blocks
-----------------------------
id INTEGER PRIMARY KEY
ip TEXT
reason TEXT
timestamp TEXT
ttl INTEGER   # seconds

Table: logs
------------------------------
id INTEGER PRIMARY KEY
source TEXT
event TEXT
data TEXT
timestamp TEXT

```

### Pseudocode: `database.py`

```python
init_db():
    create 'blocks' table if not exists
    create 'logs' table if not exists

add_block(ip, reason, ttl):
    insert row into blocks

log_event(source, event, data):
    insert row into logs

get_blocks():
    return all rows

```

---

# **STEP 5 — Implement nftables Wrapper (firewall_service.py)**

This file handles:

- Adding IP to nftables set
- Removing IP
- Listing blocks
- Validating IP addresses

### Pseudocode:

```python
add_block(ip, ttl):
    run command:
    "sudo nft add element inet firewall blocked_ips { ip timeout TTL }"

remove_block(ip):
    run:
    "sudo nft delete element inet firewall blocked_ips { ip }"

is_valid_ip(ip):
    Validate with regex or ipaddress module

```

---

# **STEP 6 — Implement the Decision Engine API (app.py)**

### Flask app must include endpoints:

| Route | Purpose |
| --- | --- |
| `POST /api/block_ip` | Add IP to nftables and DB |
| `POST /api/unblock_ip` | Remove IP |
| `POST /api/log_detection` | Store arbitrary logs |
| `GET /api/list_blocks` | Inspect blocks |
| `GET /api/health` | System heartbeat |

### Pseudocode:

```python
@app.route('/api/block_ip', methods=['POST'])
def block_ip():
    ip = request.json['ip']
    reason = request.json.get('reason')
    ttl = request.json.get('ttl', '1h')

    if firewall_service.add_block(ip, ttl):
        database.add_block(ip, reason, ttl)
        logger.warn(f"Blocked IP {ip} for reason: {reason}")
        return {"success": True}

```

---

# **STEP 7 — Create Automation CLI Scripts**

Place in:

```
/usr/local/bin/

```

### 7.1 block

```bash
sudo nano /usr/local/bin/block

```

```bash
#!/bin/bash
IP=$1
TTL=${2:-1h}
sudo nft add element inet firewall blocked_ips "{ $IP timeout $TTL }"
echo "Blocked $IP for $TTL"

```

### 7.2 unblock

```bash
sudo nft delete element inet firewall blocked_ips "{ $IP }"

```

### 7.3 listblocked

```bash
sudo nft list set inet firewall blocked_ips

```

Make executable:

```bash
sudo chmod +x /usr/local/bin/block
sudo chmod +x /usr/local/bin/unblock
sudo chmod +x /usr/local/bin/listblocked

```

---

# **STEP 8 — Turn the API into a Systemd Service**

Create:

```
sudo nano /etc/systemd/system/ngfw-control.service

```

Contents:

```
[Unit]
Description=NGFW Control API
After=network.target

[Service]
User=root
WorkingDirectory=/opt/ngfw-control
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target

```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ngfw-control

```

---

# **STEP 9 — Test the API and Blocklist**

### 9.1 Send test block

```bash
curl -X POST http://10.0.0.1:5000/api/block_ip \
     -H "Content-Type: application/json" \
     -d '{"ip": "192.168.1.50", "reason": "test"}'

```

### 9.2 Confirm with nftables

```bash
sudo nft list set inet firewall blocked_ips

```

### 9.3 Test traffic drop

From host machine:

Try accessing VM2 site → should be blocked.

---

# **STEP 10 — Integrate with VM2 File Scan Alerts**

(You already know this structure, but now Phase 3’s API is ready.)

VM2 just does:

```python
requests.post(
    "http://10.0.0.1:5000/api/block_ip",
    json={
        "ip": detected_client_ip,
        "reason": "malware_upload",
        "signature": signature,
        "ttl": "1h"
    }
)

```

Done.

---

# 🏁 **RESULT: PHASE 3 FULLY COMPLETED**

After following this workflow, VM1 will have:

- Full nftables firewall with DoS hardening
- NAT gateway
- Dynamic blocklist with TTL
- A central NGFW Decision Engine with REST API
- Logging stored in SQLite
- Wrapper CLI tools
- Kernel-level protection (sysctl)
- Integration points for Suricata + ML + VM2 alerts

This satisfies *100% of Phase 3 requirements* and prepares the system for Phase 4 (Suricata).

---

If you want, I can now generate:

✔ The actual full code (app.py, firewall_service.py, database.py)

✔ The exact folder structure

✔ The systemd-ready version

✔ NAT+filter final ruleset

Just say **"Generate Phase 3 full code"** and I’ll produce everything cleanly.