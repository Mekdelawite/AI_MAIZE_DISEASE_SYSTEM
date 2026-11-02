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

from datetime import date, timedelta

from flask import Blueprint, current_app
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
from backend.app.services.weather_service import WeatherService
from backend.app.services.soil_water_service import SoilWaterService
from backend.app.services.agricultural_advisory_service import AgriculturalAdvisoryService
from backend.app.services.crop_calendar_notification_service import CropCalendarNotificationService
import requests


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
        current_app.logger.exception(
            "Failed to generate crop calendar for user_id=%s",
            user.id,
        )
        return error_response(
            "CROP_CALENDAR_INTERNAL_ERROR",
            "Unable to generate the crop calendar.",
            500,
        )

    calendar["upcoming_reminders"] = CropCalendarNotificationService.attach_status(
        user.id, farmer_profile
    )

    return success_response(calendar)


@crop_calendar_bp.get("/soil-water")
@jwt_required()
@roles_required("farmer")
def get_soil_water_estimate():
    """Return weather-derived, explicitly estimated soil-water information for the JWT owner."""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return error_response("INVALID_USER_ID", "Authenticated user identity is invalid.", 401)
    user = db.session.get(User, user_id)
    if user is None:
        return error_response("USER_NOT_FOUND", "Authenticated user was not found.", 404)
    if not user.is_active:
        return error_response("USER_INACTIVE", "This user account is inactive.", 403)
    profile = db.session.get(FarmerProfile, user.id)
    if profile is None:
        return error_response("FARMER_PROFILE_NOT_FOUND", "Farmer profile has not been configured.", 404)
    historical = None
    forecast = None
    current_weather = None
    if profile.latitude is not None and profile.longitude is not None:
        end = date.today() - timedelta(days=1)
        history_cutoff = end - timedelta(days=365)
        truncated = bool(profile.planting_date and profile.planting_date < history_cutoff)
        start = max(profile.planting_date or (end - timedelta(days=30)), history_cutoff)
        if start <= end:
            try:
                historical = WeatherService.get_historical_water_weather(
                    float(profile.latitude), float(profile.longitude), start.isoformat(), end.isoformat()
                )
                historical["window_truncated"] = truncated
            except (requests.RequestException, ValueError):
                current_app.logger.exception("Historical water weather unavailable for farmer_id=%s", user.id)
        try:
            forecast = WeatherService.get_forecast_by_coordinates(float(profile.latitude), float(profile.longitude))
        except (requests.RequestException, ValueError):
            current_app.logger.exception("Forecast water weather unavailable for farmer_id=%s", user.id)
        try:
            current_weather = WeatherService.get_current_weather_by_coordinates(
                float(profile.latitude), float(profile.longitude), units="metric"
            )
        except (requests.RequestException, ValueError):
            current_app.logger.exception("Current weather unavailable for agricultural advisories (farmer_id=%s)", user.id)
    result = SoilWaterService.calculate(profile, historical, forecast)
    language = user.preferred_language if user.preferred_language in {"en", "am"} else "en"
    calendar = CropCalendarService.get_calendar(
        region=profile.region,
        woreda=profile.woreda,
        kebele=profile.kebele,
        language=language,
    )
    result["current_weather"] = current_weather
    result["forecast_data"] = forecast
    result["advisories"] = AgriculturalAdvisoryService.generate(
        profile=profile,
        calendar=calendar,
        current_weather=current_weather,
        forecast=forecast,
        soil_water=result,
        historical=historical,
    )
    return success_response(result)
