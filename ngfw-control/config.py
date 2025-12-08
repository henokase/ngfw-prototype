import os


class Config:
    """Configuration for NGFW decision engine (VM1 control API)."""

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.environ.get("NGFW_DB_PATH") or os.path.join(BASE_DIR, "ngfw.db")

    # Logging
    LOG_DIR = os.environ.get("NGFW_LOG_DIR") or os.path.join(BASE_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    APP_LOG_FILE = os.path.join(LOG_DIR, "ngfw-control.log")
    SECURITY_LOG_FILE = os.path.join(LOG_DIR, "ngfw-security.log")
    LOG_LEVEL = os.environ.get("NGFW_LOG_LEVEL", "INFO")

    # Flask
    BIND_HOST = os.environ.get("NGFW_BIND_HOST", "0.0.0.0")
    BIND_PORT = int(os.environ.get("NGFW_BIND_PORT", "5001"))
    SECRET_KEY = os.environ.get("NGFW_SECRET_KEY", "ngfw_control_dev_secret_change_me")

    # Firewall / nftables
    NFT_BIN = os.environ.get("NGFW_NFT_BIN", "nft")
    NFT_TABLE = os.environ.get("NGFW_NFT_TABLE", "inet firewall")
    NFT_BLOCK_SET = os.environ.get("NGFW_NFT_BLOCK_SET", "blocked_ips")
    DEFAULT_TTL = os.environ.get("NGFW_DEFAULT_TTL", "1h")

    # API auth (optional, can be extended later)
    API_KEY = os.environ.get("NGFW_API_KEY")


config = Config()
