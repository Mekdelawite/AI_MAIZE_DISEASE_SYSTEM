"""
=========================================================
SMS Record Model
=========================================================

Stores SMS notification attempts made by the AI Maize
Disease Detection System.

The model keeps a history of:
    - recipient phone number
    - message content
    - recipient type
    - SMS purpose
    - provider
    - provider message ID
    - delivery status
    - error information
    - timestamps

This model is independent from the SMS provider itself.
The SMS service is responsible for communicating with
Africa's Talking.

=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class SMSRecord(db.Model):
    """
    Database record for an SMS notification.
    """

    __tablename__ = "sms_records"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # =====================================================
    # RECIPIENT
    # =====================================================

    recipient_phone = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )

    recipient_type = db.Column(
        db.String(30),
        nullable=False,
        default="farmer",
        index=True,
    )

    # =====================================================
    # MESSAGE
    # =====================================================

    message = db.Column(
        db.Text,
        nullable=False,
    )

    language = db.Column(
        db.String(5),
        nullable=False,
        default="en",
    )

    # =====================================================
    # SMS PURPOSE
    # =====================================================

    notification_type = db.Column(
        db.String(50),
        nullable=False,
        default="general",
        index=True,
    )

    # =====================================================
    # PROVIDER INFORMATION
    # =====================================================

    provider = db.Column(
        db.String(50),
        nullable=False,
        default="africas_talking",
    )

    provider_message_id = db.Column(
        db.String(150),
        nullable=True,
        index=True,
    )

    # =====================================================
    # DELIVERY STATUS
    # =====================================================

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True,
    )

    error_message = db.Column(
        db.Text,
        nullable=True,
    )

    # =====================================================
    # RELATED USER
    # =====================================================

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    # =====================================================
    # OUTBREAK ALERT
    # =====================================================

    outbreak_alert_id = db.Column(
    db.Integer,
    db.ForeignKey(
        "outbreak_alerts.id",
        ondelete="SET NULL",
    ),
    nullable=True,
    index=True,
    )

    outbreak_alert = db.relationship(
    "OutbreakAlert",
    backref="sms_records",
    lazy=True,
    )   

    # =====================================================
    # LOCATION
    # =====================================================

    region = db.Column(
        db.String(50),
        nullable=True,
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
    # TIMESTAMPS
    # =====================================================

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    sent_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    delivered_at = db.Column(
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
            f"<SMSRecord "
            f"id={self.id} "
            f"recipient={self.recipient_phone!r} "
            f"status={self.status!r}>"
        )