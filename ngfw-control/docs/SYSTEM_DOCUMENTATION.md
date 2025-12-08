# NGFW Control System Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Component Details](#component-details)
4. [Database Schema](#database-schema)
5. [Configuration Management](#configuration-management)
6. [Logging System](#logging-system)
7. [Security Framework](#security-framework)
8. [Deployment Guide](#deployment-guide)
9. [Monitoring and Maintenance](#monitoring-and-maintenance)
10. [Troubleshooting](#troubleshooting)

## System Overview

The NGFW Control System is a lightweight, high-performance firewall management service designed to provide dynamic IP blocking and unblocking capabilities. It serves as the central control plane for Next Generation Firewall (NGFW) operations, integrating with nftables for real-time network access control.

### Key Features

- **Dynamic IP Blocking**: Real-time IP address blocking with configurable TTL
- **RESTful API**: Clean, well-documented API for integration with other systems
- **Database Persistence**: SQLite-based storage for audit trails and state management
- **Comprehensive Logging**: Dual logging system for application and security events
- **nftables Integration**: Direct integration with Linux nftables for high-performance packet filtering
- **Health Monitoring**: Built-in health checks for service monitoring
- **Configurable Deployment**: Environment-variable based configuration

### Use Cases

- **Intrusion Detection Response**: Automatic blocking of malicious IP addresses
- **DDoS Mitigation**: Rate-based blocking of attacking sources
- **Threat Intelligence Integration**: Blocking known bad actors from threat feeds
- **Manual Security Operations**: Administrative control for security teams
- **Compliance Logging**: Audit trail for security actions and decisions

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    NGFW Control System                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    Flask    │  │   Config    │  │   Logger    │         │
│  │    API      │  │  Manager    │  │   System    │         │
│  │   (app.py)  │  │ (config.py) │  │ (logger.py) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                 │                 │              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Database   │  │  Firewall   │  │             │         │
│  │   Layer     │  │   Service   │  │    ...      │         │
│  │(database.py)│  │(firewall_   │  │             │         │
│  │             │  │ service.py) │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────┐      ┌─────────────┐
│   SQLite    │      │  nftables   │
│  Database   │      │   Kernel    │
│  (ngfw.db)  │      │   Module    │
└─────────────┘      └─────────────┘
```

### Data Flow

1. **API Request**: External systems send HTTP requests to Flask API
2. **Validation**: Input validation and parameter normalization
3. **Firewall Operations**: nftables commands executed via subprocess
4. **Database Recording**: Actions logged to SQLite database
5. **Response**: JSON response with operation results
6. **Logging**: Security and application events recorded to log files

### Integration Points

- **External APIs**: RESTful endpoints for system integration
- **nftables**: Linux kernel packet filtering framework
- **SQLite Database**: Local persistence layer
- **File System**: Configuration and log file management
- **Operating System**: Process management and network stack

## Component Details

### 1. Flask Application (`app.py`)

**Purpose**: Main application entry point and API route definitions

**Key Functions**:
- `_normalize_ttl()`: TTL parameter normalization
- `api_block_ip()`: IP blocking endpoint handler
- `api_unblock_ip()`: IP unblocking endpoint handler
- `api_log_detection()`: Security event logging handler
- `api_list_blocks()`: Block listing endpoint handler
- `api_health()`: Health check endpoint handler

**Design Patterns**:
- **Dependency Injection**: Modular service imports
- **Error Handling**: Consistent error response format
- **Logging Integration**: Dual logger usage
- **Configuration Separation**: External config management

**Threading Model**: Single-threaded Flask development server (production deployment should use WSGI server)

### 2. Configuration Manager (`config.py`)

**Purpose**: Centralized configuration management with environment variable support

**Configuration Categories**:

1. **Database Settings**
   - `DB_PATH`: SQLite database file location
   - Default: `{BASE_DIR}/ngfw.db`

2. **Logging Configuration**
   - `LOG_DIR`: Directory for log files
   - `APP_LOG_FILE`: Application log file path
   - `SECURITY_LOG_FILE`: Security log file path
   - `LOG_LEVEL`: Logging verbosity level

3. **Network Settings**
   - `BIND_HOST`: API server bind address
   - `BIND_PORT`: API server port number
   - `SECRET_KEY`: Flask session encryption key

4. **Firewall Configuration**
   - `NFT_BIN`: nftables binary path
   - `NFT_TABLE`: Target nftables table
   - `NFT_BLOCK_SET`: Target IP set name
   - `DEFAULT_TTL`: Default block duration

**Environment Variable Mapping**:
```bash
# Database
NGFW_DB_PATH=/path/to/database.db

# Logging  
NGFW_LOG_DIR=/var/log/ngfw
NGFW_LOG_LEVEL=DEBUG

# Network
NGFW_BIND_HOST=127.0.0.1
NGFW_BIND_PORT=5001
NGFW_SECRET_KEY=your-secret-key

# Firewall
NGFW_NFT_BIN=/usr/sbin/nft
NGFW_NFT_TABLE="inet firewall"
NGFW_NFT_BLOCK_SET=blocked_ips
NGFW_DEFAULT_TTL=1h

# Security
NGFW_API_KEY=your-api-key
```

### 3. Database Layer (`database.py`)

**Purpose**: Data persistence and ORM management using SQLAlchemy

**Database Models**:

1. **Block Model**
   ```python
   class Block(Base):
       id: Integer (Primary Key)
       ip: String(64) - IP address
       reason: Text - Block reason
       timestamp: String(64) - ISO-8601 timestamp
       ttl: Integer - TTL in seconds
   ```

2. **LogEvent Model**
   ```python
   class LogEvent(Base):
       id: Integer (Primary Key)
       source: String(64) - Event source system
       event: String(128) - Event type
       data: Text - JSON event data
       timestamp: String(64) - ISO-8601 timestamp
   ```

**Key Functions**:
- `init_db()`: Database initialization and table creation
- `get_session()`: SQLAlchemy session factory
- `add_block()`: Create new block record
- `log_event()`: Create new log event record
- `get_blocks()`: Retrieve all block records
- `remove_block()`: Delete block records by IP

**Database Features**:
- **Connection Pooling**: SQLAlchemy session management
- **Transaction Safety**: Automatic commit/rollback
- **Schema Evolution**: Declarative model definitions
- **Concurrency Control**: SQLite WAL mode support

### 4. Firewall Service (`firewall_service.py`)

**Purpose**: nftables integration and IP address validation

**Key Functions**:

1. **IP Validation**
   ```python
   def is_valid_ip(ip: str) -> bool
   ```
   - Validates IPv4 and IPv6 addresses using Python's `ipaddress` module
   - Returns boolean validation result

2. **nftables Command Execution**
   ```python
   def _run_nft(args: List[str]) -> Tuple[bool, str]
   ```
   - Executes nft commands via subprocess
   - Captures stdout/stderr for result processing
   - Returns success status and output

3. **IP Blocking**
   ```python
   def add_block(ip: str, ttl: str) -> Tuple[bool, str]
   ```
   - Adds IP to nftables blocked set with timeout
   - Format: `nft add element inet firewall blocked_ips { IP timeout TTL }`

4. **IP Unblocking**
   ```python
   def remove_block(ip: str) -> Tuple[bool, str]
   ```
   - Removes IP from nftables blocked set
   - Format: `nft delete element inet firewall blocked_ips { IP }`

5. **Block Listing**
   ```python
   def list_blocks() -> Tuple[bool, str]
   ```
   - Lists current nftables blocked set contents
   - Format: `nft list set inet firewall blocked_ips`

**nftables Integration**:
- **Set-based Blocking**: Uses nftables named sets for efficient IP matching
- **Automatic Timeouts**: Leverages nftables built-in timeout functionality
- **Atomic Operations**: Individual IP add/remove operations
- **Error Handling**: Comprehensive error capture and reporting

### 5. Logging System (`logger.py`)

**Purpose**: Dual logging system for application and security events

**Logger Types**:

1. **Application Logger** (`ngfw-control`)
   - General application events and errors
   - Debug information and performance metrics
   - File: `ngfw-control.log`

2. **Security Logger** (`ngfw-security`)
   - Security-related events (blocks, unblocks, detections)
   - Compliance and audit trail information
   - File: `ngfw-security.log`

**Logging Features**:
- **Rotating Files**: 10MB max size, 5 backup files
- **Dual Output**: File and console logging
- **Structured Format**: Timestamp, level, module, and message
- **Configurable Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Log Format**:
```
[2024-01-15 10:30:00,123] WARNING ngfw-security in firewall_service: Blocked IP via nftables: 192.168.1.100 ttl=1h
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐         ┌─────────────────┐
│     blocks      │         │      logs       │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │         │ id (PK)         │
│ ip              │         │ source          │
│ reason          │         │ event           │
│ timestamp       │         │ data            │
│ ttl             │         │ timestamp       │
└─────────────────┘         └─────────────────┘
```

### Table Specifications

#### blocks Table

| Column    | Type        | Constraints | Description |
|-----------|-------------|-------------|-------------|
| id        | INTEGER     | PRIMARY KEY | Auto-increment record ID |
| ip        | STRING(64)  | NOT NULL    | IPv4/IPv6 address |
| reason    | TEXT        | NULL        | Block reason description |
| timestamp | STRING(64)  | NOT NULL    | ISO-8601 timestamp |
| ttl       | INTEGER     | NULL        | TTL in seconds |

**Indexes**:
- Primary key on `id`
- Recommended index on `ip` for lookup performance
- Recommended index on `timestamp` for time-based queries

#### logs Table

| Column    | Type         | Constraints | Description |
|-----------|--------------|-------------|-------------|
| id        | INTEGER      | PRIMARY KEY | Auto-increment record ID |
| source    | STRING(64)   | NOT NULL    | Event source system |
| event     | STRING(128)  | NOT NULL    | Event type/name |
| data      | TEXT         | NULL        | JSON event data |
| timestamp | STRING(64)   | NOT NULL    | ISO-8601 timestamp |

**Indexes**:
- Primary key on `id`
- Recommended composite index on `(source, event)` for filtering
- Recommended index on `timestamp` for time-based queries

### Database Maintenance

**Vacuum Operations**:
```sql
-- Reclaim space and optimize
VACUUM;

-- Analyze query patterns
ANALYZE;
```

**Cleanup Procedures**:
```sql
-- Remove old log entries (older than 90 days)
DELETE FROM logs WHERE timestamp < date('now', '-90 days');

-- Remove expired blocks (assuming TTL tracking)
DELETE FROM blocks WHERE 
    ttl IS NOT NULL AND 
    datetime(timestamp) + (ttl || ' seconds') < datetime('now');
```

## Configuration Management

### Environment Variables

The system uses environment variables for all configuration, following the 12-factor app methodology:

**Development Configuration** (`.env`):
```bash
# Development settings
NGFW_BIND_HOST=127.0.0.1
NGFW_BIND_PORT=5001
NGFW_LOG_LEVEL=DEBUG
NGFW_SECRET_KEY=dev-secret-key

# Database
NGFW_DB_PATH=./ngfw.db

# Firewall (development/testing)
NGFW_NFT_BIN=/usr/bin/nft
NGFW_DEFAULT_TTL=5m
```

**Production Configuration**:
```bash
# Production settings
NGFW_BIND_HOST=0.0.0.0
NGFW_BIND_PORT=5001
NGFW_LOG_LEVEL=INFO
NGFW_SECRET_KEY=${SECURE_RANDOM_KEY}

# Database
NGFW_DB_PATH=/var/lib/ngfw/ngfw.db

# Logging
NGFW_LOG_DIR=/var/log/ngfw

# Firewall
NGFW_NFT_BIN=/usr/sbin/nft
NGFW_NFT_TABLE="inet firewall"
NGFW_NFT_BLOCK_SET=blocked_ips
NGFW_DEFAULT_TTL=1h

# Security
NGFW_API_KEY=${API_KEY}
```

### Configuration Validation

```python
# Example validation logic
def validate_config():
    required_vars = [
        'NGFW_SECRET_KEY',
        'NGFW_NFT_TABLE',
        'NGFW_NFT_BLOCK_SET'
    ]
    
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise ConfigurationError(f"Missing required variables: {missing}")
```

## Security Framework

### Threat Model

**Assets Protected**:
- Network infrastructure and services
- System availability and performance
- Audit logs and compliance data

**Threat Actors**:
- External attackers (DDoS, intrusion attempts)
- Malicious insiders
- Automated attack tools
- Advanced persistent threats (APTs)

**Attack Vectors**:
- Network-based attacks (scanning, exploitation)
- API abuse and manipulation
- Configuration tampering
- Log manipulation

### Security Controls

1. **Input Validation**
   - IP address format validation
   - Parameter sanitization
   - JSON schema validation

2. **Access Control**
   - Network-level access restrictions
   - API key authentication (configurable)
   - Principle of least privilege

3. **Audit Logging**
   - All security actions logged
   - Tamper-evident log formats
   - Centralized log collection support

4. **System Hardening**
   - Minimal attack surface
   - Secure defaults
   - Regular security updates

### Security Best Practices

**Deployment Security**:
- Run with minimal required privileges
- Use dedicated service account
- Implement network segmentation
- Enable firewall protection

**Data Protection**:
- Encrypt sensitive configuration data
- Secure database file permissions
- Implement log rotation and retention
- Regular backup procedures

**Monitoring and Detection**:
- Monitor API usage patterns
- Detect configuration changes
- Alert on security events
- Implement anomaly detection

## Deployment Guide

### System Requirements

**Minimum Requirements**:
- Linux distribution with nftables support (kernel 3.13+)
- Python 3.8+
- 512MB RAM
- 1GB disk space
- Network connectivity

**Recommended Requirements**:
- Linux distribution with nftables 0.9.3+
- Python 3.10+
- 2GB RAM
- 10GB disk space
- Dedicated network interface

### Installation Steps

1. **System Preparation**
   ```bash
   # Install nftables
   sudo apt update
   sudo apt install nftables python3 python3-pip

   # Create service user
   sudo useradd -r -s /bin/false ngfw-control
   sudo mkdir -p /opt/ngfw-control /var/lib/ngfw /var/log/ngfw
   sudo chown ngfw-control:ngfw-control /var/lib/ngfw /var/log/ngfw
   ```

2. **Application Installation**
   ```bash
   # Copy application files
   sudo cp -r ngfw-control/* /opt/ngfw-control/
   sudo chown -R ngfw-control:ngfw-control /opt/ngfw-control

   # Install Python dependencies
   cd /opt/ngfw-control
   sudo -u ngfw-control pip3 install -r requirements.txt
   ```

3. **nftables Configuration**
   ```bash
   # Create nftables configuration
   cat > /etc/nftables.conf << EOF
   table inet firewall {
       set blocked_ips {
           type ipv4_addr
           flags timeout
           timeout 1h
       }
       
       chain input {
           type filter hook input priority 0;
           ip saddr @blocked_ips drop
       }
   }
   EOF

   # Enable and start nftables
   sudo systemctl enable nftables
   sudo systemctl start nftables
   ```

4. **Service Configuration**
   ```bash
   # Create systemd service file
   cat > /etc/systemd/system/ngfw-control.service << EOF
   [Unit]
   Description=NGFW Control API
   After=network.target

   [Service]
   Type=simple
   User=ngfw-control
   WorkingDirectory=/opt/ngfw-control
   Environment=NGFW_DB_PATH=/var/lib/ngfw/ngfw.db
   Environment=NGFW_LOG_DIR=/var/log/ngfw
   Environment=NGFW_BIND_HOST=0.0.0.0
   Environment=NGFW_BIND_PORT=5001
   ExecStart=/usr/bin/python3 app.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   EOF

   # Enable and start service
   sudo systemctl daemon-reload
   sudo systemctl enable ngfw-control
   sudo systemctl start ngfw-control
   ```

### Production Deployment

**WSGI Server Configuration** (using Gunicorn):
```bash
# Install Gunicorn
pip install gunicorn

# Create Gunicorn configuration
cat > /opt/ngfw-control/gunicorn.conf.py << EOF
bind = "0.0.0.0:5001"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
max_requests = 1000
max_requests_jitter = 100
preload_app = True
EOF

# Update systemd service
ExecStart=/usr/local/bin/gunicorn --config gunicorn.conf.py app:app
```

**Reverse Proxy Configuration** (Nginx):
```nginx
upstream ngfw_backend {
    server 127.0.0.1:5001;
}

server {
    listen 80;
    server_name ngfw-api.example.com;

    location / {
        proxy_pass http://ngfw_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring and Maintenance

### Health Monitoring

**Service Health Checks**:
```bash
#!/bin/bash
# Health check script

HEALTH_URL="http://localhost:5001/api/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$RESPONSE" = "200" ]; then
    echo "Service healthy"
    exit 0
else
    echo "Service unhealthy (HTTP $RESPONSE)"
    exit 1
fi
```

**Monitoring Metrics**:
- API response times and status codes
- Database connection pool status
- Log file sizes and rotation
- nftables rule counts and performance
- System resource utilization

### Maintenance Procedures

**Log Rotation**:
```bash
# Logrotate configuration
cat > /etc/logrotate.d/ngfw-control << EOF
/var/log/ngfw/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ngfw-control ngfw-control
    postrotate
        systemctl reload ngfw-control
    endscript
}
EOF
```

**Database Maintenance**:
```bash
#!/bin/bash
# Database maintenance script

DB_PATH="/var/lib/ngfw/ngfw.db"
BACKUP_DIR="/var/backups/ngfw"

# Create backup
mkdir -p $BACKUP_DIR
sqlite3 $DB_PATH ".backup $BACKUP_DIR/ngfw-$(date +%Y%m%d_%H%M%S).db"

# Cleanup old logs (keep 90 days)
sqlite3 $DB_PATH "DELETE FROM logs WHERE timestamp < datetime('now', '-90 days');"

# Vacuum database
sqlite3 $DB_PATH "VACUUM;"
```

**Security Updates**:
- Regular Python package updates
- Operating system security patches
- nftables version updates
- Security configuration reviews

### Performance Tuning

**Database Optimization**:
```sql
-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_blocks_ip ON blocks(ip);
CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_source_event ON logs(source, event);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);

-- SQLite optimization settings
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;
```

**Application Tuning**:
- Increase worker processes for high load
- Implement connection pooling
- Add caching for frequently accessed data
- Optimize nftables rule ordering

## Troubleshooting

### Common Issues

1. **nftables Permission Denied**
   ```bash
   # Symptoms: "nft: Operation not permitted" errors
   # Solution: Ensure service runs with sufficient privileges
   sudo setcap cap_net_admin+ep /usr/bin/python3
   # Or run service as root (not recommended for production)
   ```

2. **Database Locked Errors**
   ```bash
   # Symptoms: "database is locked" errors
   # Solution: Enable WAL mode and check for long-running transactions
   sqlite3 /var/lib/ngfw/ngfw.db "PRAGMA journal_mode = WAL;"
   ```

3. **API Timeout Issues**
   ```bash
   # Symptoms: Slow API responses
   # Solution: Check nftables performance and database indexing
   nft list ruleset | wc -l  # Check rule count
   sqlite3 ngfw.db "EXPLAIN QUERY PLAN SELECT * FROM blocks WHERE ip = '1.1.1.1';"
   ```

### Diagnostic Commands

**Service Status**:
```bash
systemctl status ngfw-control
journalctl -u ngfw-control -f
```

**nftables Diagnostics**:
```bash
# Check nftables status
nft list ruleset
nft list set inet firewall blocked_ips

# Monitor nftables performance
nft monitor
```

**Database Diagnostics**:
```bash
# Check database integrity
sqlite3 /var/lib/ngfw/ngfw.db "PRAGMA integrity_check;"

# Analyze table statistics
sqlite3 /var/lib/ngfw/ngfw.db "ANALYZE; SELECT * FROM sqlite_stat1;"
```

**Log Analysis**:
```bash
# Monitor application logs
tail -f /var/log/ngfw/ngfw-control.log

# Monitor security logs
tail -f /var/log/ngfw/ngfw-security.log

# Search for errors
grep ERROR /var/log/ngfw/*.log
```

### Performance Debugging

**API Performance**:
```python
# Add timing middleware for debugging
import time
from functools import wraps

def timing_decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        app_logger.debug(f"{f.__name__} took {end - start:.3f}s")
        return result
    return wrapper
```

**Database Performance**:
```sql
-- Enable query logging
PRAGMA temp_store = MEMORY;

-- Analyze slow queries
EXPLAIN QUERY PLAN SELECT * FROM blocks ORDER BY timestamp DESC LIMIT 100;
```

### Emergency Procedures

**Emergency Block Removal**:
```bash
# Remove all blocks via nftables
nft flush set inet firewall blocked_ips

# Clear database blocks
sqlite3 /var/lib/ngfw/ngfw.db "DELETE FROM blocks;"
```

**Service Recovery**:
```bash
# Force restart service
sudo systemctl stop ngfw-control
sudo systemctl start ngfw-control

# Check system resources
free -h
df -h
top -p $(pgrep -f ngfw-control)
```

**Backup and Recovery**:
```bash
# Create emergency backup
cp /var/lib/ngfw/ngfw.db /tmp/ngfw-emergency-backup-$(date +%s).db

# Restore from backup
systemctl stop ngfw-control
cp /var/backups/ngfw/ngfw-latest.db /var/lib/ngfw/ngfw.db
chown ngfw-control:ngfw-control /var/lib/ngfw/ngfw.db
systemctl start ngfw-control
```

This comprehensive documentation provides complete coverage of the NGFW Control system architecture, implementation details, and operational procedures.