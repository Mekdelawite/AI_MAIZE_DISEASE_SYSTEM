"""
=========================================================
Crop Calendar API Routes
=========================================================

Farmer-specific Ethiopian maize crop calendar.

Endpoint:
    GET /api/crop-calendar

The endpoint reuses:
    - User.preferred_language
    - FarmerProfile region/woreda/kebele

No duplicate farmer-location or language storage
is introduced.

=========================================================
"""

from __future__ import annotations

from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.app.extensions import db
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User
from backend.app.routes.auth import (
    error_response,
    roles_required,
    success_response,
)
from backend.app.services.crop_calendar_service import (
    CropCalendarService,
)


crop_calendar_bp = Blueprint(
    "crop_calendar",
    __name__,
    url_prefix="/api/crop-calendar",
)


@crop_calendar_bp.get("")
@jwt_required()
@roles_required("farmer")
def get_crop_calendar():
    """
    Return the maize crop calendar for the authenticated
    farmer's existing agricultural location and preferred
    language.
    """

    identity = get_jwt_identity()

    try:
        user_id = int(identity)

    except (TypeError, ValueError):
        return error_response(
            "INVALID_USER_ID",
            "Authenticated user identity is invalid.",
            401,
        )

    user = db.session.get(User, user_id)

    if user is None:
        return error_response(
            "USER_NOT_FOUND",
            "Authenticated user was not found.",
            404,
        )

    if not user.is_active:
        return error_response(
            "USER_INACTIVE",
            "This user account is inactive.",
            403,
        )

    farmer_profile = db.session.get(
        FarmerProfile,
        user.id,
    )

    if farmer_profile is None:
        return error_response(
            "FARMER_PROFILE_NOT_FOUND",
            "Farmer profile has not been configured.",
            404,
        )

    if not farmer_profile.region:
        return error_response(
            "LOCATION_NOT_CONFIGURED",
            "Farmer region has not been configured.",
            400,
        )

    language = (
        user.preferred_language
        if user.preferred_language in {"en", "am"}
        else "en"
    )

    try:
        calendar = CropCalendarService.get_calendar(
            region=farmer_profile.region,
            woreda=farmer_profile.woreda,
            kebele=farmer_profile.kebele,
            language=language,
        )

    except ValueError as exc:
        return error_response(
            "CROP_CALENDAR_ERROR",
            str(exc),
            400,
        )

    except Exception:
        return error_response(
            "CROP_CALENDAR_INTERNAL_ERROR",
            "Unable to generate the crop calendar.",
            500,
        )

    return success_response(calendar)