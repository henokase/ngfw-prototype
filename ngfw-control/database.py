from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config import config

Base = declarative_base()


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True)
    ip = Column(String(64), nullable=False)
    reason = Column(Text, nullable=True)
    timestamp = Column(String(64), nullable=False)  # ISO-8601
    ttl = Column(Integer, nullable=True)  # seconds


class LogEvent(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    source = Column(String(64), nullable=False)
    event = Column(String(128), nullable=False)
    data = Column(Text, nullable=True)
    timestamp = Column(String(64), nullable=False)  # ISO-8601


class MalwareAlert(Base):
    """Basic malware alert record from VM2.

    This implements the foundation of the malware_alerts table from the
    integration plan, focusing on core fields needed for Phase 1:
    - filename / file_hash / signature
    - vm2 and vm1 timestamps
    - vm2_source identifier

    Correlation and decision fields can be added later as the
    conntrack/decision engine evolves.
    """

    __tablename__ = "malware_alerts"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(128), nullable=False, index=True)
    signature = Column(String(255), nullable=False)
    vm2_timestamp = Column(String(64), nullable=False)
    vm1_timestamp = Column(String(64), nullable=False)
    vm2_source = Column(String(64), nullable=False)

    # Correlation / decision placeholders (kept simple for now)
    correlated_ips = Column(Text, nullable=True)
    selected_ip = Column(String(64), nullable=True)
    confidence_score = Column(Float, nullable=True)
    correlation_method = Column(String(64), nullable=True)
    action_taken = Column(String(64), nullable=True)
    block_duration = Column(String(64), nullable=True)
    block_reason = Column(Text, nullable=True)
    blocked_at = Column(String(64), nullable=True)

    block_id = Column(Integer, ForeignKey("blocks.id"), nullable=True)
    log_event_id = Column(Integer, ForeignKey("logs.id"), nullable=True)


_engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=_engine)


def get_session() -> Session:
    return SessionLocal()


def add_block(ip: str, reason: Optional[str], ttl_seconds: Optional[int]) -> Block:
    session = get_session()
    try:
        block = Block(
            ip=ip,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
            ttl=ttl_seconds,
        )
        session.add(block)
        session.commit()
        session.refresh(block)
        return block
    finally:
        session.close()


def log_event(source: str, event: str, data: Optional[str]) -> LogEvent:
    session = get_session()
    try:
        entry = LogEvent(
            source=source,
            event=event,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry
    finally:
        session.close()


def create_malware_alert(
    *,
    filename: str,
    file_hash: str,
    signature: str,
    vm2_timestamp: str,
    vm2_source: str,
    action_taken: Optional[str] = None,
) -> MalwareAlert:
    """Create a MalwareAlert record from a VM2 notification.

    For now this stores core alert data and marks the action as
    "pending_correlation" or similar; correlation and blocking decisions
    can be filled in later.
    """

    session = get_session()
    try:
        alert = MalwareAlert(
            filename=filename,
            file_hash=file_hash,
            signature=signature,
            vm2_timestamp=vm2_timestamp,
            vm1_timestamp=datetime.utcnow().isoformat(),
            vm2_source=vm2_source,
            action_taken=action_taken,
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert
    finally:
        session.close()


def get_blocks() -> List[Block]:
    session = get_session()
    try:
        return session.query(Block).all()
    finally:
        session.close()


def remove_block(ip: str) -> int:
    """Remove block rows for a given IP. Returns number of rows deleted."""
    session = get_session()
    try:
        count = session.query(Block).filter_by(ip=ip).delete()
        session.commit()
        return count
    finally:
        session.close()
