"""Farmer-owned Web Push subscriptions and delivery receipts."""
from datetime import datetime, timezone

from backend.app.extensions import db


class FarmerPushSubscription(db.Model):
    __tablename__ = "farmer_push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(100), nullable=False)
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


class FarmerPushDelivery(db.Model):
    __tablename__ = "farmer_push_deliveries"
    __table_args__ = (
        db.UniqueConstraint(
            "notification_id",
            "subscription_id",
            name="uq_farmer_push_delivery_notification_subscription",
        ),
        db.Index(
            "ix_farmer_push_delivery_due",
            "status",
            "next_attempt_at",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(
        db.Integer,
        db.ForeignKey("farmer_notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    subscription_id = db.Column(
        db.Integer,
        db.ForeignKey("farmer_push_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(db.String(80), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
