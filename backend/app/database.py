"""
Database configuration and session management.
"""

import logging
import os
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

logger = logging.getLogger(__name__)

# Default: in-memory SQLite. Set DATABASE_URL to switch to file DB.
# Example (file): sqlite:////app/data/ecg_mi.db
DEFAULT_DATABASE_URL = "sqlite:///:memory:"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL

if DATABASE_URL.startswith("sqlite:///") and DATABASE_URL != "sqlite:///:memory:":
    db_path = DATABASE_URL.removeprefix("sqlite:///")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

# Create SQLite engine
engine_kwargs: dict = {
    "connect_args": {"check_same_thread": False},
    "echo": False,  # Set to True for SQL debugging
}

if DATABASE_URL == "sqlite:///:memory:":
    # Keep one shared in-memory DB across all sessions in this process.
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Create tables
Base.metadata.create_all(bind=engine)


def ensure_sqlite_schema() -> None:
    """Add columns introduced after first deploy (SQLite has no ALTER in metadata)."""
    if not DATABASE_URL.startswith("sqlite:"):
        return
    try:
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("examinations")}
        if "mfer_file_path" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE examinations ADD COLUMN mfer_file_path VARCHAR(500)")
                )
    except Exception:
        logger.warning("ensure_sqlite_schema failed", exc_info=True)


ensure_sqlite_schema()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database with sample data (empty DB only).
    Default is skip. To enable, set ECG_MI_ENABLE_SAMPLE_DB_SEED=1.
    ECG_MI_SKIP_SAMPLE_DB_SEED=1 is still honored for backward compatibility.
    """
    skip_seed = os.getenv("ECG_MI_SKIP_SAMPLE_DB_SEED", "").lower() in ("1", "true", "yes", "on")
    enable_seed = os.getenv("ECG_MI_ENABLE_SAMPLE_DB_SEED", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if skip_seed or not enable_seed:
        logger.info(
            "init_db: sample seed skipped (enable=%s, skip=%s)",
            int(enable_seed),
            int(skip_seed),
        )
        return

    from datetime import datetime, timedelta

    from .models import Examination, Inference, Patient

    db = SessionLocal()

    # Check if data already exists
    if db.query(Patient).count() > 0:
        db.close()
        return

    # Create sample patients
    patient1 = Patient(name="田中太郎", patient_id="P001", age=65, gender="男性")
    patient2 = Patient(name="佐藤花子", patient_id="P002", age=58, gender="女性")

    db.add(patient1)
    db.add(patient2)
    db.flush()

    # Create sample examinations
    exam1 = Examination(
        patient_id=patient1.id,
        exam_date=datetime.utcnow() - timedelta(days=2),
        csv_file_path="/data/ecg/P001_20260307.csv",
        notes="通常検査",
    )
    exam2 = Examination(
        patient_id=patient1.id,
        exam_date=datetime.utcnow() - timedelta(days=1),
        csv_file_path="/data/ecg/P001_20260308.csv",
        notes="フォローアップ検査",
    )
    exam3 = Examination(
        patient_id=patient2.id,
        exam_date=datetime.utcnow(),
        csv_file_path="/data/ecg/P002_20260309.csv",
        notes="初回検査",
    )

    db.add_all([exam1, exam2, exam3])
    db.flush()

    # Create sample inference
    inference1 = Inference(
        examination_id=exam1.id,
        status="完了",
        result='{"mi_type": "anterior", "severity": "high"}',
        confidence_score=0.92,
        mi_probability=0.87,
    )

    db.add(inference1)
    db.commit()
    db.close()


def purge_sensitive_generated_artifacts() -> None:
    """
    Security mode: remove persisted generated artifacts.
    - inferences rows (delete all)
    - examination ecg_image_etag
    """
    from .models import Examination, Inference

    db = SessionLocal()
    try:
        db.query(Inference).delete(synchronize_session=False)
        db.query(Examination).update(
            {
                Examination.ecg_image_etag: None,
            },
            synchronize_session=False,
        )
        db.commit()
    finally:
        db.close()
