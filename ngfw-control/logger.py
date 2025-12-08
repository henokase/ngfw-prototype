import logging
from logging.handlers import RotatingFileHandler
import os

from config import config


def _ensure_log_dir() -> None:
    os.makedirs(config.LOG_DIR, exist_ok=True)


def create_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    _ensure_log_dir()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s in %(module)s: %(message)s"
    )

    handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def get_app_logger() -> logging.Logger:
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    return create_logger("ngfw-control", config.APP_LOG_FILE, level)


def get_security_logger() -> logging.Logger:
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    return create_logger("ngfw-security", config.SECURITY_LOG_FILE, level)
