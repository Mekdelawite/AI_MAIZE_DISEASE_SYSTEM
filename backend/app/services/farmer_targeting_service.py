"""
=========================================================
Farmer Targeting Service
=========================================================

Finds farmers who are eligible to receive location-based
SMS alerts.

Responsibilities:
    - Filter farmers by geographic location
    - Check farmer account status
    - Check SMS opt-in preference
    - Ensure a phone number exists
    - Return structured recipient information

This service does NOT send SMS.
SMS delivery is handled by SMSService.
=========================================================
"""

from __future__ import annotations

from typing import Any

from backend.app.models.user import User
from backend.app.models.farmer_profile import FarmerProfile


class FarmerTargetingService:
    """Service for finding farmers who should receive alerts."""

    @staticmethod
    def find_farmers(
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find active farmers who have opted in to SMS alerts
        and match the requested geographic location.

        Args:
            region: Required farmer region.
            woreda: Optional woreda filter.
            kebele: Optional kebele filter.

        Returns:
            List of eligible farmers.
        """

        query = (
            User.query
            .join(FarmerProfile, FarmerProfile.user_id == User.id)
            .filter(
                User.role == "farmer",
                User.is_active.is_(True),
                FarmerProfile.sms_opt_in.is_(True),
                User.phone_number.isnot(None),
                FarmerProfile.region == region,
            )
        )

        if woreda is not None:
            query = query.filter(FarmerProfile.woreda == woreda)

        if kebele is not None:
            query = query.filter(FarmerProfile.kebele == kebele)

        farmers = query.all()

        return [
            {
                "user_id": farmer.id,
                "full_name": farmer.full_name,
                "phone_number": farmer.phone_number,
                "preferred_language": farmer.preferred_language,
                "region": farmer.farmer_profile.region,
                "woreda": farmer.farmer_profile.woreda,
                "kebele": farmer.farmer_profile.kebele,
            }
            for farmer in farmers
        ]

    @staticmethod
    def count_farmers(
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
    ) -> int:
        """
        Count eligible farmers in a geographic area.
        """

        return len(
            FarmerTargetingService.find_farmers(
                region=region,
                woreda=woreda,
                kebele=kebele,
            )
        )