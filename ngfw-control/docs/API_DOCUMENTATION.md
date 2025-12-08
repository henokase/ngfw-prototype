# NGFW Control API Documentation

## Overview

The NGFW Control API is a Flask-based RESTful service that provides centralized IP blocking and unblocking capabilities using nftables. It serves as the control plane for a Next Generation Firewall (NGFW) system, allowing other components to dynamically manage network access controls.

## Base URL

```
http://{NGFW_BIND_HOST}:{NGFW_BIND_PORT}
```

Default: `http://0.0.0.0:5001`

## Authentication

Currently, the API does not implement authentication. Future versions may include API key authentication via the `NGFW_API_KEY` environment variable.

## API Endpoints

### 1. Block IP Address

**Endpoint:** `POST /api/block_ip`

**Description:** Blocks an IP address using nftables and records the action in the database.

**Request Body:**
```json
{
    "ip": "string (required)",
    "reason": "string (optional)",
    "ttl": "string|number (optional)",
    "signature": "string (optional)"
}
```

**Parameters:**
- `ip` (required): IPv4 or IPv6 address to block
- `reason` (optional): Reason for blocking (default: "unknown")
- `ttl` (optional): Time-to-live for the block. Can be:
  - Number (seconds): `300`
  - String with unit: `"1h"`, `"30m"`, `"300s"`
  - Default: `"1h"`
- `signature` (optional): Detection signature or identifier

**Response:**
```json
{
    "success": true,
    "blocked_ip": "192.168.1.100",
    "ttl": "1h",
    "db_id": 123
}
```

**Error Response:**
```json
{
    "success": false,
    "error": "error message"
}
```

**Status Codes:**
- `200`: Success
- `400`: Bad request (missing IP)
- `500`: Internal server error (nftables failure)

**Example:**
```bash
curl -X POST http://localhost:5001/api/block_ip \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "reason": "Malicious activity detected",
    "ttl": "2h",
    "signature": "MALWARE_DETECTED_001"
  }'
```

### 2. Unblock IP Address

**Endpoint:** `POST /api/unblock_ip`

**Description:** Removes an IP address from the nftables blocked set and removes database records.

**Request Body:**
```json
{
    "ip": "string (required)"
}
```

**Parameters:**
- `ip` (required): IPv4 or IPv6 address to unblock

**Response:**
```json
{
    "success": true,
    "unblocked_ip": "192.168.1.100",
    "rows_deleted": 1
}
```

**Error Response:**
```json
{
    "success": false,
    "error": "error message"
}
```

**Status Codes:**
- `200`: Success
- `400`: Bad request (missing IP)
- `500`: Internal server error (nftables failure)

**Example:**
```bash
curl -X POST http://localhost:5001/api/unblock_ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.100"}'
```

### 3. Log Detection Event

**Endpoint:** `POST /api/log_detection`

**Description:** Logs a security detection event to the database and security log files.

**Request Body:**
```json
{
    "source": "string (optional)",
    "event": "string (optional)",
    "data": "any (optional)"
}
```

**Parameters:**
- `source` (optional): Source system or component (default: "unknown")
- `event` (optional): Event type or name (default: "detection")
- `data` (optional): Additional event data (JSON serializable)

**Response:**
```json
{
    "success": true,
    "log_id": 456
}
```

**Status Codes:**
- `200`: Success

**Example:**
```bash
curl -X POST http://localhost:5001/api/log_detection \
  -H "Content-Type: application/json" \
  -d '{
    "source": "IDS",
    "event": "Port Scan Detected",
    "data": {
      "src_ip": "10.0.0.5",
      "target_ports": [22, 80, 443],
      "timestamp": "2024-01-15T10:30:00Z"
    }
  }'
```

### 4. List Blocked IPs

**Endpoint:** `GET /api/list_blocks`

**Description:** Retrieves a list of all currently blocked IP addresses from the database.

**Request:** No parameters required

**Response:**
```json
{
    "success": true,
    "blocks": [
        {
            "id": 123,
            "ip": "192.168.1.100",
            "reason": "Malicious activity detected",
            "timestamp": "2024-01-15T10:30:00.123456",
            "ttl": 7200
        }
    ]
}
```

**Response Fields:**
- `id`: Database record ID
- `ip`: Blocked IP address
- `reason`: Reason for blocking
- `timestamp`: ISO-8601 formatted timestamp
- `ttl`: Time-to-live in seconds (null if not specified)

**Status Codes:**
- `200`: Success

**Example:**
```bash
curl -X GET http://localhost:5001/api/list_blocks
```

### 5. Health Check

**Endpoint:** `GET /api/health`

**Description:** Provides health status of the API service and its dependencies.

**Request:** No parameters required

**Response:**
```json
{
    "status": "ok",
    "db": "ok"
}
```

**Response Fields:**
- `status`: Overall service status (`"ok"` or `"degraded"`)
- `db`: Database status (`"ok"` or `"error"`)

**Status Codes:**
- `200`: Success

**Example:**
```bash
curl -X GET http://localhost:5001/api/health
```

## Configuration

The API is configured through environment variables:

### Database Configuration
- `NGFW_DB_PATH`: SQLite database file path (default: `./ngfw.db`)

### Logging Configuration
- `NGFW_LOG_DIR`: Log directory path (default: `./logs`)
- `NGFW_LOG_LEVEL`: Logging level (default: `INFO`)

### Server Configuration
- `NGFW_BIND_HOST`: Bind host address (default: `0.0.0.0`)
- `NGFW_BIND_PORT`: Bind port number (default: `5001`)
- `NGFW_SECRET_KEY`: Flask secret key

### Firewall Configuration
- `NGFW_NFT_BIN`: nftables binary path (default: `nft`)
- `NGFW_NFT_TABLE`: nftables table name (default: `inet firewall`)
- `NGFW_NFT_BLOCK_SET`: nftables set name for blocked IPs (default: `blocked_ips`)
- `NGFW_DEFAULT_TTL`: Default TTL for blocks (default: `1h`)

### Authentication Configuration
- `NGFW_API_KEY`: API key for authentication (optional, not yet implemented)

## Error Handling

All API endpoints return consistent error responses:

```json
{
    "success": false,
    "error": "Descriptive error message"
}
```

Common error scenarios:
- Missing required parameters (400 Bad Request)
- Invalid IP addresses (500 Internal Server Error)
- nftables command failures (500 Internal Server Error)
- Database connection issues (500 Internal Server Error)

## Logging

The system maintains two types of logs:

1. **Application Log** (`ngfw-control.log`): General application events, errors, and debugging information
2. **Security Log** (`ngfw-security.log`): Security-related events including blocks, unblocks, and detections

Both logs use rotating file handlers with a maximum size of 10MB and keep 5 backup files.

## Dependencies

- Flask >= 3.0.0: Web framework
- SQLAlchemy >= 2.0.0: Database ORM
- nftables: System firewall (external dependency)

## Integration Examples

### Python Client Example

```python
import requests

class NGFWClient:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
    
    def block_ip(self, ip, reason=None, ttl=None, signature=None):
        data = {"ip": ip}
        if reason:
            data["reason"] = reason
        if ttl:
            data["ttl"] = ttl
        if signature:
            data["signature"] = signature
        
        response = requests.post(f"{self.base_url}/api/block_ip", json=data)
        return response.json()
    
    def unblock_ip(self, ip):
        response = requests.post(f"{self.base_url}/api/unblock_ip", json={"ip": ip})
        return response.json()
    
    def list_blocks(self):
        response = requests.get(f"{self.base_url}/api/list_blocks")
        return response.json()

# Usage
client = NGFWClient()
result = client.block_ip("192.168.1.100", "Suspicious activity", "30m")
print(result)
```

### Bash Script Example

```bash
#!/bin/bash

NGFW_API="http://localhost:5001"

# Block an IP
block_ip() {
    local ip=$1
    local reason=$2
    curl -X POST "$NGFW_API/api/block_ip" \
         -H "Content-Type: application/json" \
         -d "{\"ip\":\"$ip\",\"reason\":\"$reason\"}"
}

# Unblock an IP
unblock_ip() {
    local ip=$1
    curl -X POST "$NGFW_API/api/unblock_ip" \
         -H "Content-Type: application/json" \
         -d "{\"ip\":\"$ip\"}"
}

# Usage
block_ip "10.0.0.5" "Failed login attempts"
```

## Security Considerations

1. **Network Access**: Ensure the API is only accessible from trusted networks
2. **Authentication**: Implement API key authentication in production environments
3. **Rate Limiting**: Consider implementing rate limiting to prevent abuse
4. **Input Validation**: The API validates IP addresses but additional validation may be needed
5. **Logging**: Monitor security logs for suspicious patterns
6. **nftables Permissions**: Ensure the service has appropriate permissions to modify nftables rules

## Monitoring and Troubleshooting

### Health Monitoring
Use the `/api/health` endpoint for service monitoring and alerting.

### Log Analysis
Monitor the following log patterns:
- Failed nftables commands
- Database connection errors
- Invalid IP address attempts
- High frequency of block/unblock operations

### Common Issues
1. **nftables not found**: Ensure nftables is installed and in PATH
2. **Permission denied**: Ensure service has sudo/root privileges for nftables
3. **Database locked**: Check for concurrent access issues with SQLite
4. **Invalid table/set**: Verify nftables table and set configuration

## API Versioning

Current API version: 1.0
Future versions will maintain backward compatibility where possible.