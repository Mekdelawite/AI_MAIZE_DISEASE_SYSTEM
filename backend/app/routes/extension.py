"""
=========================================================
Extension Agent Routes
=========================================================

Extension Agent Regional Monitoring & Support

Responsibilities:
    - View diagnoses within assigned region/woreda
    - Filter diagnoses by disease and date
    - View individual diagnosis details
    - Maintain strict regional assignment security
    - Provide regional diagnosis statistics
    - Provide disease trends
    - Provide cases by woreda
    - Provide geographic diagnosis data

Role:
    extension_agent

Security:
    - JWT authentication required
    - Extension-agent role required
    - Agents can only access their assigned region
    - If a woreda is assigned, access is restricted to that woreda
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from backend.app.extensions import db
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User
from backend.app.routes.auth import roles_required


# =========================================================
# BLUEPRINT
# =========================================================

extension_bp = Blueprint(
    "extension",
    __name__,
    url_prefix="/api/extension",
)


# =========================================================
# RESPONSE HELPERS
# =========================================================

def success_response(
    data: Any,
    status_code: int = 200,
):
    """
    Standard successful API response.
    """

    return jsonify(
        {
            "success": True,
            "data": data,
        }
    ), status_code


def error_response(
    code: str,
    message: str,
    status_code: int,
):
    """
    Standard error API response.
    """

    return jsonify(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        }
    ), status_code


# =========================================================
# =========================================================
# AUTHENTICATION / ASSIGNMENT HELPERS
# =========================================================

def _get_authenticated_agent():
    """
    Get the currently authenticated extension agent.

    Returns:
        tuple[User | None, ExtensionAgent | None]
    """

    user_id = get_jwt_identity()

    if user_id is None:
        return None, None

    try:
        user_id = int(user_id)

    except (
        TypeError,
        ValueError,
    ):
        return None, None

    # Use SQLAlchemy 2.x style session.get().
    user = db.session.get(
        User,
        user_id,
    )

    if user is None:
        return None, None

    # Confirm actual database role.
    if (
        str(user.role)
        .strip()
        .lower()
        != "extension_agent"
    ):
        return None, None

    agent_profile = db.session.get(
        ExtensionAgent,
        user.id,
    )

    if agent_profile is None:
        return None, None

    return user, agent_profile


def _get_agent_location(
    agent_profile: ExtensionAgent,
):
    """
    Return the agent's assigned region and woreda.
    """

    region = (
        agent_profile.region or ""
    ).strip()

    woreda = (
        agent_profile.woreda or ""
    ).strip()

    return (
        region,
        woreda,
    )


def _diagnosis_is_in_agent_area(
    diagnosis: DiagnosisRecord,
    agent_profile: ExtensionAgent,
) -> bool:
    """
    Check whether a diagnosis belongs to the
    agent's assigned geographical area.
    """

    if diagnosis is None:
        return False

    farmer = diagnosis.user

    if farmer is None:
        return False

    if (
        str(farmer.role)
        .strip()
        .lower()
        != "farmer"
    ):
        return False

    farmer_profile = (
        farmer.farmer_profile
    )

    if farmer_profile is None:
        return False

    agent_region = (
        agent_profile.region or ""
    ).strip()

    farmer_region = (
        farmer_profile.region or ""
    ).strip()

    if not agent_region:
        return False

    if not farmer_region:
        return False

    # Region must always match.
    if agent_region != farmer_region:
        return False

    agent_woreda = (
        agent_profile.woreda or ""
    ).strip()

    farmer_woreda = (
        farmer_profile.woreda or ""
    ).strip()

    # If the agent has a woreda assignment,
    # the farmer must belong to that exact woreda.
    if agent_woreda:

        if not farmer_woreda:
            return False

        if agent_woreda != farmer_woreda:
            return False

    return True


def _get_assigned_diagnosis(
    diagnosis_id: int,
    agent_profile: ExtensionAgent,
):
    """
    Retrieve one diagnosis only if it belongs to the
    authenticated agent's assigned area.
    """

    query = (
        DiagnosisRecord.query
        .join(
            User,
            DiagnosisRecord.user_id == User.id,
        )
        .join(
            FarmerProfile,
            FarmerProfile.user_id == User.id,
        )
        .filter(
            DiagnosisRecord.id == diagnosis_id,
            User.role == "farmer",
            FarmerProfile.region
            == agent_profile.region,
        )
    )

    if agent_profile.woreda:

        query = query.filter(
            FarmerProfile.woreda
            == agent_profile.woreda
        )

    return query.first()


# =========================================================
# SERIALIZATION
# =========================================================

def _serialize_diagnosis(
    diagnosis: DiagnosisRecord,
):
    """
    Convert a DiagnosisRecord into an API-safe
    dictionary.
    """

    farmer = diagnosis.user

    farmer_profile = (
        farmer.farmer_profile
        if farmer
        else None
    )

    return {
        "id": diagnosis.id,

        "farmer": {
            "id": (
                farmer.id
                if farmer
                else None
            ),

            "full_name": (
                farmer.full_name
                if farmer
                else None
            ),

            "phone_number": (
                farmer.phone_number
                if farmer
                else None
            ),
        },

        "farmer_location": {
            "region": (
                farmer_profile.region
                if farmer_profile
                else None
            ),

            "woreda": (
                farmer_profile.woreda
                if farmer_profile
                else None
            ),
        },

        "image_filename": (
            diagnosis.image_filename
        ),

        "disease_class": (
            diagnosis.disease_class
        ),

        "confidence": (
            diagnosis.confidence
        ),

        "model_name": (
            diagnosis.model_name
        ),

        "model_version": (
            diagnosis.model_version
        ),

        "prediction_time": (
            diagnosis.prediction_time
        ),

        "explainability_requested": (
            diagnosis.explainability_requested
        ),

        "heatmap_path": (
            diagnosis.heatmap_path
        ),

        "created_at": (
            diagnosis.created_at.isoformat()
            if diagnosis.created_at
            else None
        ),
    }


# =========================================================
# DATE HELPERS
# =========================================================

def _parse_date(
    value: str,
):
    """
    Parse a YYYY-MM-DD date.

    Returns:
        timezone-aware UTC datetime
        or None if invalid.
    """

    try:

        parsed_date = datetime.strptime(
            value,
            "%Y-%m-%d",
        )

        return parsed_date.replace(
            tzinfo=timezone.utc
        )

    except ValueError:

        return None


# =========================================================
# 7.1 REGIONAL DIAGNOSIS MONITORING
# =========================================================

@extension_bp.get("/diagnoses")
@jwt_required()
@roles_required("extension_agent")
def get_diagnoses():
    """
    Get diagnoses within the authenticated
    extension agent's assigned region/woreda.

    Supported query parameters:

        page
        per_page
        disease_class
        start_date
        end_date

    Date format:

        YYYY-MM-DD

    Examples:

        /api/extension/diagnoses

        /api/extension/diagnoses?disease_class=Blight

        /api/extension/diagnoses?start_date=2026-09-01

        /api/extension/diagnoses?end_date=2026-09-08

        /api/extension/diagnoses?
            disease_class=Blight&
            start_date=2026-09-01&
            end_date=2026-09-08
    """

    try:

        # =================================================
        # AUTHENTICATED AGENT
        # =================================================

        agent_user, agent_profile = (
            _get_authenticated_agent()
        )

        if (
            agent_user is None
            or agent_profile is None
        ):
            return error_response(
                "EXTENSION_AGENT_NOT_FOUND",
                (
                    "Extension agent profile "
                    "was not found."
                ),
                404,
            )

        # =================================================
        # AGENT ASSIGNMENT
        # =================================================

        agent_region, agent_woreda = (
            _get_agent_location(
                agent_profile
            )
        )

        if not agent_region:

            return error_response(
                "INVALID_AGENT_ASSIGNMENT",
                (
                    "Extension agent has "
                    "no assigned region."
                ),
                400,
            )

        # =================================================
        # PAGINATION
        # =================================================

        page = request.args.get(
            "page",
            default=1,
            type=int,
        )

        per_page = request.args.get(
            "per_page",
            default=20,
            type=int,
        )

        if page is None or page < 1:
            page = 1

        if (
            per_page is None
            or per_page < 1
        ):
            per_page = 20

        if per_page > 100:
            per_page = 100

        # =================================================
        # DISEASE FILTER
        # =================================================

        disease_class = request.args.get(
            "disease_class",
            default=None,
            type=str,
        )

        if disease_class is not None:

            disease_class = (
                disease_class.strip()
            )

            if not disease_class:
                disease_class = None

        # =================================================
        # DATE FILTERS
        # =================================================

        start_date_value = request.args.get(
            "start_date",
            default=None,
            type=str,
        )

        end_date_value = request.args.get(
            "end_date",
            default=None,
            type=str,
        )

        start_datetime = None
        end_datetime = None

        # -------------------------------------------------
        # START DATE
        # -------------------------------------------------

        if start_date_value:

            start_date_value = (
                start_date_value.strip()
            )

            start_datetime = _parse_date(
                start_date_value
            )

            if start_datetime is None:

                return error_response(
                    "INVALID_START_DATE",
                    (
                        "start_date must use "
                        "YYYY-MM-DD format."
                    ),
                    400,
                )

        # -------------------------------------------------
        # END DATE
        # -------------------------------------------------

        if end_date_value:

            end_date_value = (
                end_date_value.strip()
            )

            parsed_end_date = _parse_date(
                end_date_value
            )

            if parsed_end_date is None:

                return error_response(
                    "INVALID_END_DATE",
                    (
                        "end_date must use "
                        "YYYY-MM-DD format."
                    ),
                    400,
                )

            # Make the end date inclusive.

            end_datetime = (
                parsed_end_date
                + timedelta(days=1)
            )

        # -------------------------------------------------
        # DATE RANGE VALIDATION
        # -------------------------------------------------

        if (
            start_datetime is not None
            and end_datetime is not None
            and start_datetime >= end_datetime
        ):

            return error_response(
                "INVALID_DATE_RANGE",
                (
                    "start_date must be earlier "
                    "than or equal to end_date."
                ),
                400,
            )

        # =================================================
        # BASE QUERY
        # =================================================

        query = (
            DiagnosisRecord.query
            .join(
                User,
                DiagnosisRecord.user_id
                == User.id,
            )
            .join(
                FarmerProfile,
                FarmerProfile.user_id
                == User.id,
            )
            .filter(
                User.role == "farmer",
                FarmerProfile.region
                == agent_region,
            )
        )

        # =================================================
        # WOREDA RESTRICTION
        # =================================================

        if agent_woreda:

            query = query.filter(
                FarmerProfile.woreda
                == agent_woreda
            )

        # =================================================
        # DISEASE FILTER
        # =================================================

        if disease_class:

            query = query.filter(
                DiagnosisRecord.disease_class
                == disease_class
            )

        # =================================================
        # START DATE FILTER
        # =================================================

        if start_datetime is not None:

            query = query.filter(
                DiagnosisRecord.created_at
                >= start_datetime
            )

        # =================================================
        # END DATE FILTER
        # =================================================

        if end_datetime is not None:

            query = query.filter(
                DiagnosisRecord.created_at
                < end_datetime
            )

        # =================================================
        # ORDER
        # =================================================

        query = query.order_by(
            DiagnosisRecord.created_at.desc()
        )

        # =================================================
        # PAGINATION
        # =================================================

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

        # =================================================
        # SERIALIZE
        # =================================================

        diagnoses = [
            _serialize_diagnosis(
                diagnosis
            )
            for diagnosis in pagination.items
        ]

        # =================================================
        # RESPONSE
        # =================================================

        return success_response(
            {
                "agent_assignment": {
                    "region": agent_region,
                    "woreda": (
                        agent_woreda
                        if agent_woreda
                        else None
                    ),
                },

                "filters": {
                    "disease_class": (
                        disease_class
                    ),
                    "start_date": (
                        start_date_value
                        if start_date_value
                        else None
                    ),
                    "end_date": (
                        end_date_value
                        if end_date_value
                        else None
                    ),
                },

                "diagnoses": diagnoses,

                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                },
            }
        )

    except Exception:

        db.session.rollback()

        return error_response(
            "EXTENSION_DIAGNOSIS_ERROR",
            (
                "An error occurred while "
                "retrieving regional diagnoses."
            ),
            500,
        )


# =========================================================
# 7.1 DIAGNOSIS DETAILS
# =========================================================

@extension_bp.get(
    "/diagnoses/<int:diagnosis_id>"
)
@jwt_required()
@roles_required("extension_agent")
def get_diagnosis(
    diagnosis_id: int,
):
    """
    Get detailed information about one diagnosis.

    The diagnosis must belong to the authenticated
    extension agent's assigned region/woreda.
    """

    try:

        # =================================================
        # AUTHENTICATED AGENT
        # =================================================

        agent_user, agent_profile = (
            _get_authenticated_agent()
        )

        if (
            agent_user is None
            or agent_profile is None
        ):

            return error_response(
                "EXTENSION_AGENT_NOT_FOUND",
                (
                    "Extension agent profile "
                    "was not found."
                ),
                404,
            )

        # =================================================
        # ASSIGNED DIAGNOSIS
        # =================================================

        diagnosis = _get_assigned_diagnosis(
            diagnosis_id,
            agent_profile,
        )

        if diagnosis is None:

            return error_response(
                "DIAGNOSIS_NOT_FOUND",
                (
                    "Diagnosis was not found "
                    "in your assigned area."
                ),
                404,
            )

        # =================================================
        # RESPONSE
        # =================================================

        return success_response(
            {
                "agent_assignment": {
                    "region": (
                        agent_profile.region
                    ),
                    "woreda": (
                        agent_profile.woreda
                    ),
                },

                "diagnosis": (
                    _serialize_diagnosis(
                        diagnosis
                    )
                ),
            }
        )

    except Exception:

        db.session.rollback()

        return error_response(
            "EXTENSION_DIAGNOSIS_DETAIL_ERROR",
            (
                "An error occurred while "
                "retrieving the diagnosis."
            ),
            500,
        )


# =========================================================
# 7.2 REGIONAL DASHBOARD
# =========================================================

@extension_bp.get("/dashboard")
@jwt_required()
@roles_required("extension_agent")
def get_regional_dashboard():
    """
    Return regional diagnosis statistics.

    Includes:

        - total diagnoses
        - healthy cases
        - diseased cases
        - disease distribution
        - daily diagnosis trends
        - cases by woreda

    All data is restricted to the authenticated
    extension agent's assigned region/woreda.
    """

    try:

        # =================================================
        # AUTHENTICATED AGENT
        # =================================================

        agent_user, agent_profile = (
            _get_authenticated_agent()
        )

        if (
            agent_user is None
            or agent_profile is None
        ):

            return error_response(
                "EXTENSION_AGENT_NOT_FOUND",
                (
                    "Extension agent profile "
                    "was not found."
                ),
                404,
            )

        # =================================================
        # ASSIGNMENT
        # =================================================

        agent_region, agent_woreda = (
            _get_agent_location(
                agent_profile
            )
        )

        if not agent_region:

            return error_response(
                "INVALID_AGENT_ASSIGNMENT",
                (
                    "Extension agent has "
                    "no assigned region."
                ),
                400,
            )

        # =================================================
        # BASE QUERY
        # =================================================

        query = (
            DiagnosisRecord.query
            .join(
                User,
                DiagnosisRecord.user_id
                == User.id,
            )
            .join(
                FarmerProfile,
                FarmerProfile.user_id
                == User.id,
            )
            .filter(
                User.role == "farmer",
                FarmerProfile.region
                == agent_region,
            )
        )

        # =================================================
        # WOREDA RESTRICTION
        # =================================================

        if agent_woreda:

            query = query.filter(
                FarmerProfile.woreda
                == agent_woreda
            )

        # =================================================
        # LOAD DIAGNOSES
        # =================================================

        diagnoses = query.all()

        # =================================================
        # TOTAL
        # =================================================

        total_diagnoses = len(
            diagnoses
        )

        # =================================================
        # HEALTHY / DISEASED
        # =================================================

        healthy_count = 0
        diseased_count = 0

        disease_distribution = {}

        for diagnosis in diagnoses:

            disease = str(
                diagnosis.disease_class
                or ""
            ).strip()

            normalized_disease = (
                disease.lower()
            )

            if normalized_disease == "healthy":

                healthy_count += 1

            else:

                diseased_count += 1

                if disease:

                    disease_distribution[
                        disease
                    ] = (
                        disease_distribution.get(
                            disease,
                            0,
                        )
                        + 1
                    )

        # =================================================
        # DISEASE DISTRIBUTION
        # =================================================

        disease_distribution_list = [
            {
                "disease_class": disease,
                "count": count,
            }

            for disease, count
            in sorted(
                disease_distribution.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        # =================================================
        # DAILY TRENDS
        # =================================================

        trend_map = {}

        for diagnosis in diagnoses:

            if diagnosis.created_at is None:
                continue

            date_key = (
                diagnosis.created_at
                .date()
                .isoformat()
            )

            trend_map[date_key] = (
                trend_map.get(
                    date_key,
                    0,
                )
                + 1
            )

        trends = [
            {
                "date": date,
                "count": count,
            }

            for date, count
            in sorted(
                trend_map.items()
            )
        ]

        # =================================================
        # CASES BY WOREDA
        # =================================================

        woreda_map = {}

        for diagnosis in diagnoses:

            farmer = diagnosis.user

            if farmer is None:
                continue

            farmer_profile = (
                farmer.farmer_profile
            )

            if farmer_profile is None:
                continue

            woreda = (
                farmer_profile.woreda
                or "Unknown"
            ).strip()

            woreda_map[woreda] = (
                woreda_map.get(
                    woreda,
                    0,
                )
                + 1
            )

        cases_by_woreda = [
            {
                "woreda": woreda,
                "count": count,
            }

            for woreda, count
            in sorted(
                woreda_map.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        # =================================================
        # RESPONSE
        # =================================================

        return success_response(
            {
                "agent_assignment": {
                    "region": agent_region,
                    "woreda": (
                        agent_woreda
                        if agent_woreda
                        else None
                    ),
                },

                "summary": {
                    "total_diagnoses": (
                        total_diagnoses
                    ),

                    "healthy_cases": (
                        healthy_count
                    ),

                    "diseased_cases": (
                        diseased_count
                    ),
                },

                "disease_distribution": (
                    disease_distribution_list
                ),

                "trends": trends,

                "cases_by_woreda": (
                    cases_by_woreda
                ),
            }
        )

    except Exception:

        db.session.rollback()

        return error_response(
            "EXTENSION_DASHBOARD_ERROR",
            (
                "An error occurred while "
                "generating the regional dashboard."
            ),
            500,
        )


# =========================================================
# 7.3 GEO-DISEASE MONITORING
# =========================================================

@extension_bp.get("/geo-diseases")
@jwt_required()
@roles_required("extension_agent")
def get_geo_diseases():
    """
    Return diagnosis cases with farmer coordinates.

    Only cases belonging to the authenticated
    extension agent's assigned area are returned.

    Cases without latitude/longitude are excluded.

    Supported filters:

        disease_class
        start_date
        end_date
    """

    try:

        # =================================================
        # AUTHENTICATED AGENT
        # =================================================

        agent_user, agent_profile = (
            _get_authenticated_agent()
        )

        if (
            agent_user is None
            or agent_profile is None
        ):

            return error_response(
                "EXTENSION_AGENT_NOT_FOUND",
                (
                    "Extension agent profile "
                    "was not found."
                ),
                404,
            )

        # =================================================
        # ASSIGNMENT
        # =================================================

        agent_region, agent_woreda = (
            _get_agent_location(
                agent_profile
            )
        )

        if not agent_region:

            return error_response(
                "INVALID_AGENT_ASSIGNMENT",
                (
                    "Extension agent has "
                    "no assigned region."
                ),
                400,
            )

        # =================================================
        # DISEASE FILTER
        # =================================================

        disease_class = request.args.get(
            "disease_class",
            default=None,
            type=str,
        )

        if disease_class is not None:

            disease_class = (
                disease_class.strip()
            )

            if not disease_class:
                disease_class = None

        # =================================================
        # DATE FILTERS
        # =================================================

        start_date_value = request.args.get(
            "start_date",
            default=None,
            type=str,
        )

        end_date_value = request.args.get(
            "end_date",
            default=None,
            type=str,
        )

        start_datetime = None
        end_datetime = None

        # -------------------------------------------------
        # START DATE
        # -------------------------------------------------

        if start_date_value:

            start_date_value = (
                start_date_value.strip()
            )

            start_datetime = _parse_date(
                start_date_value
            )

            if start_datetime is None:

                return error_response(
                    "INVALID_START_DATE",
                    (
                        "start_date must use "
                        "YYYY-MM-DD format."
                    ),
                    400,
                )

        # -------------------------------------------------
        # END DATE
        # -------------------------------------------------

        if end_date_value:

            end_date_value = (
                end_date_value.strip()
            )

            parsed_end_date = _parse_date(
                end_date_value
            )

            if parsed_end_date is None:

                return error_response(
                    "INVALID_END_DATE",
                    (
                        "end_date must use "
                        "YYYY-MM-DD format."
                    ),
                    400,
                )

            # Inclusive end date.
            end_datetime = (
                parsed_end_date
                + timedelta(days=1)
            )

        # =================================================
        # DATE RANGE VALIDATION
        # =================================================

        if (
            start_datetime is not None
            and end_datetime is not None
            and start_datetime >= end_datetime
        ):

            return error_response(
                "INVALID_DATE_RANGE",
                (
                    "start_date must be earlier "
                    "than or equal to end_date."
                ),
                400,
            )

        # =================================================
        # BASE QUERY
        # =================================================

        query = (
            DiagnosisRecord.query
            .join(
                User,
                DiagnosisRecord.user_id
                == User.id,
            )
            .join(
                FarmerProfile,
                FarmerProfile.user_id
                == User.id,
            )
            .filter(
                User.role == "farmer",
                FarmerProfile.region
                == agent_region,
            )
        )

        # =================================================
        # WOREDA RESTRICTION
        # =================================================

        if agent_woreda:

            query = query.filter(
                FarmerProfile.woreda
                == agent_woreda
            )

        # =================================================
        # DISEASE FILTER
        # =================================================

        if disease_class:

            query = query.filter(
                DiagnosisRecord.disease_class
                == disease_class
            )

        # =================================================
        # START DATE
        # =================================================

        if start_datetime is not None:

            query = query.filter(
                DiagnosisRecord.created_at
                >= start_datetime
            )

        # =================================================
        # END DATE
        # =================================================

        if end_datetime is not None:

            query = query.filter(
                DiagnosisRecord.created_at
                < end_datetime
            )

        # =================================================
        # ORDER
        # =================================================

        query = query.order_by(
            DiagnosisRecord.created_at.desc()
        )

        diagnoses = query.all()

        # =================================================
        # GEO CASES
        # =================================================

        cases = []

        for diagnosis in diagnoses:

            farmer = diagnosis.user

            if farmer is None:
                continue

            farmer_profile = (
                farmer.farmer_profile
            )

            if farmer_profile is None:
                continue

            # Exclude cases without coordinates.
            if (
                farmer_profile.latitude
                is None
                or
                farmer_profile.longitude
                is None
            ):
                continue

            cases.append(
                {
                    "diagnosis_id": (
                        diagnosis.id
                    ),

                    "disease_class": (
                        diagnosis.disease_class
                    ),

                    "confidence": (
                        diagnosis.confidence
                    ),

                    "latitude": float(
                        farmer_profile.latitude
                    ),

                    "longitude": float(
                        farmer_profile.longitude
                    ),

                    "farmer": {
                        "id": farmer.id,

                        "full_name": (
                            farmer.full_name
                        ),
                    },

                    "location": {
                        "region": (
                            farmer_profile.region
                        ),

                        "woreda": (
                            farmer_profile.woreda
                        ),

                        "kebele": (
                            farmer_profile.kebele
                        ),
                    },

                    "created_at": (
                        diagnosis.created_at.isoformat()
                        if diagnosis.created_at
                        else None
                    ),
                }
            )

        # =================================================
        # RESPONSE
        # =================================================

        return success_response(
            {
                "agent_assignment": {
                    "region": agent_region,
                    "woreda": (
                        agent_woreda
                        if agent_woreda
                        else None
                    ),
                },

                "filters": {
                    "disease_class": (
                        disease_class
                    ),

                    "start_date": (
                        start_date_value
                        if start_date_value
                        else None
                    ),

                    "end_date": (
                        end_date_value
                        if end_date_value
                        else None
                    ),
                },

                "total_cases": len(
                    cases
                ),

                "cases": cases,
            }
        )

    except Exception:

        db.session.rollback()

        return error_response(
            "EXTENSION_GEO_ERROR",
            (
                "An error occurred while "
                "retrieving geographic "
                "disease data."
            ),
            500,
        )
