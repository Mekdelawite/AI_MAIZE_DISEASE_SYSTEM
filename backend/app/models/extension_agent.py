
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

from datetime import datetime, timezone

from sqlalchemy import text

from backend.app.extensions import db


class ExtensionAgent(db.Model):
    """
    Professional profile for an extension agent.

    The user_id is both the primary key and foreign key,
    creating a one-to-one relationship with the User model.
    """

    __tablename__ = "extension_agents"

    __table_args__ = (
        db.CheckConstraint(
            "account_status <> 'active' OR "
            "(region_id IS NOT NULL AND zone_id IS NOT NULL AND woreda_id IS NOT NULL)",
            name="ck_extension_agent_active_woreda",
        ),
        db.CheckConstraint(
            "account_status IN ('pending_activation', 'active', 'suspended')",
            name="ck_extension_agent_account_status",
        ),
        db.CheckConstraint(
            "(professional_info_verified = FALSE "
            "AND professional_info_verified_by_id IS NULL "
            "AND professional_info_verified_at IS NULL) "
            "OR (professional_info_verified = TRUE "
            "AND professional_info_verified_by_id IS NOT NULL "
            "AND professional_info_verified_at IS NOT NULL)",
            name="ck_extension_agent_professional_verification",
        ),
        db.ForeignKeyConstraint(
            ["zone_id", "region_id"],
            ["geography_zones.id", "geography_zones.region_id"],
            name="fk_extension_agent_zone_region",
        ),
        db.ForeignKeyConstraint(
            ["woreda_id", "zone_id"],
            ["geography_woredas.id", "geography_woredas.zone_id"],
            name="fk_extension_agent_woreda_zone",
        ),
        db.Index(
            "uq_extension_agents_email",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
        db.Index(
            "uq_extension_agents_employee_id",
            "employee_id",
            unique=True,
            postgresql_where=text("employee_id IS NOT NULL"),
        ),
    )

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

    zone = db.Column(
        db.String(100),
        nullable=True,
    )

    woreda = db.Column(
        db.String(50),
        nullable=True,
    )

    region_id = db.Column(
        db.String(32),
        db.ForeignKey("geography_regions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    zone_id = db.Column(
        db.String(32),
        db.ForeignKey("geography_zones.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    woreda_id = db.Column(
        db.String(32),
        db.ForeignKey("geography_woredas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    email = db.Column(
        db.String(254),
        nullable=True,
    )

    employee_id = db.Column(
        db.String(80),
        nullable=True,
    )

    organization = db.Column(
        db.String(150),
        nullable=True,
    )

    professional_info_verified = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    professional_info_verified_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    professional_info_verified_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    account_status = db.Column(
        db.String(30),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
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
        foreign_keys=[user_id],
        backref=db.backref(
            "extension_agent_profile",
            uselist=False,
        ),
    )

    region_record = db.relationship(
        "GeographyRegion",
        foreign_keys=[region_id],
    )

    zone_record = db.relationship(
        "GeographyZone",
        foreign_keys=[zone_id],
    )

    woreda_record = db.relationship(
        "GeographyWoreda",
        foreign_keys=[woreda_id],
    )

    professional_info_verified_by = db.relationship(
        "User",
        foreign_keys=[professional_info_verified_by_id],
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
