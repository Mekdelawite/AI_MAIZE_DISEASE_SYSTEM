"""
=========================================================
Farmer Profile Model
=========================================================

Stores agricultural and location information specific
to farmers.

Authentication and common account information remain in
the users table.

This model stores:
    - Farmer's assigned region
    - Farmer's assigned woreda
    - Farmer's kebele
    - Farmer's latitude
    - Farmer's longitude
    - Farmer's SMS notification preference

Relationship:
    User 1 ---- 1 FarmerProfile
=========================================================
"""

from __future__ import annotations

from backend.app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB


class FarmerProfile(db.Model):
    """
    Agricultural profile for a farmer.

    user_id is both the primary key and foreign key,
    creating a one-to-one relationship with User.
    """

    __tablename__ = "farmer_profiles"

    # =====================================================
    # FARMER / USER ID
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
    # LOCATION
    # =====================================================

    region = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    woreda = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    kebele = db.Column(
        db.String(50),
        nullable=True,
    )

    latitude = db.Column(
        db.Numeric(9, 6),
        nullable=True,
    )

    longitude = db.Column(
        db.Numeric(9, 6),
        nullable=True,
    )

    # =====================================================
    # SMS PREFERENCE
    # =====================================================

    sms_opt_in = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    # Nullable for legacy rows; the profile API supplies backward-compatible defaults.
    notification_preferences = db.Column(db.JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Optional farmer-confirmed inputs for transparent soil-water estimates.
    planting_date = db.Column(db.Date, nullable=True)
    soil_type = db.Column(db.String(40), nullable=True)
    available_water_capacity_mm_per_m = db.Column(db.Numeric(7, 2), nullable=True)
    crop_growth_stage = db.Column(db.String(24), nullable=True)
    irrigation_status = db.Column(db.String(16), nullable=True)
    last_irrigation_date = db.Column(db.Date, nullable=True)
    last_irrigation_mm = db.Column(db.Numeric(7, 2), nullable=True)

    # =====================================================
    # RELATIONSHIP
    # =====================================================

    user = db.relationship(
        "User",
        backref=db.backref(
            "farmer_profile",
            uselist=False,
        ),
    )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<FarmerProfile "
            f"user_id={self.user_id} "
            f"region={self.region!r} "
            f"woreda={self.woreda!r} "
            f"kebele={self.kebele!r} "
            f"latitude={self.latitude!r} "
            f"longitude={self.longitude!r} "
            f"sms_opt_in={self.sms_opt_in!r}>"
        )
