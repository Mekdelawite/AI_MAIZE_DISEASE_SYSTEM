"""
=========================================================
Discussion Reply Model
=========================================================

Replies to agricultural discussion posts.

A reply can be written by:
    - a farmer
    - an extension agent

Exactly one author field should be populated.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class DiscussionReply(db.Model):
    """
    Reply to a discussion post.
    """

    __tablename__ = "discussion_replies"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "discussion_posts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    farmer_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    extension_agent_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    content = db.Column(
        db.Text,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    post = db.relationship(
        "DiscussionPost",
        backref=db.backref(
            "replies",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    farmer = db.relationship(
        "User",
        foreign_keys=[farmer_id],
        backref=db.backref(
            "discussion_farmer_replies",
            lazy=True,
        ),
    )

    extension_agent = db.relationship(
        "User",
        foreign_keys=[extension_agent_id],
        backref=db.backref(
            "discussion_extension_replies",
            lazy=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DiscussionReply "
            f"id={self.id} "
            f"post_id={self.post_id}>"
        )
