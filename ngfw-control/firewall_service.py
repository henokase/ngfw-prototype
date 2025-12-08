import subprocess
from typing import Tuple, List
import ipaddress

from config import config
from logger import get_app_logger, get_security_logger

app_logger = get_app_logger()
security_logger = get_security_logger()


def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def _run_nft(args: List[str]) -> Tuple[bool, str]:
    """Run an nft command. Returns (success, output)."""
    cmd = [config.NFT_BIN] + args
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
        success = completed.returncode == 0
        output = completed.stdout if success else completed.stderr
        if not success:
            app_logger.error(f"nft command failed: {' '.join(cmd)} :: {output}")
        return success, output.strip()
    except FileNotFoundError:
        app_logger.error("nft binary not found; firewall operations unavailable")
        return False, "nft not found"


def add_block(ip: str, ttl: str) -> Tuple[bool, str]:
    """Add IP to nftables blocked set with timeout TTL (e.g. '1h' or '300s')."""
    if not is_valid_ip(ip):
        return False, "invalid IP"

    set_expr = f"{{ {ip} timeout {ttl} }}"
    table, set_name = config.NFT_TABLE, config.NFT_BLOCK_SET
    args = [
        "add",
        "element",
        table,
        set_name,
        set_expr,
    ]
    success, out = _run_nft(args)
    if success:
        security_logger.warning(f"Blocked IP via nftables: {ip} ttl={ttl}")
    return success, out


def remove_block(ip: str) -> Tuple[bool, str]:
    if not is_valid_ip(ip):
        return False, "invalid IP"

    set_expr = f"{{ {ip} }}"
    table, set_name = config.NFT_TABLE, config.NFT_BLOCK_SET
    args = [
        "delete",
        "element",
        table,
        set_name,
        set_expr,
    ]
    success, out = _run_nft(args)
    if success:
        security_logger.warning(f"Unblocked IP via nftables: {ip}")
    return success, out


def list_blocks() -> Tuple[bool, str]:
    table, set_name = config.NFT_TABLE, config.NFT_BLOCK_SET
    args = ["list", "set", table, set_name]
    return _run_nft(args)
