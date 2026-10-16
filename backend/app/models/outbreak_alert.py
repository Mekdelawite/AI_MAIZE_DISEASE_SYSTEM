"""
=========================================================
Outbreak Alert Model
=========================================================

Stores disease outbreak alert events detected by the
system or created manually by an administrator.

An outbreak alert represents ONE alert event.

Individual SMS delivery attempts are stored separately
in SMSRecord.

Example:

    OutbreakAlert
        |
        +---- SMSRecord -> Farmer A
        +---- SMSRecord -> Farmer B
        +---- SMSRecord -> Farmer C

Trigger types:
    - automatic
    - manual

Status:
    - pending
    - processing
    - sent
    - partially_sent
    - failed

=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class OutbreakAlert(db.Model):
    """
    Represents a disease outbreak alert event.

    The record stores the outbreak assessment and the
    result of the alert operation.

    Individual recipient SMS records are stored in
    SMSRecord.
    """

    __tablename__ = "outbreak_alerts"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # =====================================================
    # OUTBREAK INFORMATION
    # =====================================================

    disease_class = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    risk_level = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )

    risk_score = db.Column(
        db.Float,
        nullable=False,
    )

    # =====================================================
    # GEOGRAPHIC INFORMATION
    # =====================================================

    region = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    woreda = db.Column(
        db.String(50),
        nullable=True,
        index=True,
    )

    kebele = db.Column(
        db.String(50),
        nullable=True,
        index=True,
    )

    # =====================================================
    # OUTBREAK STATISTICS
    # =====================================================

    registered_farmers = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    affected_farmers = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    total_diagnoses = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    recent_diagnoses = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    total_kebeles = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    affected_kebeles = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    # =====================================================
    # ALERT TRIGGER
    # =====================================================

    trigger_type = db.Column(
        db.String(20),
        nullable=False,
        default="automatic",
        index=True,
    )

    # =====================================================
    # ALERT STATUS
    # =====================================================

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True,
    )

    # =====================================================
    # SMS STATISTICS
    # =====================================================

    total_recipients = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    sms_sent = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    sms_failed = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    sms_pending = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    # =====================================================
    # CREATOR
    # =====================================================

    created_by = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    sent_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
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
            "<OutbreakAlert "
            f"id={self.id} "
            f"disease={self.disease_class!r} "
            f"risk={self.risk_level!r} "
            f"region={self.region!r} "
            f"status={self.status!r}>"
        )