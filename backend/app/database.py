"""
Database configuration and session management.
"""

import logging
import os
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)

# Use SQLite database in backend/data directory
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'ecg_mi.db')}"

# Create SQLite engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for SQL debugging
)

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
    """Initialize database with sample data."""
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
