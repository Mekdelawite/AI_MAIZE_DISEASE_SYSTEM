"""
=========================================================
Discussion Post Model
=========================================================

Agricultural communication posts created by farmers or
extension agents.

Post types:
    - question       -> farmer question
    - advisory       -> extension-agent advice
    - announcement   -> extension-agent information
    - alert          -> extension-agent urgent warning

Extension-agent posts can be targeted by:
    - region
    - woreda
    - kebele

A post may optionally be connected to an AI diagnosis.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class DiscussionPost(db.Model):
    """
    Agricultural discussion or communication post.
    """

    __tablename__ = "discussion_posts"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    post_type = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )

    title = db.Column(
        db.String(200),
        nullable=False,
    )

    content = db.Column(
        db.Text,
        nullable=False,
    )

    image_path = db.Column(
        db.String(500),
        nullable=True,
    )

    diagnosis_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "diagnosis_records.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    target_region = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    target_woreda = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    target_kebele = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    priority = db.Column(
        db.String(20),
        nullable=False,
        default="normal",
        index=True,
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

    author = db.relationship(
        "User",
        foreign_keys=[author_id],
        backref=db.backref(
            "discussion_posts",
            lazy=True,
        ),
    )

    diagnosis = db.relationship(
        "DiagnosisRecord",
        foreign_keys=[diagnosis_id],
        backref=db.backref(
            "discussion_posts",
            lazy=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DiscussionPost "
            f"id={self.id} "
            f"author_id={self.author_id} "
            f"post_type={self.post_type}>"
        )