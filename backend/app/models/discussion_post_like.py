"""A user's persistent like on a community discussion post."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint

from backend.app.extensions import db


class DiscussionPostLike(db.Model):
    __tablename__ = "discussion_post_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_discussion_post_like_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("discussion_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    post = db.relationship(
        "DiscussionPost",
        backref=db.backref("likes", lazy=True, cascade="all, delete-orphan"),
    )
    user = db.relationship(
        "User",
        backref=db.backref("discussion_post_likes", lazy=True, cascade="all, delete-orphan"),
    )
