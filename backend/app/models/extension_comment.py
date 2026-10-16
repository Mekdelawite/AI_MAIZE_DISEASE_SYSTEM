"""
=========================================================
Extension Comment Model
=========================================================

Stores expert comments made by agricultural extension
agents on farmer AI diagnosis records.

An extension agent can review an AI diagnosis and provide
additional agricultural guidance or professional feedback.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class ExtensionComment(db.Model):
    """
    Stores one expert comment made by an extension agent
    on a diagnosis record.
    """

    __tablename__ = "extension_comments"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
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
        nullable=False,
        index=True,
    )

    diagnosis = db.relationship(
        "DiagnosisRecord",
        backref=db.backref(
            "extension_comments",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    # =====================================================
    # EXTENSION AGENT
    # =====================================================

    extension_agent_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    extension_agent = db.relationship(
        "User",
        foreign_keys=[extension_agent_id],
        backref=db.backref(
            "extension_comments",
            lazy=True,
        ),
    )

    # =====================================================
    # COMMENT
    # =====================================================

    comment = db.Column(
        db.Text,
        nullable=False,
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

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<ExtensionComment "
            f"id={self.id} "
            f"diagnosis_id={self.diagnosis_id} "
            f"extension_agent_id={self.extension_agent_id}>"
        )