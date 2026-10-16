"""
=========================================================
Diagnosis Record Model
=========================================================

Stores AI maize disease diagnosis history.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class DiagnosisRecord(db.Model):
    """
    Stores one completed AI diagnosis.
    """

    __tablename__ = "diagnosis_records"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # =====================================================
    # USER
    # =====================================================

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "diagnosis_records",
            lazy=True,
        ),
    )

    # =====================================================
    # IMAGE INFORMATION
    # =====================================================

    image_filename = db.Column(
        db.String(255),
        nullable=True,
    )

    image_path = db.Column(
        db.String(500),
        nullable=True,
    )

    # =====================================================
    # AI PREDICTION
    # =====================================================

    disease_class = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    confidence = db.Column(
        db.Float,
        nullable=False,
    )

    model_name = db.Column(
        db.String(100),
        nullable=True,
    )

    model_version = db.Column(
        db.String(50),
        nullable=True,
    )

    prediction_time = db.Column(
        db.Float,
        nullable=True,
    )

    # =====================================================
    # EXPLAINABILITY
    # =====================================================

    explainability_requested = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    heatmap_path = db.Column(
        db.String(500),
        nullable=True,
    )

    # =====================================================
    # TIMESTAMP
    # =====================================================

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<DiagnosisRecord "
            f"id={self.id} "
            f"disease={self.disease_class!r} "
            f"confidence={self.confidence}>"
        )