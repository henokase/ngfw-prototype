from datetime import datetime, timedelta
from typing import Optional, List, Any
import json

from sqlalchemy import Column, Integer, String, Text, Float, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config import config

Base = declarative_base()


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True)
    ip = Column(String(64), nullable=False)
    reason = Column(Text, nullable=True)
    timestamp = Column(String(64), nullable=False)
    ttl = Column(Integer, nullable=True)


class LogEvent(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    data = Column(Text, nullable=False)
    timestamp = Column(String(64), nullable=False)


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True)
    timestamp = Column(String(64), nullable=False)
    attack_type = Column(String(128), nullable=True)
    source_ip = Column(String(64), nullable=True)
    dest_ip = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    ensemble_score = Column(Float, nullable=True)
    rf_score = Column(Float, nullable=True)
    xgb_score = Column(Float, nullable=True)
    decision_tree_score = Column(Float, nullable=True)
    logistic_regression_score = Column(Float, nullable=True)
    catboost_score = Column(Float, nullable=True)
    lgb_score = Column(Float, nullable=True)
    mlp_score = Column(Float, nullable=True)
    action = Column(String(32), nullable=True)


class BackupLog(Base):
    __tablename__ = "backup_logs"

    id = Column(Integer, primary_key=True)
    data = Column(Text, nullable=False)
    timestamp = Column(String(64), nullable=False)


class BackupMLPrediction(Base):
    __tablename__ = "backup_ml_predictions"

    id = Column(Integer, primary_key=True)
    timestamp = Column(String(64), nullable=False)
    predicted_label = Column(String(32), nullable=True)
    features = Column(Text, nullable=True)


class BackupMalwareAlert(Base):
    __tablename__ = "backup_malware_alerts"

    id = Column(Integer, primary_key=True)
    timestamp = Column(String(64), nullable=False)
    filename = Column(String(256), nullable=True)
    file_hash = Column(String(64), nullable=True)
    signature = Column(String(256), nullable=True)
    source_ip = Column(String(64), nullable=True)
    action = Column(String(32), nullable=True)
    confidence = Column(Float, nullable=True)


_engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=_engine)


def get_session() -> Session:
    return SessionLocal()


# ─── Block Operations ───────────────────────────────────────────────────────

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


def get_blocks() -> List[Block]:
    session = get_session()
    try:
        return session.query(Block).all()
    finally:
        session.close()


def remove_block(ip: str) -> int:
    session = get_session()
    try:
        count = session.query(Block).filter_by(ip=ip).delete()
        session.commit()
        return count
    finally:
        session.close()


def remove_all_blocks() -> int:
    session = get_session()
    try:
        count = session.query(Block).delete()
        session.commit()
        return count
    finally:
        session.close()


# ─── Log Operations ─────────────────────────────────────────────────────────

def log_event(data: str) -> LogEvent:
    session = get_session()
    try:
        entry = LogEvent(
            data=data,
            timestamp=datetime.utcnow().isoformat(),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        
        sync_log_to_backup(entry)
        
        return entry
    finally:
        session.close()


def get_logs(limit: int = 50, offset: int = 0, search: Optional[str] = None) -> tuple[List[LogEvent], int]:
    session = get_session()
    try:
        query = session.query(LogEvent)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(LogEvent.data.like(search_pattern))

        total = query.count()
        logs = query.order_by(LogEvent.id.desc()).offset(offset).limit(limit).all()
        return logs, total
    finally:
        session.close()


def get_logs_today_count() -> int:
    session = get_session()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return session.query(LogEvent).filter(LogEvent.timestamp >= today_start).count()
    finally:
        session.close()


def get_active_threats_count() -> int:
    session = get_session()
    try:
        last_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        logs = session.query(LogEvent).filter(LogEvent.timestamp >= last_24h).all()
        count = 0
        for log in logs:
            try:
                data = json.loads(log.data)
                if data.get("action") == "block_ip":
                    count += 1
            except:
                pass
        return count
    finally:
        session.close()


def clear_logs() -> int:
    """Clear all logs from the logs table."""
    session = get_session()
    try:
        count = session.query(LogEvent).delete()
        session.commit()
        return count
    finally:
        session.close()


def clear_ml_predictions() -> int:
    """Clear all ML predictions from the ml_predictions table."""
    session = get_session()
    try:
        count = session.query(MLPrediction).delete()
        session.commit()
        return count
    finally:
        session.close()


# ─── ML Prediction Operations ────────────────────────────────────────────────

def add_ml_prediction(
    attack_type: str,
    source_ip: Optional[str],
    dest_ip: Optional[str],
    confidence: float,
    ensemble_score: float,
    rf_score: float,
    xgb_score: float,
    action: str,
    decision_tree_score: float = 0.0,
    logistic_regression_score: float = 0.0,
    catboost_score: float = 0.0,
    lgb_score: float = 0.0,
    mlp_score: float = 0.0,
    features: Optional[List[float]] = None
) -> MLPrediction:
    session = get_session()
    try:
        pred = MLPrediction(
            timestamp=datetime.utcnow().isoformat(),
            attack_type=attack_type,
            source_ip=source_ip,
            dest_ip=dest_ip,
            confidence=confidence,
            ensemble_score=ensemble_score,
            rf_score=rf_score,
            xgb_score=xgb_score,
            decision_tree_score=decision_tree_score,
            logistic_regression_score=logistic_regression_score,
            catboost_score=catboost_score,
            lgb_score=lgb_score,
            mlp_score=mlp_score,
            action=action,
        )
        session.add(pred)
        session.commit()
        session.refresh(pred)
        
        sync_ml_prediction_to_backup(pred, features)
        
        return pred
    finally:
        session.close()


def get_ml_predictions(limit: int = 100) -> List[MLPrediction]:
    session = get_session()
    try:
        return session.query(MLPrediction).order_by(MLPrediction.id.desc()).limit(limit).all()
    finally:
        session.close()


# ─── Malware Alert Operations ───────────────────────────────────────────────

def get_malware_alerts(limit: int = 100, search: Optional[str] = None) -> tuple[List[Any], int]:
    from sqlalchemy import text
    session = get_session()
    try:
        query = text("SELECT id, vm2_timestamp, filename, file_hash, signature, selected_ip, action_taken, confidence_score FROM malware_alerts ORDER BY id DESC")

        if search:
            search_pattern = f"%{search}%"
            query = text(f"SELECT id, vm2_timestamp, filename, file_hash, signature, selected_ip, action_taken, confidence_score FROM malware_alerts WHERE filename LIKE '{search_pattern}' OR signature LIKE '{search_pattern}' OR selected_ip LIKE '{search_pattern}' ORDER BY id DESC")

        result = session.execute(query)
        rows = result.fetchall()

        alerts = []
        for row in rows:
            alerts.append({
                "id": row[0],
                "timestamp": row[1],
                "filename": row[2],
                "file_hash": row[3],
                "signature": row[4],
                "source_ip": row[5],
                "action": row[6],
                "confidence": row[7],
            })

        return alerts, len(alerts)
    finally:
        session.close()


def add_malware_alert(
    filename: str,
    file_hash: str,
    signature: str,
    source_ip: str,
    action: str = "blocked",
    confidence: float = 1.0
) -> Optional[int]:
    """Add a malware alert to the database."""
    import sqlite3
    try:
        conn = sqlite3.connect('/opt/ngfw-control/ngfw.db')
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO malware_alerts 
            (vm2_timestamp, vm1_timestamp, filename, file_hash, signature, vm2_source, selected_ip, action_taken, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, timestamp, filename, file_hash, signature, source_ip, source_ip, action, confidence))
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        sync_malware_alert_to_backup(alert_id)
        
        return alert_id
    except Exception as e:
        print(f"ERROR: Failed to add malware alert: {e}")
        return None


def clear_malware_alerts() -> int:
    """Delete all malware alerts."""
    import sqlite3
    try:
        conn = sqlite3.connect('/opt/ngfw-control/ngfw.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM malware_alerts")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count
    except Exception as e:
        print(f"ERROR: Failed to clear malware alerts: {e}")
        return 0


# ─── Backup Functions ───────────────────────────────────────────────────────

def sync_log_to_backup(log: LogEvent) -> None:
    """Sync a log to backup_logs table."""
    session = get_session()
    try:
        existing = session.query(BackupLog).filter_by(id=log.id).first()
        if not existing:
            backup = BackupLog(
                id=log.id,
                data=log.data,
                timestamp=log.timestamp,
            )
            session.add(backup)
            session.commit()
    finally:
        session.close()


def sync_ml_prediction_to_backup(pred: MLPrediction, features: Optional[List[float]] = None) -> None:
    """Sync an ML prediction to backup_ml_predictions table."""
    session = get_session()
    try:
        existing = session.query(BackupMLPrediction).filter_by(id=pred.id).first()
        if not existing:
            predicted_label = "Attack" if pred.action in ("block", "alert") else "Normal"
            features_json = json.dumps(features) if features else None
            backup = BackupMLPrediction(
                id=pred.id,
                timestamp=pred.timestamp,
                predicted_label=predicted_label,
                features=features_json,
            )
            session.add(backup)
            session.commit()
    finally:
        session.close()


def sync_malware_alert_to_backup(alert_id: int) -> None:
    """Sync a malware alert to backup_malware_alerts table."""
    import sqlite3
    try:
        conn = sqlite3.connect('/opt/ngfw-control/ngfw.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT vm1_timestamp, filename, file_hash, signature, vm2_source, action_taken, confidence_score
            FROM malware_alerts WHERE vm1_timestamp IN (
                SELECT vm1_timestamp FROM malware_alerts ORDER BY rowid DESC LIMIT 1
            ) AND rowid = ?
        """, (alert_id,))
        row = cursor.fetchone()
        if row:
            session = get_session()
            existing = session.query(BackupMalwareAlert).filter_by(id=alert_id).first()
            if not existing:
                backup = BackupMalwareAlert(
                    id=alert_id,
                    timestamp=row[0] or datetime.utcnow().isoformat(),
                    filename=row[1],
                    file_hash=row[2],
                    signature=row[3],
                    source_ip=row[4],
                    action=row[5],
                    confidence=row[6],
                )
                session.add(backup)
                session.commit()
            session.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: Failed to sync malware alert: {e}")


def get_backup_logs(limit: int = 10000) -> List[BackupLog]:
    session = get_session()
    try:
        return session.query(BackupLog).order_by(BackupLog.id.desc()).limit(limit).all()
    finally:
        session.close()


def get_backup_ml_predictions(limit: int = 10000) -> List[BackupMLPrediction]:
    session = get_session()
    try:
        return session.query(BackupMLPrediction).order_by(BackupMLPrediction.id.desc()).limit(limit).all()
    finally:
        session.close()


def get_backup_malware_alerts(limit: int = 10000) -> List[BackupMalwareAlert]:
    session = get_session()
    try:
        return session.query(BackupMalwareAlert).order_by(BackupMalwareAlert.id.desc()).limit(limit).all()
    finally:
        session.close()


def clear_all_backup_tables() -> dict:
    """Clear all backup tables."""
    session = get_session()
    try:
        logs_count = session.query(BackupLog).delete()
        ml_count = session.query(BackupMLPrediction).delete()
        malware_count = session.query(BackupMalwareAlert).delete()
        session.commit()
        return {"logs": logs_count, "ml_predictions": ml_count, "malware_alerts": malware_count}
    finally:
        session.close()