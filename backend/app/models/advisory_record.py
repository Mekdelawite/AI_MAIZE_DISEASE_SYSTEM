"""
=========================================================
Advisory Record Model
=========================================================

Stores agricultural advisory results generated from
maize disease diagnoses.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class AdvisoryRecord(db.Model):
    """
    Stores an advisory generated for a diagnosis.
    """

    __tablename__ = "advisory_records"

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
            "advisory_records",
            lazy=True,
        ),
    )

    # =====================================================
    # DIAGNOSIS
    # =====================================================

    diagnosis_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "diagnosis_records.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    diagnosis = db.relationship(
        "DiagnosisRecord",
        backref=db.backref(
            "advisory_records",
            lazy=True,
        ),
    )

    # =====================================================
    # ADVISORY CONTENT
    # =====================================================

    language = db.Column(
        db.String(5),
        nullable=False,
        default="en",
    )

    advisory_text = db.Column(
        db.Text,
        nullable=False,
    )

    # =====================================================
    # SOURCE
    # =====================================================

    source = db.Column(
        db.String(50),
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
            f"<AdvisoryRecord "
            f"id={self.id} "
            f"diagnosis_id={self.diagnosis_id}>"
        )