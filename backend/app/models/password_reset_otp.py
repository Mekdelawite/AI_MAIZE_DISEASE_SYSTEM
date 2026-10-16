"""
=========================================================
Password Reset OTP Model
=========================================================

Stores temporary password-reset verification information.

Security:
    - OTP values are never stored in plaintext.
    - Only the OTP hash is persisted.
    - OTPs expire automatically through application logic.
    - Failed verification attempts are tracked.
    - Successful OTPs are permanently consumed.

Relationship:
    PasswordResetOTP -> User

=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class PasswordResetOTP(db.Model):
    """
    Temporary password-reset OTP record.
    """

    __tablename__ = "password_reset_otps"

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
        nullable=False,
        index=True,
    )

    # =====================================================
    # OTP SECURITY
    # =====================================================

    otp_hash = db.Column(
        db.String(64),
        nullable=False,
    )

    # =====================================================
    # EXPIRATION
    # =====================================================

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # =====================================================
    # VERIFICATION ATTEMPTS
    # =====================================================

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

    # =====================================================
    # STATUS
    # =====================================================

    used_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # =====================================================
    # RELATIONSHIP
    # =====================================================

    user = db.relationship(
        "User",
        backref=db.backref(
            "password_reset_otps",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    # =====================================================
    # HELPERS
    # =====================================================

    @property
    def is_used(self) -> bool:
        """
        Return True when the OTP has already been consumed.
        """

        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        """
        Return True when the OTP has expired.
        """

        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def attempts_exceeded(self) -> bool:
        """
        Return True when the maximum number of attempts
        has been reached.
        """

        return self.attempts >= self.max_attempts

    def mark_used(self) -> None:
        """
        Permanently consume this OTP.
        """

        self.used_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"<PasswordResetOTP "
            f"id={self.id} "
            f"user_id={self.user_id} "
            f"used={self.is_used}>"
        )