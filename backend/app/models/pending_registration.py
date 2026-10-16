
"""
Pending Farmer Registration Model.

Stores temporary phone-verification state before a farmer account
is created. Never stores the raw OTP or a registration password.
"""

from datetime import datetime, timezone

from backend.app.extensions import db


def utc_now():
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class PendingRegistration(db.Model):
    """Temporary record for verifying a phone before registration."""

    __tablename__ = "pending_registrations"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # Store phone numbers in one canonical format, e.g. +251911998877.
    phone_number = db.Column(
        db.String(20),
        nullable=False,
        unique=True,
        index=True,
    )

    # SHA-256 hexadecimal digest; never store the raw OTP.
    otp_hash = db.Column(
        db.String(64),
        nullable=True,
    )

    otp_expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # Limit guesses against the current OTP.
    attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    max_attempts = db.Column(
        db.Integer,
        nullable=False,
        default=5,
    )

    last_sent_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    verified_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # Give the user time to complete the form after verification.
    registration_expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    def __repr__(self):
        return (
            f"<PendingRegistration "
            f"id={self.id} "
            f"phone_number={self.phone_number!r}>"
        )
