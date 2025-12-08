# NGFW Control Documentation

Welcome to the NGFW Control system documentation. This directory contains comprehensive documentation for understanding, deploying, and maintaining the Next Generation Firewall (NGFW) Control API.

## Documentation Overview

### 📚 Available Documents

| Document | Description | Target Audience |
|----------|-------------|-----------------|
| **[API Documentation](API_DOCUMENTATION.md)** | Complete API reference with endpoints, parameters, examples, and integration guides | Developers, Integration Teams |
| **[System Documentation](SYSTEM_DOCUMENTATION.md)** | Detailed system architecture, components, deployment, and maintenance guide | System Administrators, DevOps Engineers |
| **[README](README.md)** | This overview document with quick start guide | All Users |

### 🚀 Quick Start

The NGFW Control system is a Flask-based REST API that provides dynamic IP blocking capabilities using nftables. Here's how to get started:

#### Prerequisites
- Linux system with nftables support
- Python 3.8+
- Required permissions for nftables operations

#### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database import init_db; init_db()"

# Start the service
python app.py
```

#### Basic Usage
```bash
# Block an IP address
curl -X POST http://localhost:5001/api/block_ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.100", "reason": "Malicious activity"}'

# List blocked IPs
curl http://localhost:5001/api/list_blocks

# Unblock an IP address
curl -X POST http://localhost:5001/api/unblock_ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.100"}'
```

## System Overview

### 🎯 Purpose
The NGFW Control system serves as a centralized control plane for firewall operations, enabling:
- **Dynamic IP Blocking**: Real-time blocking of malicious IP addresses
- **Automated Response**: Integration with intrusion detection systems
- **Audit Trail**: Comprehensive logging of all security actions
- **Scalable Operations**: RESTful API for system integration

### 🏗️ Architecture
```
External Systems → Flask API → nftables + SQLite Database
     ↓               ↓              ↓
Integration     JSON Responses   Packet Filtering + Audit Logs
```

### 🔧 Core Components
- **Flask Application** (`app.py`): RESTful API server
- **Configuration Manager** (`config.py`): Environment-based configuration
- **Database Layer** (`database.py`): SQLAlchemy ORM for data persistence
- **Firewall Service** (`firewall_service.py`): nftables integration
- **Logging System** (`logger.py`): Dual logging for app and security events

### 🌟 Key Features
- ✅ **Real-time IP blocking** with configurable TTL
- ✅ **RESTful API** with JSON responses
- ✅ **Database persistence** for audit trails
- ✅ **Comprehensive logging** for security and debugging
- ✅ **Health monitoring** endpoints
- ✅ **Environment-based configuration**
- ✅ **IPv4 and IPv6 support**
- ✅ **Production-ready deployment** options

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/block_ip` | Block an IP address |
| POST | `/api/unblock_ip` | Unblock an IP address |
| POST | `/api/log_detection` | Log security events |
| GET | `/api/list_blocks` | List blocked IPs |
| GET | `/api/health` | Health check |

## Configuration Quick Reference

### Environment Variables
```bash
# Server Configuration
NGFW_BIND_HOST=0.0.0.0          # Bind address
NGFW_BIND_PORT=5001             # Bind port

# Database
NGFW_DB_PATH=./ngfw.db          # SQLite database path

# Logging
NGFW_LOG_DIR=./logs             # Log directory
NGFW_LOG_LEVEL=INFO             # Log level

# Firewall
NGFW_NFT_BIN=nft                # nftables binary
NGFW_NFT_TABLE="inet firewall"  # nftables table
NGFW_NFT_BLOCK_SET=blocked_ips  # IP set name
NGFW_DEFAULT_TTL=1h             # Default block duration

# Security
NGFW_SECRET_KEY=your-secret-key # Flask secret key
NGFW_API_KEY=your-api-key       # API authentication (future)
```

## Integration Examples

### Python Client
```python
import requests

def block_ip(ip, reason="Suspicious activity"):
    response = requests.post("http://localhost:5001/api/block_ip", 
                           json={"ip": ip, "reason": reason})
    return response.json()

result = block_ip("10.0.0.5", "Failed login attempts")
print(f"Blocked: {result['success']}")
```

### Bash Script
```bash
#!/bin/bash
API_BASE="http://localhost:5001"

block_ip() {
    curl -s -X POST "$API_BASE/api/block_ip" \
         -H "Content-Type: application/json" \
         -d "{\"ip\":\"$1\",\"reason\":\"$2\"}"
}

# Usage
block_ip "192.168.1.100" "Port scanning detected"
```

### Integration with Security Tools

#### Fail2Ban Integration
```ini
# /etc/fail2ban/action.d/ngfw-control.conf
[Definition]
actionstart = 
actionstop = 
actioncheck = 
actionban = curl -X POST http://localhost:5001/api/block_ip -H "Content-Type: application/json" -d '{"ip":"<ip>","reason":"Fail2Ban: <name>","ttl":"<bantime>s"}'
actionunban = curl -X POST http://localhost:5001/api/unblock_ip -H "Content-Type: application/json" -d '{"ip":"<ip>"}'
```

#### Suricata Integration
```yaml
# suricata.yaml output configuration
outputs:
  - http-log:
      enabled: yes
      filename: http.log
      append: yes
      custom: yes
      customformat: |
        POST http://localhost:5001/api/log_detection
        Content-Type: application/json
        
        {"source":"suricata","event":"alert","data":{"timestamp":"%{timestamp}","src_ip":"%{src_ip}","alert":"%{alert}"}}
```

## Monitoring and Maintenance

### Health Monitoring
```bash
# Check service health
curl http://localhost:5001/api/health

# Monitor logs
tail -f logs/ngfw-control.log
tail -f logs/ngfw-security.log

# Check nftables status
nft list set inet firewall blocked_ips
```

### Maintenance Tasks
- **Daily**: Monitor log files and service health
- **Weekly**: Review blocked IP lists and cleanup expired entries
- **Monthly**: Database maintenance and backup verification
- **Quarterly**: Security review and dependency updates

## Troubleshooting

### Common Issues

1. **Permission Denied for nftables**
   ```bash
   # Ensure proper permissions
   sudo setcap cap_net_admin+ep $(which python3)
   ```

2. **Database Lock Errors**
   ```bash
   # Enable WAL mode for better concurrency
   sqlite3 ngfw.db "PRAGMA journal_mode = WAL;"
   ```

3. **Service Won't Start**
   ```bash
   # Check logs for detailed error messages
   journalctl -u ngfw-control -n 50
   ```

### Debug Mode
```bash
# Run with debug logging
NGFW_LOG_LEVEL=DEBUG python app.py
```

## Security Considerations

### Deployment Security
- ⚠️ **Network Access**: Restrict API access to trusted networks only
- ⚠️ **Authentication**: Implement API key authentication for production
- ⚠️ **Privileges**: Run with minimal required system privileges
- ⚠️ **Monitoring**: Enable comprehensive logging and monitoring

### Operational Security
- 🔒 Use HTTPS in production deployments
- 🔒 Implement rate limiting to prevent API abuse
- 🔒 Regular security updates and patch management
- 🔒 Secure configuration file and database permissions

## Support and Development

### Getting Help
1. **Check Documentation**: Start with the relevant documentation file
2. **Review Logs**: Application and security logs contain detailed information
3. **Test Configuration**: Use the health endpoint to verify system status
4. **Community Support**: Refer to project repository for issues and discussions

### Contributing
- Follow the existing code style and patterns
- Add comprehensive tests for new features
- Update documentation for any changes
- Submit pull requests with clear descriptions

### Development Environment
```bash
# Clone repository
git clone <repository-url>
cd ngfw-control

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Run tests
pytest tests/

# Format code
black *.py

# Lint code
flake8 *.py
```

## Version History

### Current Version: 1.0.0
- Initial release with core IP blocking functionality
- RESTful API with comprehensive endpoints
- SQLite database integration
- nftables firewall integration
- Comprehensive logging system
- Environment-based configuration
- Health monitoring capabilities

### Planned Features
- API key authentication
- Role-based access control
- Metrics and monitoring endpoints
- Bulk IP operations
- Integration with threat intelligence feeds
- Web-based management interface

---

## Quick Reference Card

### Essential Commands
```bash
# Start service
python app.py

# Block IP
curl -X POST http://localhost:5001/api/block_ip -H "Content-Type: application/json" -d '{"ip":"x.x.x.x"}'

# Unblock IP  
curl -X POST http://localhost:5001/api/unblock_ip -H "Content-Type: application/json" -d '{"ip":"x.x.x.x"}'

# List blocks
curl http://localhost:5001/api/list_blocks

# Check health
curl http://localhost:5001/api/health

# View logs
tail -f logs/ngfw-control.log
```

### File Structure
```
ngfw-control/
├── app.py                  # Main Flask application
├── config.py              # Configuration management
├── database.py            # Database models and operations
├── firewall_service.py    # nftables integration
├── logger.py              # Logging system
├── requirements.txt       # Python dependencies
├── ngfw.db                # SQLite database (created at runtime)
└── docs/                  # Documentation
    ├── README.md           # This file
    ├── API_DOCUMENTATION.md
    └── SYSTEM_DOCUMENTATION.md
```

For detailed information, please refer to the specific documentation files above.