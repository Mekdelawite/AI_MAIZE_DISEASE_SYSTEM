"""
=========================================================
Weather API Routes
=========================================================

REST API endpoints for weather information.

Supported endpoints:
    GET /api/weather/current
    GET /api/weather/farmer

The farmer weather endpoint uses the authenticated
farmer's existing FarmerProfile coordinates.

No duplicate location information is stored.
=========================================================
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
import requests

from backend.app.extensions import db
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User
from backend.app.routes.auth import roles_required
from backend.app.services.weather_service import WeatherService


# =========================================================
# BLUEPRINT
# =========================================================

weather_bp = Blueprint(
    "weather",
    __name__,
    url_prefix="/api/weather",
)


# =========================================================
# CURRENT WEATHER BY CITY
# =========================================================

@weather_bp.get("/current")
def current_weather():
    """
    Get current weather for a requested city.

    Example:
        GET /api/weather/current?city=Bahir%20Dar
    """

    city = request.args.get("city", "").strip()
    units = request.args.get(
        "units",
        "metric",
    ).strip().lower()

    # -----------------------------------------------------
    # Validate city
    # -----------------------------------------------------

    if not city:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "CITY_REQUIRED",
                    "message": "City parameter is required.",
                },
            }
        ), 400

    # -----------------------------------------------------
    # Validate units
    # -----------------------------------------------------

    if units not in {
        "metric",
        "imperial",
        "standard",
    }:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_UNITS",
                    "message": (
                        "Invalid units. Use metric, "
                        "imperial, or standard."
                    ),
                },
            }
        ), 400

    # -----------------------------------------------------
    # Get weather
    # -----------------------------------------------------

    try:
        weather = WeatherService.get_current_weather(
            city=city,
            units=units,
        )

        return jsonify(
            {
                "success": True,
                "data": weather,
            }
        ), 200

    # -----------------------------------------------------
    # Expected errors
    # -----------------------------------------------------

    except ValueError as error:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "WEATHER_REQUEST_ERROR",
                    "message": str(error),
                },
            }
        ), 400

    # -----------------------------------------------------
    # OpenWeather / network errors
    # -----------------------------------------------------

    except requests.RequestException:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "WEATHER_SERVICE_UNAVAILABLE",
                    "message": (
                        "Unable to retrieve weather "
                        "information right now."
                    ),
                },
            }
        ), 503

    # -----------------------------------------------------
    # Unexpected errors
    # -----------------------------------------------------

    except Exception:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "WEATHER_INTERNAL_ERROR",
                    "message": (
                        "An unexpected error occurred "
                        "while retrieving weather."
                    ),
                },
            }
        ), 500


# =========================================================
# FARMER WEATHER BY SAVED LOCATION
# =========================================================

@weather_bp.get("/farmer")
@jwt_required()
@roles_required("farmer")
def farmer_weather():
    """
    Get current weather using the authenticated farmer's
    saved latitude and longitude.

    The coordinates are read from the existing FarmerProfile.

    Example:
        GET /api/weather/farmer

    Optional:
        ?units=metric
        ?units=imperial
        ?units=standard
    """

    # -----------------------------------------------------
    # Validate units
    # -----------------------------------------------------

    units = request.args.get(
        "units",
        "metric",
    ).strip().lower()

    if units not in {
        "metric",
        "imperial",
        "standard",
    }:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_UNITS",
                    "message": (
                        "Invalid units. Use metric, "
                        "imperial, or standard."
                    ),
                },
            }
        ), 400

    # -----------------------------------------------------
    # Get authenticated user
    # -----------------------------------------------------

    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": (
                        "Authenticated user identity is invalid."
                    ),
                },
            }
        ), 401

    user = db.session.get(User, user_id)

    if user is None:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": (
                        "Authenticated user was not found."
                    ),
                },
            }
        ), 404

    if not user.is_active:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "USER_INACTIVE",
                    "message": (
                        "This user account is inactive."
                    ),
                },
            }
        ), 403

    # -----------------------------------------------------
    # Get existing farmer profile
    # -----------------------------------------------------

    farmer_profile = db.session.get(
        FarmerProfile,
        user.id,
    )

    if farmer_profile is None:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "FARMER_PROFILE_NOT_FOUND",
                    "message": (
                        "Farmer profile was not found. "
                        "Please complete your profile first."
                    ),
                },
            }
        ), 404

    # -----------------------------------------------------
    # Validate saved coordinates
    # -----------------------------------------------------

    if (
        farmer_profile.latitude is None
        or farmer_profile.longitude is None
    ):
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "LOCATION_NOT_CONFIGURED",
                    "message": (
                        "Farmer location coordinates are not "
                        "configured. Please update your profile "
                        "with latitude and longitude."
                    ),
                },
            }
        ), 400

    # -----------------------------------------------------
    # Get weather
    # -----------------------------------------------------

    try:
        weather = (
            WeatherService.get_current_weather_by_coordinates(
                latitude=float(farmer_profile.latitude),
                longitude=float(farmer_profile.longitude),
                units=units,
            )
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "farmer_location": {
                        "region": farmer_profile.region,
                        "woreda": farmer_profile.woreda,
                        "kebele": farmer_profile.kebele,
                        "latitude": float(
                            farmer_profile.latitude
                        ),
                        "longitude": float(
                            farmer_profile.longitude
                        ),
                    },
                    "weather": weather,
                },
            }
        ), 200

    # -----------------------------------------------------
    # Expected errors
    # -----------------------------------------------------

    except ValueError as error:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "WEATHER_REQUEST_ERROR",
                    "message": str(error),
                },
            }
        ), 400

    # -----------------------------------------------------
    # OpenWeather / network errors
    # -----------------------------------------------------

    except requests.RequestException:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "WEATHER_SERVICE_UNAVAILABLE",
                    "message": (
                        "Unable to retrieve weather "
                        "information right now."
                    ),
                },
            }
        ), 503

    # -----------------------------------------------------
    # Unexpected errors
    # -----------------------------------------------------

    except Exception:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "WEATHER_INTERNAL_ERROR",
                    "message": (
                        "An unexpected error occurred "
                        "while retrieving farmer weather."
                    ),
                },
            }
        ), 500