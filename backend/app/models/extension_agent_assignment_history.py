from __future__ import annotations

from datetime import datetime, timezone

from backend.app.extensions import db


class ExtensionAgentAssignmentHistory(db.Model):
    __tablename__ = "extension_agent_assignment_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    previous_woreda_id = db.Column(
        db.String(32),
        db.ForeignKey("geography_woredas.id", ondelete="RESTRICT"),
        nullable=True,
    )
    new_woreda_id = db.Column(
        db.String(32),
        db.ForeignKey("geography_woredas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    changed_by_admin_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    changed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.func.now(),
    )

    agent = db.relationship("User", foreign_keys=[user_id])
    changed_by_admin = db.relationship("User", foreign_keys=[changed_by_admin_id])
    previous_woreda = db.relationship(
        "GeographyWoreda",
        foreign_keys=[previous_woreda_id],
    )
    new_woreda = db.relationship(
        "GeographyWoreda",
        foreign_keys=[new_woreda_id],
    )
