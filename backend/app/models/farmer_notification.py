"""Persistent notifications delivered to farmer accounts."""
from datetime import datetime, timezone

from backend.app.extensions import db


class FarmerNotification(db.Model):
    __tablename__ = "farmer_notifications"

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "notification_type",
            "outbreak_alert_id",
            name="uq_farmer_notification_user_alert_type",
        ),
        db.Index(
            "uq_farmer_notification_user_dedupe_key",
            "user_id",
            "dedupe_key",
            unique=True,
            postgresql_where=db.text("dedupe_key IS NOT NULL"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title_en = db.Column(db.String(200), nullable=False)
    title_am = db.Column(db.String(200), nullable=False)
    message_en = db.Column(db.Text, nullable=False)
    message_am = db.Column(db.Text, nullable=False)
    region = db.Column(db.String(100), nullable=False, index=True)
    notification_type = db.Column(db.String(50), nullable=False, default="general", index=True)
    # Deterministic key for scheduled crop reminders and advisory alerts.
    # Nullable so existing/manual notifications retain their current behavior.
    dedupe_key = db.Column(db.String(180), nullable=True)
    outbreak_alert_id = db.Column(
        db.Integer,
        db.ForeignKey("outbreak_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    discussion_post_id = db.Column(db.Integer, db.ForeignKey("discussion_posts.id", ondelete="SET NULL"), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
