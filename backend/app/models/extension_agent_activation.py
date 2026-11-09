from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class ExtensionAgentActivation(db.Model):
    __tablename__ = "extension_agent_activations"
    __table_args__ = (
    db.CheckConstraint(
        "verification_method IN ('email', 'sms')",
        name="ck_extension_agent_activation_verification_method",
    ),
    db.CheckConstraint(
        "attempts >= 0",
        name="ck_extension_agent_activation_attempts",
    ),
    db.CheckConstraint(
        "max_attempts > 0",
        name="ck_extension_agent_activation_max_attempts",
    ),
    db.CheckConstraint(
        "resend_count >= 0",
        name="ck_extension_agent_activation_resend_count",
    ),
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    verification_method = db.Column(db.String(10), nullable=False)
    otp_hash = db.Column(db.String(64), nullable=True)
    otp_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    max_attempts = db.Column(db.Integer, nullable=False, default=5, server_default="5")
    last_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resend_window_started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resend_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    activation_token_hash = db.Column(db.String(64), nullable=True)
    activation_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.func.now(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.func.now(),
    )

    user = db.relationship("User", backref=db.backref("extension_agent_activation", uselist=False))
