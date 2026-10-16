"""
=========================================================
Extension Agent Model
=========================================================

Stores professional information specific to agricultural
extension agents.

Authentication and common user information remain in the
users table. This model stores only extension-agent-specific
profile information.
=========================================================
"""

from __future__ import annotations

from backend.app.extensions import db


class ExtensionAgent(db.Model):
    """
    Professional profile for an extension agent.

    The user_id is both the primary key and foreign key,
    creating a one-to-one relationship with the User model.
    """

    __tablename__ = "extension_agents"

    # =====================================================
    # AGENT ID
    # =====================================================

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    # =====================================================
    # PROFESSIONAL INFORMATION
    # =====================================================

    region = db.Column(
        db.String(50),
        nullable=False,
    )

    woreda = db.Column(
        db.String(50),
        nullable=True,
    )

    specialization = db.Column(
        db.String(50),
        nullable=True,
    )

    certification_number = db.Column(
        db.String(50),
        unique=True,
        nullable=True,
        index=True,
    )

    # =====================================================
    # RELATIONSHIP
    # =====================================================

    user = db.relationship(
        "User",
        backref=db.backref(
            "extension_agent_profile",
            uselist=False,
        ),
    )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<ExtensionAgent "
            f"user_id={self.user_id} "
            f"region={self.region!r} "
            f"specialization={self.specialization!r}>"
        )