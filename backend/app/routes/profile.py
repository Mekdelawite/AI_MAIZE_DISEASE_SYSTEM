"""
=========================================================
Farmer Profile API Routes
=========================================================

Provides authenticated user and farmer profile management.

Endpoints:
    GET  /api/profile
    PUT  /api/profile

User information:
    - full_name
    - preferred_language

Farmer information:
    - region
    - woreda
    - kebele
    - latitude
    - longitude
    - sms_opt_in

The authenticated user's ID is obtained from the JWT.

=========================================================
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.app.extensions import db
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.advisory_record import AdvisoryRecord
from backend.app.models.discussion_post import DiscussionPost
from backend.app.models.discussion_reply import DiscussionReply
from backend.app.models.discussion_post_like import DiscussionPostLike
from backend.app.models.farmer_notification import FarmerNotification
from backend.app.models.offline_sync_record import OfflineSyncRecord
from backend.app.models.password_reset_otp import PasswordResetOTP
from backend.app.models.extension_comment import ExtensionComment

NOTIFICATION_CATEGORIES = ("crop_activity", "weather_alert", "soil_water_alert", "agricultural_advisory", "important_alerts")
DEFAULT_NOTIFICATION_PREFERENCES = {
    "categories": {key: {"in_app": True, "sms": True, "push": False} for key in NOTIFICATION_CATEGORIES},
    "reminder_days_before": 0,
    "quiet_hours": {"enabled": False, "start": "21:00", "end": "07:00"},
    "timezone": "Africa/Addis_Ababa",
}


def _notification_preferences(profile):
    saved = profile.notification_preferences or {}
    if not isinstance(saved, dict):
        saved = {}
    result = {**DEFAULT_NOTIFICATION_PREFERENCES, **saved}
    result["categories"] = {key: {**DEFAULT_NOTIFICATION_PREFERENCES["categories"][key], **(saved.get("categories", {}).get(key) or {})} for key in NOTIFICATION_CATEGORIES}
    result["quiet_hours"] = {**DEFAULT_NOTIFICATION_PREFERENCES["quiet_hours"], **(saved.get("quiet_hours") or {})}
    return result


def _valid_notification_preferences(value):
    if not isinstance(value, dict) or set(value) != {"categories", "reminder_days_before", "quiet_hours", "timezone"}:
        return False
    categories = value.get("categories")
    if not isinstance(categories, dict) or set(categories) != set(NOTIFICATION_CATEGORIES):
        return False
    if any(not isinstance(v, dict) or set(v) != {"in_app", "sms", "push"} or any(not isinstance(v[k], bool) for k in ("in_app", "sms", "push")) for v in categories.values()):
        return False
    if type(value.get("reminder_days_before")) is not int or value["reminder_days_before"] not in (0, 1, 2, 3):
        return False
    quiet = value.get("quiet_hours")
    if not isinstance(quiet, dict) or set(quiet) != {"enabled", "start", "end"} or not isinstance(quiet.get("enabled"), bool):
        return False
    import re
    if any(not isinstance(quiet.get(k), str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", quiet[k]) for k in ("start", "end")):
        return False
    if not isinstance(value.get("timezone"), str) or len(value["timezone"]) > 64:
        return False
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(value["timezone"])
    except Exception:
        return False
    return True


# =========================================================
# BLUEPRINT
# =========================================================

profile_bp = Blueprint(
    "profile",
    __name__,
    url_prefix="/api",
)


# =========================================================
# HELPERS
# =========================================================

def _get_authenticated_user():
    """
    Get the User associated with the current JWT.
    """

    identity = get_jwt_identity()

    try:
        user_id = int(identity)

    except (TypeError, ValueError):

        return None, jsonify(
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

        return None, jsonify(
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

        return None, jsonify(
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

    return user, None, None


def _serialize_user(user: User) -> dict:
    """
    Convert a User model into a safe API response.

    Sensitive information such as the password hash
    is never returned.
    """

    return {
        "id": user.id,
        "phone_number": user.phone_number,
        "full_name": user.full_name,
        "preferred_language": user.preferred_language,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        ),
        "updated_at": (
            user.updated_at.isoformat()
            if user.updated_at
            else None
        ),
    }


def _serialize_farmer_profile(
    farmer_profile: FarmerProfile | None,
) -> dict | None:
    """
    Convert a FarmerProfile into a safe API response.
    """

    if farmer_profile is None:
        return None

    return {
        "user_id": farmer_profile.user_id,
        "region": farmer_profile.region,
        "woreda": farmer_profile.woreda,
        "kebele": farmer_profile.kebele,
        "latitude": (
            float(farmer_profile.latitude)
            if farmer_profile.latitude is not None
            else None
        ),
        "longitude": (
            float(farmer_profile.longitude)
            if farmer_profile.longitude is not None
            else None
        ),
        "sms_opt_in": farmer_profile.sms_opt_in,
        "notification_preferences": _notification_preferences(farmer_profile),
        "planting_date": farmer_profile.planting_date.isoformat() if farmer_profile.planting_date else None,
        "soil_type": farmer_profile.soil_type,
        "available_water_capacity_mm_per_m": float(farmer_profile.available_water_capacity_mm_per_m) if farmer_profile.available_water_capacity_mm_per_m is not None else None,
        "crop_growth_stage": farmer_profile.crop_growth_stage,
        "irrigation_status": farmer_profile.irrigation_status,
        "last_irrigation_date": farmer_profile.last_irrigation_date.isoformat() if farmer_profile.last_irrigation_date else None,
        "last_irrigation_mm": float(farmer_profile.last_irrigation_mm) if farmer_profile.last_irrigation_mm is not None else None,
    }


# =========================================================
# GET PROFILE
# =========================================================

@profile_bp.get("/profile")
@jwt_required()
def get_profile():
    """
    Return the authenticated user's profile.

    For farmers, the response also includes the
    FarmerProfile information.
    """

    user, error_response, status_code = (
        _get_authenticated_user()
    )

    if error_response is not None:
        return error_response, status_code

    farmer_profile = None

    if user.role == "farmer":

        farmer_profile = db.session.get(
            FarmerProfile,
            user.id,
        )

    return jsonify(
        {
            "success": True,
            "data": {
                "user": _serialize_user(user),
                "farmer_profile": _serialize_farmer_profile(
                    farmer_profile
                ),
            },
        }
    ), 200


@profile_bp.delete("/profile/account")
@jwt_required()
def delete_farmer_account():
    """Permanently delete the authenticated farmer's account after password confirmation."""
    user, response, status_code = _get_authenticated_user()
    if response is not None:
        return response, status_code
    if user.role != "farmer":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Only farmers can delete an account from this page."}}), 403

    payload = request.get_json(silent=True) or {}
    password = payload.get("password")
    if not isinstance(password, str) or not password:
        return jsonify({"success": False, "error": {"code": "PASSWORD_REQUIRED", "message": "Enter your password to confirm account deletion."}}), 400
    if not user.check_password(password):
        return jsonify({"success": False, "error": {"code": "INVALID_PASSWORD", "message": "The password is incorrect."}}), 401

    user_id = user.id
    try:
        # Remove dependent rows explicitly to avoid nullable-FK updates by ORM relationships.
        diagnosis_ids = db.session.query(DiagnosisRecord.id).filter_by(user_id=user_id).subquery()
        ExtensionComment.query.filter(ExtensionComment.diagnosis_id.in_(diagnosis_ids)).delete(synchronize_session=False)
        AdvisoryRecord.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        DiagnosisRecord.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        FarmerProfile.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        FarmerNotification.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        OfflineSyncRecord.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        PasswordResetOTP.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        DiscussionReply.query.filter_by(farmer_id=user_id).delete(synchronize_session=False)
        DiscussionPost.query.filter_by(author_id=user_id).delete(synchronize_session=False)
        DiscussionPostLike.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to delete farmer account %s.", user_id)
        return jsonify({"success": False, "error": {"code": "ACCOUNT_DELETE_FAILED", "message": "Unable to delete account. Please try again."}}), 500

    return jsonify({"success": True, "data": {"deleted": True}}), 200


# =========================================================
# UPDATE PROFILE
# =========================================================

@profile_bp.put("/profile")
@jwt_required()
def update_profile():
    """
    Update the authenticated user's profile.

    User fields:
        full_name
        preferred_language

    Farmer fields:
        region
        woreda
        kebele
        latitude
        longitude
        sms_opt_in

    Protected:
        id
        phone_number
        role
        is_active
        created_at
        updated_at
    """

    user, error_response, status_code = (
        _get_authenticated_user()
    )

    if error_response is not None:
        return error_response, status_code

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": (
                        "Request body must contain valid JSON."
                    ),
                },
            }
        ), 400

    allowed_fields = {
        "full_name",
        "preferred_language",
        "region",
        "woreda",
        "kebele",
        "latitude",
        "longitude",
        "sms_opt_in",
        "planting_date",
        "soil_type",
        "available_water_capacity_mm_per_m",
        "crop_growth_stage",
        "irrigation_status",
        "last_irrigation_date",
        "last_irrigation_mm",
        "notification_preferences",
    }

    unknown_fields = set(data.keys()) - allowed_fields

    if unknown_fields:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "UNSUPPORTED_FIELDS",
                    "message": (
                        "Unsupported profile fields: "
                        + ", ".join(
                            sorted(unknown_fields)
                        )
                    ),
                },
            }
        ), 400

    if not data:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "NO_FIELDS_TO_UPDATE",
                    "message": (
                        "Provide at least one supported "
                        "profile field."
                    ),
                },
            }
        ), 400

    # =====================================================
    # USER: FULL NAME
    # =====================================================

    if "full_name" in data:

        full_name = data.get("full_name")

        if not isinstance(full_name, str):

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_FULL_NAME",
                        "message": (
                            "Full name must be a string."
                        ),
                    },
                }
            ), 400

        full_name = full_name.strip()

        if not full_name:

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_FULL_NAME",
                        "message": (
                            "Full name cannot be empty."
                        ),
                    },
                }
            ), 400

        if len(full_name) > 120:

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_FULL_NAME",
                        "message": (
                            "Full name must not exceed "
                            "120 characters."
                        ),
                    },
                }
            ), 400

        user.full_name = full_name

    # =====================================================
    # USER: PREFERRED LANGUAGE
    # =====================================================

    if "preferred_language" in data:

        language = data.get("preferred_language")

        if not isinstance(language, str):

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_LANGUAGE",
                        "message": (
                            "Preferred language must be "
                            "a string."
                        ),
                    },
                }
            ), 400

        language = language.lower().strip()

        if language not in {"en", "am"}:

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "UNSUPPORTED_LANGUAGE",
                        "message": (
                            "Supported languages are "
                            "'en' and 'am'."
                        ),
                    },
                }
            ), 400

        user.preferred_language = language

    # =====================================================
    # FARMER PROFILE
    # =====================================================

    farmer_fields = {
        "region",
        "woreda",
        "kebele",
        "latitude",
        "longitude",
        "sms_opt_in",
        "planting_date",
        "soil_type",
        "available_water_capacity_mm_per_m",
        "crop_growth_stage",
        "irrigation_status",
        "last_irrigation_date",
        "last_irrigation_mm",
        "notification_preferences",
    }

    has_farmer_fields = bool(
        farmer_fields.intersection(data.keys())
    )

    if "notification_preferences" in data and not _valid_notification_preferences(data["notification_preferences"]):
        return jsonify({"success": False, "error": {"code": "INVALID_NOTIFICATION_PREFERENCES", "message": "Notification preferences contain invalid categories, channels, timing, quiet hours, or timezone."}}), 400

    farmer_profile = None

    if has_farmer_fields:

        if user.role != "farmer":

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "NOT_A_FARMER",
                        "message": (
                            "Farmer profile fields can only "
                            "be updated by farmer accounts."
                        ),
                    },
                }
            ), 403

        farmer_profile = db.session.get(
            FarmerProfile,
            user.id,
        )

        # -------------------------------------------------
        # Create profile if it doesn't exist
        # -------------------------------------------------

        if farmer_profile is None:

            farmer_profile = FarmerProfile(
                user_id=user.id,
                region="",
                woreda="",
                kebele=None,
                latitude=None,
                longitude=None,
                sms_opt_in=False,
            )

            db.session.add(farmer_profile)

        if "notification_preferences" in data:
            farmer_profile.notification_preferences = data["notification_preferences"]

        # Validate optional agricultural estimate inputs before assigning them.
        date_fields = ("planting_date", "last_irrigation_date")
        for field in date_fields:
            if field in data:
                value = data[field]
                if value in (None, ""):
                    setattr(farmer_profile, field, None)
                elif not isinstance(value, str):
                    return jsonify({"success": False, "error": {"code": "INVALID_DATE", "message": f"{field} must use YYYY-MM-DD."}}), 400
                else:
                    try:
                        parsed = date.fromisoformat(value)
                    except ValueError:
                        return jsonify({"success": False, "error": {"code": "INVALID_DATE", "message": f"{field} must use YYYY-MM-DD."}}), 400
                    if parsed > date.today():
                        return jsonify({"success": False, "error": {"code": "INVALID_DATE", "message": f"{field} cannot be in the future."}}), 400
                    setattr(farmer_profile, field, parsed)

        if "soil_type" in data:
            soil = data["soil_type"]
            allowed_soils = {"sand", "loamy_sand", "sandy_loam", "loam", "silt_loam", "silt", "sandy_clay_loam", "clay_loam", "silty_clay_loam", "sandy_clay", "silty_clay", "clay"}
            if soil in (None, ""):
                farmer_profile.soil_type = None
            elif not isinstance(soil, str) or soil not in allowed_soils:
                return jsonify({"success": False, "error": {"code": "INVALID_SOIL_TYPE", "message": "Select a supported soil texture."}}), 400
            else:
                farmer_profile.soil_type = soil

        if "available_water_capacity_mm_per_m" in data:
            raw = data["available_water_capacity_mm_per_m"]
            if raw in (None, ""):
                farmer_profile.available_water_capacity_mm_per_m = None
            else:
                try:
                    awc = float(raw)
                except (TypeError, ValueError):
                    return jsonify({"success": False, "error": {"code": "INVALID_AWC", "message": "Available water capacity must be numeric."}}), 400
                if not 1 <= awc <= 300:
                    return jsonify({"success": False, "error": {"code": "INVALID_AWC", "message": "Available water capacity must be between 1 and 300 mm/m."}}), 400
                farmer_profile.available_water_capacity_mm_per_m = awc

        if "crop_growth_stage" in data:
            stage = data["crop_growth_stage"]
            allowed_stages = {"initial", "development", "mid_season", "late_season"}
            if stage in (None, ""):
                farmer_profile.crop_growth_stage = None
            elif not isinstance(stage, str) or stage not in allowed_stages:
                return jsonify({"success": False, "error": {"code": "INVALID_GROWTH_STAGE", "message": "Select a supported maize growth stage."}}), 400
            else:
                farmer_profile.crop_growth_stage = stage

        if "irrigation_status" in data:
            status = data["irrigation_status"]
            if status in (None, ""):
                farmer_profile.irrigation_status = None
            elif status not in {"unknown", "rainfed", "irrigated"}:
                return jsonify({"success": False, "error": {"code": "INVALID_IRRIGATION_STATUS", "message": "Select unknown, rainfed, or irrigated."}}), 400
            else:
                farmer_profile.irrigation_status = status

        if "last_irrigation_mm" in data:
            raw = data["last_irrigation_mm"]
            if raw in (None, ""):
                farmer_profile.last_irrigation_mm = None
            else:
                try:
                    depth = float(raw)
                except (TypeError, ValueError):
                    return jsonify({"success": False, "error": {"code": "INVALID_IRRIGATION", "message": "Irrigation depth must be numeric."}}), 400
                if not 0 < depth <= 200:
                    return jsonify({"success": False, "error": {"code": "INVALID_IRRIGATION", "message": "Irrigation depth must be between 0 and 200 mm."}}), 400
                farmer_profile.last_irrigation_mm = depth

        # -------------------------------------------------
        # REGION
        # -------------------------------------------------

        if "region" in data:

            region = data.get("region")

            if not isinstance(region, str):

                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_REGION",
                            "message": (
                                "Region must be a string."
                            ),
                        },
                    }
                ), 400

            region = region.strip()

            if not region:

                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_REGION",
                            "message": (
                                "Region cannot be empty."
                            ),
                        },
                    }
                ), 400

            if len(region) > 50:

                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_REGION",
                            "message": (
                                "Region must not exceed "
                                "50 characters."
                            ),
                        },
                    }
                ), 400

            farmer_profile.region = region

        # -------------------------------------------------
        # WOREDA
        # -------------------------------------------------

        if "woreda" in data:

            woreda = data.get("woreda")

            if not isinstance(woreda, str):

                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_WOREDA",
                            "message": (
                                "Woreda must be a string."
                            ),
                        },
                    }
                ), 400

            woreda = woreda.strip()

            if not woreda:

                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_WOREDA",
                            "message": (
                                "Woreda cannot be empty."
                            ),
                        },
                    }
                ), 400

            if len(woreda) > 50:

                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_WOREDA",
                            "message": (
                                "Woreda must not exceed "
                                "50 characters."
                            ),
                        },
                    }
                ), 400

            farmer_profile.woreda = woreda

        # -------------------------------------------------
        # KEBELE
        # -------------------------------------------------

        if "kebele" in data:

            kebele = data.get("kebele")

            if kebele is not None:

                if not isinstance(kebele, str):

                    return jsonify(
                        {
                            "success": False,
                            "error": {
                                "code": "INVALID_KEBELE",
                                "message": (
                                    "Kebele must be a string "
                                    "or null."
                                ),
                            },
                        }
                    ), 400

                kebele = kebele.strip()

                if not kebele:

                    kebele = None

                elif len(kebele) > 50:

                    return jsonify(
                        {
                            "success": False,
                            "error": {
                                "code": "INVALID_KEBELE",
                                "message": (
                                    "Kebele must not exceed "
                                    "50 characters."
                                ),
                            },
                        }
                    ), 400

            farmer_profile.kebele = kebele

        # -------------------------------------------------
        # LATITUDE
        # -------------------------------------------------

        if "latitude" in data:

            latitude = data.get("latitude")

            if latitude is not None:

                try:
                    latitude = float(latitude)

                except (TypeError, ValueError):

                    return jsonify(
                        {
                            "success": False,
                            "error": {
                                "code": "INVALID_LATITUDE",
                                "message": (
                                    "Latitude must be a "
                                    "valid number or null."
                                ),
                            },
                        }
                    ), 400

                if not -90 <= latitude <= 90:

                    return jsonify(
                        {
                            "success": False,
                            "error": {
                                "code": "INVALID_LATITUDE",
                                "message": (
                                    "Latitude must be "
                                    "between -90 and 90."
                                ),
                            },
                        }
                    ), 400

            farmer_profile.latitude = latitude

        # -------------------------------------------------
        # LONGITUDE
        # -------------------------------------------------

        if "longitude" in data:

            longitude = data.get("longitude")

            if longitude is not None:

                try:
                    longitude = float(longitude)

                except (TypeError, ValueError):

                    return jsonify(
                        {
                            "success": False,
                            "error": {
                                "code": "INVALID_LONGITUDE",
                                "message": (
                                    "Longitude must be a "
                                    "valid number or null."
                                ),
                            },
                        }
                    ), 400

                if not -180 <= longitude <= 180:

                    return jsonify(
                        {
                            "success": False,
                            "error": {
                                "code": "INVALID_LONGITUDE",
                                "message": (
                                    "Longitude must be "
                                    "between -180 and 180."
                                ),
                            },
                        }
                    ), 400

            farmer_profile.longitude = longitude

        # -------------------------------------------------
        # SMS OPT-IN
        # -------------------------------------------------

        if "sms_opt_in" in data:

            sms_opt_in = data.get("sms_opt_in")

            if not isinstance(sms_opt_in, bool):

                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_SMS_OPT_IN",
                            "message": (
                                "sms_opt_in must be "
                                "true or false."
                            ),
                        },
                    }
                ), 400

            farmer_profile.sms_opt_in = sms_opt_in

    # =====================================================
    # SAVE
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": (
                        "Unable to update profile."
                    ),
                },
            }
        ), 500

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify(
        {
            "success": True,
            "data": {
                "message": (
                    "Profile updated successfully."
                ),
                "user": _serialize_user(user),
                "farmer_profile": _serialize_farmer_profile(
                    farmer_profile
                ),
            },
        }
    ), 200
