from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Text, create_engine
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
