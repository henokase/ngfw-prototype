# VM1 Suricata Deep Packet Inspection Configuration

## System Environment

| Component | Value |
|-----------|-------|
| VM Role | NGFW Gateway (VM1) |
| OS | Ubuntu Desktop |
| Suricata Version | 8.0.2 RELEASE |
| Suricata Service | `suricata.service` (systemd, enabled, running) |
| Kernel | 6.14.0-37-generic |
| nftables Version | v1.0.9 |
| Rule Count | 47,309 rules (Emerging Threats) + 13 custom rules (SID 1000000-1000061) |
| PID | 12375 |
| Uptime | Active since Fri 2026-05-01 18:30 |

### Updates (May 1, 2026):
- **Custom rules updated:** Added `pass` rule for `/upload` endpoint (SID 1000000)
- **Custom rules added:** 13 content-based rules (no pcre) for SQLi, XSS, Path Traversal, XXE, Open Redirect
- **EVE JSON logging:** Alert logging enabled (`enabled: yes` in `eve-log` types)

## Network Topology (Relevant to Suricata)

| Interface | Name | IP Address | Role | Suricata Monitoring |
|-----------|------|------------|------|---------------------|
| External | `enp0s3` | `192.168.1.10` | Bridged — internet-facing | AF_PACKET cluster_id 99 |
| Internal | `enp0s8` | `10.0.0.1` | Internal — `ngfw-net` | AF_PACKET cluster_id 100 |
| Loopback | `lo` | `127.0.0.1` | Local | Not monitored |

**Protected Server (VM2):** `10.0.0.5` (connected via `enp0s8`)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `/etc/suricata/suricata.yaml` | Main Suricata configuration |
| `/var/lib/suricata/rules/suricata.rules` | Emerging Threats ruleset (63,118 rules) |
| `/var/lib/suricata/rules/local.rules` | Custom project-specific rules |
| `/etc/suricata/classification.config` | Alert classification definitions |
| `/etc/suricata/reference.config` | Reference URL mappings for rule IDs |

---

## Key Configuration Parameters

### Variable Definitions

```yaml
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    EXTERNAL_NET: "!$HOME_NET"
    HTTP_SERVERS: "$HOME_NET"
    SMTP_SERVERS: "$HOME_NET"
    SQL_SERVERS: "$HOME_NET"
    DNS_SERVERS: "$HOME_NET"
    TELNET_SERVERS: "$HOME_NET"
    DC_SERVERS: "$HOME_NET"
    DNP3_SERVER: "$HOME_NET"
    MODBUS_CLIENT: "$HOME_NET"
    MODBUS_SERVER: "$HOME_NET"
    ENIP_CLIENT: "$HOME_NET"
    ENIP_SERVER: "$HOME_NET"
  port-groups:
    HTTP_PORTS: "80"
    SHELLCODE_PORTS: "!80"
    ORACLE_PORTS: 1521
    SSH_PORTS: 22
    DNP3_PORTS: 20000
    MODBUS_PORTS: 502
    FILE_DATA_PORTS: "[$HTTP_PORTS,110,143]"
    FTP_PORTS: 21
    GENEVE_PORTS: 6081
    VXLAN_PORTS: 4789
    TEREDO_PORTS: 3544
    SIP_PORTS: "[5060, 5061]"
```

| Variable | Value | Meaning |
|----------|-------|---------|
| `HOME_NET` | Private RFC 1918 ranges | Defines the protected network space — any traffic to/from these ranges is treated as internal |
| `EXTERNAL_NET` | `!$HOME_NET` | Everything outside `HOME_NET` — used as the source for attack rules |
| `HTTP_SERVERS` | `$HOME_NET` | All internal hosts are treated as potential web servers |
| `HTTP_PORTS` | `80` | Standard HTTP port for rule matching |
| `FILE_DATA_PORTS` | `80, 110, 143` | Ports where Suricata will inspect file content (HTTP, POP3, IMAP) |

### Address Group Explanation

The `HOME_NET` covers three private ranges:
- `192.168.0.0/16` — the external bridged network where the host and VM1 reside
- `10.0.0.0/8` — the internal `ngfw-net` where VM2 resides
- `172.16.0.0/12` — standard private range for completeness

This means **all private IP traffic is considered internal**, and Suricata rules that target `EXTERNAL_NET` will fire only against truly external (public) addresses.

---

## Capture Method: AF_PACKET

Suricata captures traffic using the Linux **AF_PACKET** socket interface, which operates at the kernel level and bypasses the standard network stack for performance.

```yaml
af-packet:
  - interface: enp0s3
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
  - interface: enp0s8
    cluster-id: 100
    cluster-type: cluster_flow
    defrag: yes
  - interface: default
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `interface` | `enp0s3`, `enp0s8` | Suricata monitors **both interfaces simultaneously** — external ingress and internal traffic |
| `cluster-id` | `99`, `100` | Unique identifier per interface for kernel packet distribution. Ensures packets from the same flow always go to the same worker thread |
| `cluster-type` | `cluster_flow` | Packets belonging to the same flow (same 5-tuple: src IP, dst IP, src port, dst port, protocol) are delivered to the same thread. This is critical for **stateful protocol parsing** and TCP stream reassembly |
| `defrag` | `yes` | Kernel-level IP defragmentation is enabled. Suricata reassembles fragmented IP packets before inspection, preventing fragmentation evasion attacks |
| `interface: default` | — | Fallback interface; if no specific interface is matched, this rule applies. Effectively a catch-all |

### Why AF_PACKET?

- **Zero-copy**: Packets are passed directly from kernel to userspace without copying, minimizing CPU overhead
- **Multi-threading**: Combined with `cluster_flow`, Suricata can distribute packet processing across multiple CPU cores
- **Promiscuous mode**: Captures all packets on the wire, not just those destined for the VM
- **No libpcap overhead**: More efficient than PCAP-based capture, which is designed for analysis rather than real-time IDS

---

## Output Configuration

### EVE JSON Log (Primary Output)

```yaml
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: /var/log/suricata/eve.json
      metadata: yes
      suricata-version: yes
      pcap-file: false
      community-id: true
      community-id-seed: 0
```

EVE (Extensible Event Format) is Suricata's **primary structured output**. Every detected event is written as a single-line JSON object, making it easy to parse by downstream tools (the `suri_clam_processor.py` tails this file).

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `filetype` | `regular` | Writes to a flat file. Alternatives: `syslog`, `unix_dgram`, `unix_stream`, `redis` |
| `filename` | `/var/log/suricata/eve.json` | Absolute path to the log file. Currently 134 MB (as of Apr 30, 2026) |
| `metadata` | `yes` | Includes Suricata metadata in each event (flow information, timestamps) |
| `suricata-version` | `yes` | Embeds the Suricata version string in each event for compatibility tracking |
| `community-id` | `true` | Generates a standardized flow hash (community ID) for correlating events across different security tools. Uses seed `0` |

### EVE Event Types

The following event types are enabled in the EVE log:

| # | Event Type | Extended | Purpose |
|---|-----------|----------|---------|
| 1 | `alert` | tagged-packets: yes | Rule-triggered alerts (signatures matched) |
| 2 | `frame` | disabled | Raw frame-level data (disabled) |
| 3 | `anomaly` | yes | Protocol anomalies and parsing errors |
| 4 | `http` | yes | HTTP transaction details (method, URL, headers, body) |
| 5 | `dns` | — | DNS query and response logging |
| 6 | `mdns` | — | Multicast DNS events |
| 7 | `tls` | yes | TLS handshake details (certificates, ciphers, JA3/JA4 fingerprints) |
| 8 | `files` | force-magic, force-hash: sha256 | File extraction metadata (SHA-256, MIME type, size) |
| 9 | `smtp` | — | SMTP email transaction details |
| 10 | `websocket` | — | WebSocket connection and message logging |
| 11 | `ftp` | — | FTP session details |
| 12 | `rdp` | — | Remote Desktop Protocol events |
| 13 | `nfs` | — | Network File System operations |
| 14 | `smb` | — | Server Message Block file sharing events |
| 15 | `tftp` | — | Trivial FTP events |
| 16 | `ike` | — | Internet Key Exchange (IPsec) events |
| 17 | `dcerpc` | — | Distributed Computing Environment RPC events |
| 18 | `krb5` | — | Kerberos authentication events |
| 19 | `bittorrent-dht` | — | BitTorrent DHT protocol events |
| 20 | `snmp` | — | Simple Network Management Protocol events |
| 21 | `rfb` | — | Remote Framebuffer (VNC) events |
| 22 | `sip` | — | Session Initiation Protocol (VoIP) events |
| 23 | `quic` | — | QUIC/HTTP/3 protocol events |
| 24 | `ldap` | — | Lightweight Directory Access Protocol events |
| 25 | `pop3` | — | POP3 email retrieval events |
| 26 | `arp` | disabled | ARP events (disabled by default due to noise) |
| 27 | `dhcp` | yes | DHCP lease events |
| 28 | `ssh` | — | SSH session details |
| 29 | `mqtt` | — | MQTT IoT protocol events |
| 30 | `http2` | — | HTTP/2 protocol events |
| 31 | `doh2` | — | DNS over HTTPS events |
| 32 | `pgsql` | disabled | PostgreSQL protocol events |
| 33 | `stats` | totals: yes | Performance statistics per interval |
| 34 | `flow` | — | Flow summary records (created/closed flows) |

### Fast Log

```yaml
  - fast:
      enabled: yes
      filename: fast.log
      append: yes
```

The fast log provides a **human-readable, single-line summary** of each alert. It is the legacy output format and serves as a quick reference. Currently 88 KB in size.

Example:
```
04/30/2026-21:16:36.492102  [**] [1:2210044:2] SURICATA STREAM Packet with invalid timestamp [**] [Classification: Generic Protocol Command Decode] [Priority: 3] {TCP} 172.65.90.21:443 -> 192.168.1.10:58492
```

### Stats Log

```yaml
  - stats:
      enabled: yes
      filename: stats.log
      append: yes
      totals: yes
      threads: no
```

Records **performance statistics** every 8 seconds (as defined by `stats.interval: 8`). Includes packet counts, drop rates, memory usage, and per-module performance. Currently 90 MB — this large size indicates significant traffic volume.

### TLS Store

```yaml
  - tls-store:
      enabled: no
```

Disabled. This would create a separate PEM file for each observed TLS certificate. Not needed since TLS data is already captured in the EVE JSON log (`tls` event type with `extended: yes`).

### PCAP Log

```yaml
  - pcap-log:
      enabled: no
```

Disabled. This would save full packet captures to `.pcap` files. Useful for forensic analysis but consumes significant disk space. Can be enabled for specific testing sessions.

---

## File Extraction and Storage

### File Store Configuration

```yaml
  - file-store:
      version: 2
      enabled: yes
      force-magic: yes
      memcap: 64 MiB
      filename: /var/lib/suricata/files
      limit: 100 MiB
      write-meta: yes
      force-filestore: yes
      stream-depth: 0
      force-hash: [sha256]
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `version` | `2` | File store format version 2 (current standard) |
| `enabled` | `yes` | File extraction is active — Suricata saves files it observes in HTTP traffic |
| `force-magic` | `yes` | Forces MIME type detection (libmagic) on all extracted files |
| `memcap` | `64 MiB` | Maximum memory allocated for file storage operations |
| `filename` | `/var/lib/suricata/files` | Base directory for extracted files |
| `limit` | `100 MiB` | Per-file size limit. Files larger than 100 MB are not fully extracted |
| `write-meta` | `yes` | Writes a `.json` metadata file alongside each extracted file |
| `force-filestore` | `yes` | Forces storage of ALL files (not just those matching rules) |
| `stream-depth` | `0` | Unlimited stream depth — Suricata will inspect the entire TCP stream (0 = no limit) |
| `force-hash` | `[sha256]` | Computes SHA-256 hash for every extracted file |

### Filestore Directory Structure

Files are stored in a **hash-based directory structure** under `/var/log/suricata/filestore/`:

```
/var/log/suricata/filestore/
├── 00/
│   ├── file.0    (extracted file data)
│   ├── file.0.json (metadata: filename, sha256, magic, size, etc.)
│   └── ...
├── 01/
├── ...
├── ff/
└── tmp/
```

The 2-character directory names (`00` through `ff`) correspond to the **first two hex characters of the file's SHA-256 hash**. Currently 256 subdirectories exist (00-ff plus tmp), and the total directory count is growing with traffic.

**Key observation:** The filestore directory was last modified on `Apr 30 18:59` and `Apr 30 20:51`, indicating active file extraction from recent traffic.

---

## Rule Configuration

### Ruleset Location

```yaml
default-rule-path: /var/lib/suricata/rules
rule-files:
  - suricata.rules
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `default-rule-path` | `/var/lib/suricata/rules` | Base directory for all rule files |
| `rule-files` | `suricata.rules` | Main ruleset file loaded |

### Rule Files on Disk

| File | Size | Lines | Purpose |
|------|------|-------|---------|
| `suricata.rules` | 39.6 MB | 63,118 | Emerging Threats (ET) Open ruleset — comprehensive signature database |
| `custom-rules.rules` | 4.2 KB | 60+ | 13 custom rules (SID 1000000-1000061) |
| `classification.config` | 3.2 KB | — | Maps rule classifications to severity levels |
| `reference.config` | — | — | Maps reference IDs to external URLs |

### Custom Rules (`custom-rules.rules`)

**SID Range:** 1000000-1000999 (above ET range, no pcre — compatible with Suricata 8+)

```suricata
# Pass rule: Skip all custom rule checks for /upload endpoint (handled by ClamAV)
pass http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Pass - /upload endpoint"; http.uri; content:"/upload"; sid:1000000; rev:1;)

# SQL Injection (5 rules)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM SQLi Auth Bypass - OR 1=1"; flow:established,to_server; http.request_body; content:"OR"; nocase; content:"="; distance:0; within:20; classtype:web-application-attack; sid:1000010; rev:1; metadata:created_at 2026_05_01, tag SQL_Injection;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM SQLi UNION SELECT"; flow:established,to_server; http.request_body; content:"UNION"; nocase; content:"SELECT"; nocase; distance:0; within:30; classtype:web-application-attack; sid:1000011; rev:1; metadata:created_at 2026_05_01, tag SQL_Injection;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM SQLi UNION SELECT in URI"; flow:established,to_server; http.uri; content:"UNION"; nocase; content:"SELECT"; nocase; distance:0; within:30; classtype:web-application-attack; sid:1000012; rev:1; metadata:created_at 2026_05_01, tag SQL_Injection;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM SQLi Comment Bypass"; flow:established,to_server; http.request_body; content:"--"; classtype:web-application-attack; sid:1000013; rev:1; metadata:created_at 2026_05_01, tag SQL_Injection;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM SQLi SELECT FROM"; flow:established,to_server; http.request_body; content:"SELECT"; nocase; content:"FROM"; nocase; distance:0; within:30; classtype:web-application-attack; sid:1000014; rev:1; metadata:created_at 2026_05_01, tag SQL_Injection;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM SQLi INSERT INTO"; flow:established,to_server; http.request_body; content:"INSERT"; nocase; content:"INTO"; nocase; distance:0; within:20; classtype:web-application-attack; sid:1000015; rev:1; metadata:created_at 2026_05_01, tag SQL_Injection;)

# XSS (4 rules)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM XSS Script Tag in Body"; flow:established,to_server; http.request_body; content:"<script"; nocase; classtype:web-application-attack; sid:1000020; rev:1; metadata:created_at 2026_05_01, tag Cross_Site_Scripting;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM XSS Script Tag in URI"; flow:established,to_server; http.uri; content:"<script"; nocase; classtype:web-application-attack; sid:1000021; rev:1; metadata:created_at 2026_05_01, tag Cross_Site_Scripting;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM XSS Event Handler"; flow:established,to_server; http.request_body; content:"onclick"; nocase; classtype:web-application-attack; sid:1000022; rev:1; metadata:created_at 2026_05_01, tag Cross_Site_Scripting;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM XSS alert()"; flow:established,to_server; http.request_body; content:"alert"; nocase; content:"("; distance:0; within:10; classtype:web-application-attack; sid:1000023; rev:1; metadata:created_at 2026_05_01, tag Cross_Site_Scripting;)

# Command Injection (3 rules)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Command Injection - Semicolon"; flow:established,to_server; http.request_body; content:";"; classtype:web-application-attack; sid:1000030; rev:1; metadata:created_at 2026_05_01, tag Command_Injection;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Command Injection - Backtick"; flow:established,to_server; http.request_body; content:"`"; classtype:web-application-attack; sid:1000031; rev:1; metadata:created_at 2026_05_01, tag Command_Injection;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Command Injection - DollarParen"; flow:established,to_server; http.request_body; content:"$("; classtype:web-application-attack; sid:1000032; rev:1; metadata:created_at 2026_05_01, tag Command_Injection;)

# Path Traversal (3 rules)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Path Traversal - ../"; flow:established,to_server; http.request_body; content:"../"; classtype:web-application-attack; sid:1000040; rev:1; metadata:created_at 2026_05_01, tag Path_Traversal;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Path Traversal - ../ in URI"; flow:established,to_server; http.uri; content:"../"; classtype:web-application-attack; sid:1000041; rev:1; metadata:created_at 2026_05_01, tag Path_Traversal;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Path Traversal - etc/passwd"; flow:established,to_server; http.request_body; content:"passwd"; nocase; classtype:web-application-attack; sid:1000042; rev:1; metadata:created_at 2026_05_01, tag Path_Traversal;)

# XXE (2 rules)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM XXE - ENTITY"; flow:established,to_server; http.request_body; content:"ENTITY"; nocase; classtype:web-application-attack; sid:1000050; rev:1; metadata:created_at 2026_05_01, tag XXE;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM XXE - SYSTEM"; flow:established,to_server; http.request_body; content:"SYSTEM"; nocase; classtype:web-application-attack; sid:1000051; rev:1; metadata:created_at 2026_05_01, tag XXE;)

# Open Redirect (2 rules)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Open Redirect - javascript:"; flow:established,to_server; http.request_body; content:"javascript:"; nocase; classtype:web-application-attack; sid:1000060; rev:1; metadata:created_at 2026_05_01, tag Open_Redirect;)
alert http any any -> $HTTP_SERVERS $HTTP_PORTS (msg:"CUSTOM Open Redirect - External URL"; flow:established,to_server; http.request_body; content:"http://"; nocase; classtype:web-application-attack; sid:1000061; rev:1; metadata:created_at 2026_05_01, tag Open_Redirect;)
```

### Key Rule Updates (May 1, 2026):
1. **Added `pass` rule (SID 1000000)** - Skips all custom rules for `/upload` endpoint
2. **All rules use `content` only** (no pcre) for Suricata 8+ compatibility
3. **13 rules total** covering 6 attack categories

---

## HTTP Parsing Configuration

Suricata's HTTP parser (libhtp v8.0.2) is configured for deep inspection:

```yaml
app-layer:
  protocols:
    http:
      enabled: yes
      libhtp:
        default-config:
          personality: IDS
          request-body-limit: 100kb
          response-body-limit: 100kb
          request-body-minimal-inspect-size: 32kb
          request-body-inspect-window: 4kb
          response-body-minimal-inspect-size: 32kb
          response-body-inspect-window: 4kb
          response-body-decompress-layer-limit: 2
          http-body-inline: auto
          swf-decompression:
            enabled: yes
            type: both
            decompress-enabled: yes
            decompress-depth: 0
          double-decode-path: no
          double-decode-query: no
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `personality` | `IDS` | Optimized for intrusion detection — prioritizes detection accuracy over performance |
| `request-body-limit` | `100kb` | Maximum HTTP request body size to inspect. Payloads larger than this are truncated |
| `response-body-limit` | `100kb` | Maximum HTTP response body size to inspect |
| `request-body-minimal-inspect-size` | `32kb` | Minimum body size before Suricata starts inspecting with full depth |
| `request-body-inspect-window` | `4kb` | Size of the inspection window that slides through the body |
| `response-body-minimal-inspect-size` | `32kb` | Same as above, for responses |
| `response-body-inspect-window` | `4kb` | Same as above, for responses |
| `response-body-decompress-layer-limit` | `2` | Maximum number of decompression layers (gzip, deflate, etc.) to process |
| `http-body-inline` | `auto` | Automatically determines inline inspection mode |
| `swf-decompression` | `yes` | Decompresses SWF (Flash) files for inspection |
| `double-decode-path` | `no` | Does not attempt double URL decoding of paths (prevents false positives) |
| `double-decode-query` | `no` | Same for query strings |

---

## Stream Reassembly Configuration

```yaml
stream:
  memcap: 64mb
  checksum-validation: yes
  midstream: false
  async-oneside: false
  inline: false
  reassembly:
    memcap: 256mb
    depth: 1mb
    toserver-chunk-size: 2560
    toclient-chunk-size: 2560
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `memcap` | `64mb` | Total memory for stream engine |
| `checksum-validation` | `yes` | Validates TCP checksums; invalid packets are dropped |
| `midstream` | `false` | Does not track sessions that started before Suricata began monitoring |
| `async-oneside` | `false` | Requires both directions of traffic to be visible |
| `inline` | `false` | Not operating in IPS (inline) mode — only detects, does not block |
| `reassembly.memcap` | `256mb` | Memory limit for TCP stream reassembly buffers |
| `reassembly.depth` | `1mb` | Maximum stream depth to reassemble. After 1 MB, Suricata stops tracking the stream content |
| `toserver-chunk-size` | `2560` | Chunk size for client-to-server data reassembly |
| `toclient-chunk-size` | `2560` | Chunk size for server-to-client data reassembly |

---

## Threading Configuration

```yaml
threading:
  set-cpu-affinity: no
  autopin: no
  cpu-affinity:
    management-cpu-set:
      cpu: [ 0 ]
    receive-cpu-set:
      cpu: [ 0 ]
    worker-cpu-set:
      cpu: [ "all" ]
      mode: "exclusive"
      prio:
        low: [ 0 ]
        medium: [ "1-2" ]
        high: [ 3 ]
        default: "medium"
  detect-thread-ratio: 1.0
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `set-cpu-affinity` | `no` | Does not force CPU pinning (relies on OS scheduler) |
| `autopin` | `no` | Does not automatically pin threads to CPUs |
| `management-cpu-set` | `[0]` | Management threads (stats, output writers) run on CPU 0 |
| `receive-cpu-set` | `[0]` | Packet receive threads run on CPU 0 |
| `worker-cpu-set` | `["all"]` | Detection worker threads can use **all available CPU cores** |
| `mode` | `exclusive` | Worker threads are pinned to specific cores, not shared |
| `detect-thread-ratio` | `1.0` | One detection thread per worker thread |

**Active threads** (from `systemctl status suricata`): `W: 6 FM: 1 FR: 1` — 6 worker threads, 1 flow manager, 1 flow recycler.

---

## Logging Configuration

```yaml
logging:
  default-log-level: notice
  outputs:
    - console:
        enabled: yes
    - file:
        enabled: yes
        level: info
        filename: suricata.log
    - syslog:
        enabled: no
```

| Output | Enabled | Level | File |
|--------|---------|-------|------|
| Console | yes | notice | stdout |
| File | yes | info | `/var/log/suricata/suricata.log` (232 KB) |
| Syslog | no | — | — |

---

## Profiling Configuration

```yaml
profiling:
  rules:
    enabled: yes
    filename: rule_perf.log
    append: yes
    limit: 10
    json: yes
  keywords:
    enabled: yes
    filename: keyword_perf.log
  prefilter:
    enabled: yes
    filename: prefilter_perf.log
  rulegroups:
    enabled: yes
    filename: rule_group_perf.log
  packets:
    enabled: yes
    filename: packet_stats.log
```

All profiling modules are **enabled**, generating performance logs for:
- **Rule performance**: Top 10 most time-consuming rules (`rule_perf.log`)
- **Keyword performance**: `content`, `pcre`, and other keyword matchers
- **Prefilter performance**: Fast matching stage before full rule evaluation
- **Rule group performance**: Grouped rule evaluation stats
- **Packet statistics**: Per-thread packet processing counts

---

## Memory and Performance Tunables

### Flow Tracking

```yaml
flow:
  memcap: 128mb
  hash-size: 65536
  emergency-recovery: 30
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `memcap` | `128mb` | Maximum memory for flow tracking |
| `hash-size` | `65536` | Flow hash table size (64K entries) |
| `emergency-recovery` | `30` | When memory pressure hits, remove 30% of oldest flows to recover |

### Defragmentation

```yaml
defrag:
  memcap: 32mb
  hash-size: 65536
  trackers: 65535
  max-frags: 65535
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `memcap` | `32mb` | Memory limit for IP fragment reassembly |
| `hash-size` | `65536` | Fragment tracking hash table size |
| `trackers` | `65535` | Maximum number of concurrent fragment trackers |
| `max-frags` | `65535` | Maximum fragments tracked per packet |

---

## Service Execution Details

```
/usr/bin/suricata --af-packet -c /etc/suricata/suricata.yaml \
  --pidfile /run/suricata.pid --user suricata --group suricata
```

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `--af-packet` | — | Use AF_PACKET capture mode (not PCAP, NFQ, or others) |
| `-c` | `/etc/suricata/suricata.yaml` | Configuration file path |
| `--pidfile` | `/run/suricata.pid` | PID file location |
| `--user suricata` | — | Drop privileges to `suricata` user after initialization |
| `--group suricata` | — | Drop privileges to `suricata` group after initialization |

**Resource usage** (current):
- Memory: 338.4 MB (peak: 445.0 MB, swap: 153.7 MB)
- CPU time: 15 min 19 sec
- Tasks: 11 (8 threads + 3 overhead)

---

## Known Issue: Unix Manager Socket

```
E: unix-manager: failed to create socket directory /var/run/suricata/: Permission denied
W: unix-manager: Unable to create unix command socket
```

The Suricata Unix management socket failed to initialize due to a **permissions issue** on `/var/run/suricata/`. This socket allows runtime interaction with Suricata (e.g., via `suricatasc` to query stats, reload rules, etc.).

**Impact:** Cannot use `suricatasc` commands to interact with the running instance. All other functionality (detection, logging, file extraction) operates normally.

**Fix:**
```bash
sudo mkdir -p /var/run/suricata/
sudo chown suricata:suricata /var/run/suricata/
sudo systemctl restart suricata
```

---

## Eve.json Log Samples

### DNS Event (Recent, Apr 30, 2026)

```json
{
  "timestamp": "2026-04-30T21:17:42.692894+0300",
  "flow_id": 2131617002890539,
  "in_iface": "enp0s3",
  "event_type": "dns",
  "src_ip": "192.168.1.6",
  "src_port": 61599,
  "dest_ip": "192.168.1.1",
  "dest_port": 53,
  "proto": "UDP",
  "dns": {
    "type": "request",
    "queries": [{
      "rrname": "tas01.cwsapp.update.microsoft.com",
      "rrtype": "A"
    }]
  }
}
```

### HTTP Event (Dec 18, 2025)

```json
{
  "timestamp": "2025-12-18T21:33:14.002425+0300",
  "flow_id": 1334568876388082,
  "in_iface": "enp0s3",
  "event_type": "http",
  "src_ip": "192.168.1.8",
  "dest_ip": "185.125.190.48",
  "dest_port": 80,
  "http": {
    "hostname": "connectivity-check.ubuntu.com.",
    "url": "/",
    "http_method": "GET",
    "protocol": "HTTP/1.1",
    "status": 204,
    "length": 0
  }
}
```

### Fileinfo Event (Dec 18, 2025)

```json
{
  "timestamp": "2025-12-18T15:56:33.547631+0300",
  "flow_id": 1713786894079936,
  "in_iface": "enp0s3",
  "event_type": "fileinfo",
  "http": {
    "hostname": "127.0.0.1",
    "http_port": 8081,
    "url": "/upload",
    "http_user_agent": "Mozilla/5.0 ... Chrome/143.0.0.0",
    "http_method": "GET",
    "status": 200
  },
  "fileinfo": {
    "filename": "/upload",
    "magic": "HTML document, ASCII text",
    "state": "CLOSED",
    "sha256": "3ae2b49c2d3cc8ea0704391ffab64722e87f6a3e4f4a742cdd1fe6650420aacc",
    "stored": true,
    "file_id": 22,
    "size": 15093,
    "tx_id": 0
  }
}
```

### Alert Events (Recent, Apr 30, 2026)

```
04/30/2026-21:05:11  [**] SURICATA STREAM reassembly overlap with different data
  [Classification: Generic Protocol Command Decode] [Priority: 3]
  {TCP} 192.168.1.6:59633 -> 18.97.36.14:443

04/30/2026-21:16:36  [**] SURICATA STREAM Packet with invalid timestamp
  [Classification: Generic Protocol Command Decode] [Priority: 3]
  {TCP} 172.65.90.21:443 -> 192.168.1.10:58492

04/30/2026-21:17:28  [**] SURICATA STREAM excessive retransmissions
  [Classification: Generic Protocol Command Decode] [Priority: 3]
  {TCP} 172.65.90.21:443 -> 192.168.1.10:58492
```

These are **TCP stream anomalies** from HTTPS traffic — not web attacks. They indicate network quality issues (packet loss, retransmissions, timestamp anomalies) rather than malicious activity. The `classification: Generic Protocol Command Decode` and `Priority: 3` (low severity, range 1-4) confirm these are informational.

---

## Essential Suricata Commands

### Service Management

| Command | Purpose |
|---------|---------|
| `sudo systemctl status suricata` | Check service status, PID, memory, threads |
| `sudo systemctl start suricata` | Start the Suricata service |
| `sudo systemctl stop suricata` | Stop the service |
| `sudo systemctl restart suricata` | Restart (needed after config/rule changes) |
| `sudo systemctl enable suricata` | Enable auto-start on boot |
| `sudo systemctl reload suricata` | Reload rules without restarting (if Unix socket works) |

### Configuration Validation

| Command | Purpose |
|---------|---------|
| `sudo suricata -T -c /etc/suricata/suricata.yaml` | **Test mode** — validate configuration and rules without starting |
| `sudo suricata --dump-config` | Print all active configuration parameters |
| `sudo suricata --build-info` | Display compile-time features and capabilities |
| `sudo suricata -V` | Show version information |

### Rule Management

| Command | Purpose |
|---------|---------|
| `sudo suricata-update` | Download and update Emerging Threats rules |
| `sudo suricata-update list-sources` | List available rule sources |
| `sudo suricata-update enable-source et/open` | Enable the ET Open ruleset |
| `sudo suricata-update enable-source ptresearch/attackdetection` | Enable Emerging Threats Pro (if licensed) |
| `sudo suricata-update disable-source <source>` | Disable a rule source |

### Log Analysis

| Command | Purpose |
|---------|---------|
| `sudo tail -f /var/log/suricata/eve.json` | Live tail of structured events |
| `sudo tail -f /var/log/suricata/fast.log` | Live tail of human-readable alerts |
| `sudo tail -f /var/log/suricata/stats.log` | Live tail of performance statistics |
| `sudo journalctl -u suricata -f` | Follow Suricata systemd journal logs |
| `sudo grep '"event_type":"alert"' /var/log/suricata/eve.json` | Extract only alert events from EVE |
| `sudo grep '"event_type":"http"' /var/log/suricata/eve.json` | Extract HTTP transaction events |
| `sudo grep '"event_type":"fileinfo"' /var/log/suricata/eve.json` | Extract file extraction events |
| `cat /var/log/suricata/eve.json \| jq -r 'select(.event_type=="alert") \| .alert.signature'` | List alert signatures (requires `jq`) |

### Runtime Interaction (if Unix socket fixed)

| Command | Purpose |
|---------|---------|
| `sudo suricatasc -c "version"` | Query Suricata version |
| `sudo suricatasc -c "command-list"` | List available commands |
| `sudo suricatasc -c "stats"` | Get live statistics |
| `sudo suricatasc -c "ruleset-reload-rules"` | Hot-reload rules |
| `sudo suricatasc -c "ruleset-stats"` | Show loaded rule counts |
| `sudo suricatasc -c "ruleset-failed-rules"` | Show rules that failed to load |

### File Extraction Inspection

| Command | Purpose |
|---------|---------|
| `sudo find /var/log/suricata/filestore/ -name "*.json" \| wc -l` | Count extracted file metadata files |
| `sudo find /var/log/suricata/filestore/ -type f -size +0 \| wc -l` | Count actual extracted files |
| `sudo find /var/log/suricata/filestore/ -mtime +1 -delete` | **Cleanup:** remove files older than 1 day |
| `sudo du -sh /var/log/suricata/filestore/` | Check total filestore disk usage |
| `sudo cat /var/log/suricata/filestore/XX/file.N.json` | Read metadata for a specific extracted file |

### Log Rotation and Cleanup

| Command | Purpose |
|---------|---------|
| `sudo logrotate -f /etc/logrotate.d/suricata` | Force log rotation |
| `sudo find /var/log/suricata/ -name "*.log" -size +100M -exec truncate -s 0 {} \;` | Truncate oversized logs |
| `sudo find /var/lib/suricata/files -type f -mtime +1 -delete` | Clean old extracted files |

---

## How to Recreate This Configuration from Scratch

### Step 1: Install Suricata

```bash
# Update package lists
sudo apt update

# Install Suricata and dependencies
sudo apt install -y suricata suricata-update jq

# Verify installation
suricata --version
# Expected: 8.0.2 RELEASE
```

### Step 2: Update Rule Sets

```bash
# Update Emerging Threats rules
sudo suricata-update

# Verify rules are loaded
sudo ls -la /var/lib/suricata/rules/
# Should show suricata.rules (~40 MB, 63k+ lines)
```

### Step 3: Configure Network Variables

Edit `/etc/suricata/suricata.yaml` and set the `HOME_NET` to match your network:

```bash
sudo nano /etc/suricata/suricata.yaml
```

Locate the `vars` section and update:

```yaml
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
```

### Step 4: Configure AF_PACKET Interfaces

In the same file, locate the `af-packet` section and add your interfaces:

```yaml
af-packet:
  - interface: enp0s3
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
  - interface: enp0s8
    cluster-id: 100
    cluster-type: cluster_flow
    defrag: yes
  - interface: default
```

Replace `enp0s3` and `enp0s8` with your actual interface names.

### Step 5: Configure EVE JSON Logging

Ensure the EVE log is enabled with the right event types:

```yaml
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: /var/log/suricata/eve.json
      types:
        - alert:
            tagged-packets: yes
        - anomaly:
            enabled: yes
        - http:
            extended: yes
        - dns:
        - tls:
            extended: yes
        - files:
            force-magic: yes
            force-hash: [sha256]
        - dhcp:
            enabled: yes
        - ssh:
        - flow:
        - smtp:
        - ftp:
        - smb:
```

### Step 6: Configure File Extraction

```yaml
  - file-store:
      version: 2
      enabled: yes
      force-magic: yes
      memcap: 64 MiB
      filename: /var/lib/suricata/files
      limit: 100 MiB
      write-meta: yes
      force-filestore: yes
      stream-depth: 0
      force-hash: [sha256]
```

Create the file extraction directory:

```bash
sudo mkdir -p /var/lib/suricata/files
sudo chown -R suricata:suricata /var/lib/suricata/files
sudo chmod 750 /var/lib/suricata/files
```

### Step 7: Add Custom Rules

Create or edit the local rules file:

```bash
sudo nano /var/lib/suricata/rules/local.rules
```

Add custom rules:

```
# Detect SQL injection authentication bypass attempt
alert http any any -> any 80 (msg:"SQLi test"; http.request_body; content:"admin' OR '1'='1'--"; nocase; sid:1000001; rev:2;)
```

Ensure the ruleset includes local rules. Edit `/etc/suricata/suricata.yaml` and verify:

```yaml
default-rule-path: /var/lib/suricata/rules
rule-files:
  - suricata.rules
  - local.rules
```

Note: If `local.rules` is not listed in `rule-files`, add it.

### Step 8: Fix Unix Socket Permissions (Optional but Recommended)

```bash
sudo mkdir -p /var/run/suricata/
sudo chown suricata:suricata /var/run/suricata/
sudo chmod 755 /var/run/suricata/
```

### Step 9: Validate Configuration

```bash
sudo suricata -T -c /etc/suricata/suricata.yaml
```

If successful, you will see:
```
Notice: suricata: Configuration provided was successfully loaded. Exiting.
```

Any errors will be printed with file paths and line numbers.

### Step 10: Start Suricata

```bash
sudo systemctl enable suricata
sudo systemctl start suricata
sudo systemctl status suricata
```

### Step 11: Verify Operation

```bash
# Check that eve.json is being written
sudo ls -la /var/log/suricata/eve.json

# Check for recent events
sudo tail -3 /var/log/suricata/eve.json | python3 -m json.tool

# Check fast.log for alerts
sudo tail -5 /var/log/suricata/fast.log

# Check stats.log for processing data
sudo tail -10 /var/log/suricata/stats.log
```

### Step 12: Test Detection

Generate test traffic to verify Suricata is inspecting:

```bash
# From any machine, make an HTTP request through VM1
curl http://192.168.1.10

# Check that Suricata logged it
sudo grep '"event_type":"http"' /var/log/suricata/eve.json | tail -1
```

Test the custom SQLi rule:

```bash
# Send a request containing the SQLi payload
curl -X POST http://192.168.1.10/login \
  -d "username=admin'+OR+'1'%3D'1'--&password=test"

# Check for the alert
sudo grep '1000001' /var/log/suricata/fast.log
```

---

## Event Flow: How Suricata Fits in the NGFW Pipeline

```
                    ┌─────────────────────────────────────────────────┐
                    │              External Traffic                    │
                    │         (Internet / Host Network)               │
                    └────────────────────┬────────────────────────────┘
                                         │
                                         ▼ enp0s3
                    ┌─────────────────────────────────────────────────┐
                    │              VM1 (NGFW Gateway)                  │
                    │                                                 │
                    │  ┌───────────┐    ┌──────────────────────────┐  │
                    │  │ nftables  │    │      Suricata (DPI)      │  │
                    │  │ (filter)  │    │                          │  │
                    │  │           │    │  AF_PACKET capture       │  │
                    │  │ Drop      │    │  ┌────────────────────┐  │  │
                    │  │ blocked   │    │  │ Protocol Parsers   │  │  │
                    │  │ IPs       │    │  │ (HTTP, DNS, TLS,   │  │  │
                    │  │           │    │  │  FTP, SSH, etc.)   │  │  │
                    │  │           │    │  └────────┬───────────┘  │  │
                    │  │           │    │           │               │  │
                    │  │ Forward   │    │  ┌────────▼───────────┐  │  │
                    │  │ allowed   │    │  │ Rule Engine        │  │  │
                    │  │ traffic   │    │  │ (63,119 rules)     │  │  │
                    │  │ to VM2    │    │  └────────┬───────────┘  │  │
                    │  └───────────┘    │           │               │  │
                    │                   │  ┌────────▼───────────┐  │  │
                    │                   │  │ File Extraction    │  │  │
                    │                   │  │ (file-store v2)    │  │  │
                    │                   │  └────────┬───────────┘  │  │
                    │                   │           │               │  │
                    │                   │  ┌────────▼───────────┐  │  │
                    │                   │  │ EVE JSON Log       │  │  │
                    │                   │  │ /var/log/suricata/ │  │  │
                    │                   │  │ eve.json           │  │  │
                    │                   │  └────────┬───────────┘  │  │
                    │                   └───────────┼──────────────┘  │
                    │                               │                  │
                    │                   ┌───────────▼───────────┐     │
                    │                   │ suri_clam_processor.py│     │
                    │                   │ (tails eve.json)      │     │
                    │                   │ Scans with ClamAV     │     │
                    │                   └───────────┬───────────┘     │
                    │                               │                  │
                    │                   ┌───────────▼───────────┐     │
                    │                   │ Decision Engine API   │     │
                    │                   │ POST /api/block_ip    │     │
                    │                   │ POST /api/log_detect  │     │
                    │                   └───────────┬───────────┘     │
                    └───────────────────────────────┼─────────────────┘
                                                    │
                                                    ▼ enp0s8
                    ┌─────────────────────────────────────────────────┐
                    │              VM2 (Test Website)                 │
                    │              10.0.0.5                           │
                    └─────────────────────────────────────────────────┘
```

### Data Flow Explanation

1. **Capture:** Suricata captures packets on both `enp0s3` (external) and `enp0s8` (internal) simultaneously using AF_PACKET
2. **Parsing:** Protocol parsers reconstruct TCP streams, parse HTTP requests/responses, DNS queries, TLS handshakes, etc.
3. **Detection:** The rule engine evaluates each parsed event against 63,119 rules
4. **Logging:** All events (alerts, HTTP, DNS, TLS, files, etc.) are written to `eve.json`
5. **File Extraction:** Files observed in HTTP traffic are saved to `/var/log/suricata/filestore/` with SHA-256 hashes
6. **Processing:** `suri_clam_processor.py` (when running) tails `eve.json`, detects `fileinfo` events, and sends extracted files to ClamAV for scanning
7. **Response:** If ClamAV detects malware, the processor posts to the Decision Engine API, which adds the attacker's IP to the nftables `blocked_ips` set

---

## 🚨 Current Issues & Fixes (As of May 2, 2026)

**Architecture Note:** VM1 handles all threat detection and IP blocking independently. VM2 does NOT communicate with VM1. Suricata on VM1 sees real source IPs directly (no NAT correlation needed).

### Issue #1: Malware Upload Blocking**

**Symptom:** When uploading EICAR test file, malware is detected and uploader's IP IS blocked.

**Fix Implemented:**
- Removed unnecessary conntrack correlation code from `suri_clam_processor.py`
- VM1 sees real `src_ip` directly from Suricata events
- `process_fileinfo_event()` uses `src_ip` from event to block attacker
- Blocks uploader's IP for 24h via `/api/block_ip`

**Status:** ✅ Working.

---

### Issue #2: False Blocks from Legitimate Traffic**

**Symptom:** Host IP (192.168.1.9) blocked when visiting Notion.so or uploading clean JSON files.

**Root Causes Fixed:**
1. **ET INFO rules** (SID 2038646) now skipped via `severity_to_block_action()`
2. **`/upload` endpoint** has `pass` rule in Suricata (SID 1000000)
3. **Clean file uploads** only scanned by ClamAV (no SQLi/XSS checks)

**Status:** ✅ Fixed.

---

### Issue #3: SSH to VM2 Not Working**

**Symptom:** SSH connection to `10.0.0.5:22` failing with `Permission denied`.

**Root Cause:** Missing `sshpass` package + incorrect credentials assumption.

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

| Capability | Status | Implementation |
|-----------|--------|----------------|
| Signature-based Detection | ✅ | 63,118 ET Open rules + 1 custom SQLi rule |
| Deep Packet Inspection | ✅ | HTTP, DNS, TLS, SSH, FTP, SMTP, SMB, and 20+ protocols |
| File Extraction | ✅ | All HTTP files extracted with SHA-256 hashing and MIME detection |
| Malware Scanning Pipeline | ✅ | File extraction → `suri_clam_processor.py` → ClamAV → Decision Engine |
| Protocol Anomaly Detection | ✅ | Anomaly events enabled — detects malformed packets, stream errors |
| Stream Reassembly | ✅ | 256 MB reassembly buffer, 1 MB depth limit |
| TLS Inspection | ✅ | JA3/JA4 fingerprinting, certificate logging, cipher suite tracking |
| Flow Tracking | ✅ | 128 MB flow table with 64K hash entries |
| IP Defragmentation | ✅ | Kernel-level reassembly on both interfaces |
| Performance Profiling | ✅ | Rule, keyword, prefilter, and packet statistics logging |
| Multi-threading | ✅ | 6 worker threads across all CPU cores |
| Community ID Correlation | ✅ | Standardized flow hashes for cross-tool event correlation |

---

## Important Notes

1. **Rule Update Frequency:** Emerging Threats rules are updated via `suricata-update`. Run `sudo suricata-update` periodically (weekly recommended) to get new signatures. After updating, restart Suricata: `sudo systemctl restart suricata`.

2. **Disk Space Management:** The EVE JSON log (`eve.json`) and stats log (`stats.log`) grow continuously. Implement log rotation:
   ```bash
   sudo nano /etc/logrotate.d/suricata
   ```
   Add:
   ```
   /var/log/suricata/*.log /var/log/suricata/*.json {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
       create 0640 suricata suricata
       postrotate
           systemctl reload suricata 2>/dev/null || true
       endscript
   }
   ```

3. **Filestore Cleanup:** Extracted files accumulate in `/var/log/suricata/filestore/`. A cleanup cron job is essential:
   ```bash
   # Add to crontab: sudo crontab -e
   0 */6 * * * find /var/log/suricata/filestore/ -type f -mtime +1 -delete
   ```

4. **Performance Impact:** Suricata on a dual-NIC VM with 63k+ rules consumes ~340 MB RAM and moderate CPU. On an 8-core/8 GB host, ensure VM1 has at least 3-4 GB RAM allocated. Monitor with `sudo tail -f /var/log/suricata/stats.log`.

5. **IDS vs IPS Mode:** Suricata is running in **IDS (detection-only)** mode, not IPS (inline blocking). It generates alerts and extracts files but does **not** block traffic itself. Blocking is handled by **nftables** via the Decision Engine API. To enable IPS mode, Suricata would need NFQUEUE integration with nftables, which is not configured.

6. **Custom Rule SID Range:** Custom rules should use SID >= 1,000,000 (like `sid:1000001`) to avoid conflicts with Emerging Threats rules (which use lower SIDs). This is a well-established convention.

7. **EVE JSON is Line-Delimited:** Each line in `eve.json` is a complete, independent JSON object. This format is designed for streaming parsers (tail + parse line by line). Do not attempt to parse the entire file as a single JSON array.
