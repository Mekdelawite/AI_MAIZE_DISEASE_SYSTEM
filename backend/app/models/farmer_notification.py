"""Persistent notifications delivered to farmer accounts."""
from datetime import datetime, timezone
from backend.app.extensions import db


class FarmerNotification(db.Model):
    __tablename__ = "farmer_notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title_en = db.Column(db.String(200), nullable=False)
    title_am = db.Column(db.String(200), nullable=False)
    message_en = db.Column(db.Text, nullable=False)
    message_am = db.Column(db.Text, nullable=False)
    region = db.Column(db.String(100), nullable=False, index=True)
    discussion_post_id = db.Column(db.Integer, db.ForeignKey("discussion_posts.id", ondelete="SET NULL"), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
