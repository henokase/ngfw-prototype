# Setup & Deployment Guide

Instructions for provisioning the two-VM NGFW lab environment.

## Network Topology

```
┌─────────────────────────────────────────────────────┐
│  Host Machine                                       │
│                                                     │
│  ┌───────────────────┐     ┌───────────────────┐    │
│  │  VM1 (Gateway)    │     │  VM2 (Web Server) │    │
│  │  Ubuntu Desktop   │     │  Ubuntu Server    │    │
│  │                   │     │                   │    │
│  │  enp0s3: NAT      │     │  enp0s8: ngfw-net │    │
│  │  10.0.2.15        │     │  10.0.0.5         │    │
│  │                   │     │                   │    │
│  │  enp0s8: ngfw-net │     │                   │    │
│  │  10.0.0.1         │     │                   │    │
│  └────────┬──────────┘     └─────────▲─────────┘    │
│           │                          │              │
│           └──────── DNAT ────────────┘              │
│           Forward to VM2:80                         │
└─────────────────────────────────────────────────────┘
```

### Network Configuration

| Interface | VM1 | VM2 | Purpose |
|-----------|-----|-----|---------|
| `enp0s3` | NAT (10.0.2.15) | N/A | Internet access |
| `enp0s8` | ngfw-net (10.0.0.1) | ngfw-net (10.0.0.5) | Internal network |

---

## VM1 Setup (Gateway/Firewall)

### 1. Install OS & Configure Networking

- **OS**: Ubuntu Desktop 24.04 LTS
- **Adapters**:
  - Adapter 1: NAT
  - Adapter 2: Internal Network (`ngfw-net`), static IP `10.0.0.1/24`

```bash
# Configure static IP on enp0s8
sudo tee /etc/netplan/01-ngfw.yaml << 'EOF'
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      addresses: [10.0.0.1/24]
      dhcp4: false
EOF
sudo netplan apply
```

### 2. Enable IP Forwarding & NAT

```bash
# Enable forwarding
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.d/99-ngfw.conf

# Configure NAT (Masquerade VM2 traffic out through enp0s3)
sudo iptables -t nat -A POSTROUTING -o enp0s3 -j MASQUERADE

# DNAT: forward port 80 traffic to VM2
sudo iptables -t nat -A PREROUTING -i enp0s3 -p tcp --dport 80 -j DNAT --to-destination 10.0.0.5:5000

# Allow forwarding
sudo iptables -A FORWARD -i enp0s8 -o enp0s3 -j ACCEPT
sudo iptables -A FORWARD -i enp0s3 -o enp0s8 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Persist iptables
sudo apt install iptables-persistent -y
sudo netfilter-persistent save
```

### 3. Install nftables

```bash
sudo apt update && sudo apt install nftables -y
sudo systemctl enable nftables

# Create baseline nftables ruleset
sudo tee /etc/nftables.conf << 'EOF'
#!/usr/sbin/nft -f
flush ruleset

table inet firewall {
    set blocked_ips {
        type ipv4_addr
        flags timeout
        timeout 1h
    }

    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        tcp dport 22 accept
        tcp dport 5001 accept
        ip saddr @blocked_ips counter drop
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
        ct state established,related accept
        iif enp0s8 oif enp0s3 accept
        tcp dport 80 accept
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
EOF

sudo systemctl restart nftables
sudo nft list ruleset
```

### 4. Install ClamAV

```bash
sudo apt install clamav clamav-daemon -y
sudo systemctl stop clamav-freshclam
sudo freshclam
sudo systemctl start clamav-freshclam
sudo systemctl enable clamav-daemon
sudo systemctl start clamav-daemon
```

### 5. Install Suricata

```bash
sudo apt install suricata -y
sudo suricata-update
sudo systemctl enable suricata
sudo systemctl start suricata
```

### 6. Deploy ngfw-control API

```bash
sudo apt install python3 python3-pip python3-venv conntrack -y

cd /opt
sudo mkdir -p ngfw-control
sudo chown $USER:$USER ngfw-control
# Copy ngfw-control/ files here
cd ngfw-control

python3 -m venv venv
source venv/bin/activate
pip install flask sqlalchemy

# Test
python3 app.py
# API should be listening on 0.0.0.0:5001
```

### 7. Create systemd Service (Optional)

```bash
sudo tee /etc/systemd/system/ngfw-control.service << 'EOF'
[Unit]
Description=NGFW Control API
After=network.target nftables.service

[Service]
Type=simple
User=ubuntuhero
WorkingDirectory=/opt/ngfw-control
Environment=PATH=/opt/ngfw-control/venv/bin
ExecStart=/opt/ngfw-control/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ngfw-control
```

### 8. Configure Suricata Rules

Suricata should be configured to:
- Monitor traffic on `enp0s8` (LAN) or `enp0s3` (WAN)
- Use `file-store` to extract uploaded files from HTTP traffic
- Trigger on malware signatures
- Use a script or hook to scan extracted files with ClamAV and block IPs via nftables

Example Suricata configuration excerpt (`/etc/suricata/suricata.yaml`):

```yaml
outputs:
  - fast:
      enabled: yes
      filename: fast.log
  - file-store:
      version: 2
      enabled: yes
      force-magic: no
```

---

## VM2 Setup (Web Server)

### 1. Install OS & Configure Networking

- **OS**: Ubuntu Server 24.04 LTS
- **Adapters**:
  - Adapter 1: Internal Network (`ngfw-net`), static IP `10.0.0.5/24`

```bash
sudo tee /etc/netplan/01-ngfw.yaml << 'EOF'
network:
  version: 2
  ethernets:
    enp0s8:
      addresses: [10.0.0.5/24]
      nameservers:
        addresses: [10.0.0.1, 8.8.8.8]
      routes:
        - to: default
          via: 10.0.0.1
          on-link: true
      dhcp4: false
EOF
sudo netplan apply
```

### 2. Install Dependencies

```bash
sudo apt update && sudo apt install -y python3 python3-venv clamav clamav-daemon
```

### 3. Set Up Python Virtual Environment

```bash
python3 -m venv /home/ubuntuhero/ngfw
source /home/ubuntuhero/ngfw/bin/activate
```

### 4. Deploy the Web Application

```bash
# Clone or copy the project to /home/ubuntuhero/ngfw-prototype
cd /home/ubuntuhero/ngfw-prototype/web

# Ensure directories exist
mkdir -p instance logs uploads/safe uploads/quarantine

# Start the application
source /home/ubuntuhero/ngfw/bin/activate
python3 app.py
```

The app listens on `0.0.0.0:5000`.

### 5. Production Deployment with Gunicorn

```bash
pip install gunicorn

# Test
gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app

# Create systemd service
sudo tee /etc/systemd/system/ngfw-web.service << 'EOF'
[Unit]
Description=NGFW Test Web Application
After=network.target clamav-daemon.service

[Service]
Type=notify
User=ubuntuhero
WorkingDirectory=/home/ubuntuhero/ngfw-prototype/web
Environment=PATH=/home/ubuntuhero/ngfw/bin
ExecStart=/home/ubuntuhero/ngfw/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ngfw-web
```

---

## Verification

### VM1 Checks

```bash
# nftables loaded
sudo nft list ruleset

# nftables blocked_ips set exists
sudo nft list set inet firewall blocked_ips

# API responding
curl http://10.0.0.1:5001/api/health
# Expected: {"status": "ok", "db": "ok"}

# ClamAV running
systemctl status clamav-daemon

# Suricata running
systemctl status suricata
```

### VM2 Checks

```bash
# Web app responding
curl http://10.0.0.5:5000/health
# Expected: {"status": "healthy", "database": "connected", ...}

# ClamAV running
systemctl status clamav-daemon

# Upload stats
curl http://10.0.0.5:5000/upload/stats
```

### End-to-End Test (from host machine)

```bash
# Access the web app through VM1's NAT
curl http://<VM1_EXTERNAL_IP>/
curl http://<VM1_EXTERNAL_IP>/health

# Upload EICAR test file
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > eicar.com
curl -X POST -F "file=@eicar.com" http://<VM1_EXTERNAL_IP>/upload
```

VM1's Suricata should detect the file upload, extract it, scan with ClamAV, and block the source IP.

---

## Troubleshooting

### VM2 cannot reach internet
```bash
# Check default route on VM2
ip route
# Should show: default via 10.0.0.1 dev enp0s8

# Check forwarding on VM1
sysctl net.ipv4.ip_forward
# Should be: net.ipv4.ip_forward = 1

# Check NAT on VM1
sudo iptables -t nat -L POSTROUTING -v
```

### ClamAV not responding on VM2
```bash
sudo systemctl status clamav-daemon
sudo freshclam
sudo systemctl restart clamav-daemon
```

### Web app database errors
```bash
cd /home/ubuntuhero/ngfw-prototype/web
rm instance/database.db
python3 app.py  # Will recreate and seed
```

### nftables rules not persisting
```bash
sudo nft list ruleset > /etc/nftables.conf
sudo systemctl restart nftables
```
