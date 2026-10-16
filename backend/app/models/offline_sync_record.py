"""
=========================================================
Offline Synchronization Record
=========================================================

Tracks client-side offline operations that are synchronized
with the backend.

The operation_id acts as an idempotency key so that retrying
the same offline operation cannot create duplicate records.

The image_path stores the durable server-side copy of the
synchronization image so an interrupted operation can be
recovered after an application crash.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class OfflineSyncRecord(db.Model):
    """
    Tracks an offline synchronization operation.
    """

    __tablename__ = "offline_sync_records"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    operation_id = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    operation_type = db.Column(
        db.String(50),
        nullable=False,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    image_path = db.Column(
        db.Text,
        nullable=True,
    )

    diagnosis_id = db.Column(
        db.Integer,
        db.ForeignKey("diagnosis_records.id"),
        nullable=True,
        index=True,
    )

    error_message = db.Column(
        db.Text,
        nullable=True,
    )

    attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<OfflineSyncRecord "
            f"id={self.id} "
            f"operation_id={self.operation_id!r} "
            f"status={self.status!r}>"
        )