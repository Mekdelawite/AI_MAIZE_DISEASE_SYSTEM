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

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.app.extensions import db
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User


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
    }

    has_farmer_fields = bool(
        farmer_fields.intersection(data.keys())
    )

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