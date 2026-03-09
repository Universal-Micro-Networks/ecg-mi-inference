"""
SQLAlchemy models for ECG MI Inference system.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Patient(Base):
    """Patient information."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    examinations: Mapped[list[Examination]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "patient_id": self.patient_id,
            "age": self.age,
            "gender": self.gender,
        }


class Examination(Base):
    """Examination record with ECG data."""

    __tablename__ = "examinations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=False, index=True
    )
    exam_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    csv_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    ecg_image_cache_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ecg_image_etag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    patient: Mapped[Patient] = relationship(back_populates="examinations")
    inferences: Mapped[list[Inference]] = relationship(
        back_populates="examination", cascade="all, delete-orphan"
    )

    def to_dict(self, include_patient=True):
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "exam_date": self.exam_date.isoformat(),
            "csv_file_path": self.csv_file_path,
            "notes": self.notes,
        }
        if include_patient:
            result["patient"] = self.patient.to_dict()
        return result


class Inference(Base):
    """Inference result record."""

    __tablename__ = "inferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    examination_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("examinations.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="未実行"
    )  # 未実行, 実行中, 完了, エラー
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mi_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    examination: Mapped[Examination] = relationship(back_populates="inferences")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "examination_id": self.examination_id,
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message,
            "confidence_score": self.confidence_score,
            "mi_probability": self.mi_probability,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
