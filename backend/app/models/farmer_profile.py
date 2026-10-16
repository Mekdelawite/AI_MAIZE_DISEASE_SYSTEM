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