"""
=========================================================
Admin Routes
=========================================================

Administrator-only API endpoints for the AI Maize Disease
Detection System.

Responsibilities:
    - Extension agent management
    - User management
    - Farmer management
    - Diagnosis monitoring
    - Extension comment monitoring
    - Global dashboard statistics
    - Regional statistics
    - Geo-disease map data

Authorization:
    All endpoints require:
        1. Valid JWT
        2. admin role

The route layer delegates business logic to AdminService
and other existing services.

No duplicate business logic is implemented here.
=========================================================
"""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    request,
)

from flask_jwt_extended import jwt_required

from backend.app.routes.auth import roles_required

from backend.app.services.admin_service import (
    AdminService,
    InvalidDateFilterError,
)

from backend.app.services.auth_service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)

from backend.app.services.extension_agent_service import (
    ExtensionAgentService,
)


# =========================================================
# BLUEPRINT
# =========================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin",
)


# =========================================================
# RESPONSE HELPERS
# =========================================================

def success_response(
    data,
    status_code=200,
):
    """
    Return a standard successful API response.
    """

    return {
        "success": True,
        "data": data,
    }, status_code


def error_response(
    code,
    message,
    status_code,
):
    """
    Return a standard API error response.
    """

    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }, status_code


# =========================================================
# EXTENSION AGENT MANAGEMENT
# =========================================================

@admin_bp.post("/extension-agents")
@jwt_required()
@roles_required("admin")
def create_extension_agent():
    """
    Create a new extension-agent account and professional
    extension-agent profile.
    """

    payload = request.get_json(silent=True) or {}

    try:

        agent = (
            ExtensionAgentService
            .create_extension_agent(
                payload
            )
        )

        return success_response(
            agent,
            201,
        )

    except UserAlreadyExistsError as exc:

        return error_response(
            "USER_ALREADY_EXISTS",
            str(exc),
            409,
        )

    except ValueError as exc:

        return error_response(
            "VALIDATION_ERROR",
            str(exc),
            400,
        )

    except Exception:

        current_app.logger.exception(
            "Failed to create extension agent."
        )

        return error_response(
            "EXTENSION_AGENT_CREATE_ERROR",
            "Unable to create extension agent.",
            500,
        )


@admin_bp.get("/extension-agents")
@jwt_required()
@roles_required("admin")
def get_extension_agents():
    """
    Return all extension agents.
    """

    try:

        search = request.args.get("search", "").strip() or None
        region = request.args.get("region", "").strip() or None
        woreda = request.args.get("woreda", "").strip() or None

        agents = (
            AdminService
            .get_all_extension_agents(
                search=search,
                region=region,
                woreda=woreda,
            )
        )

        return success_response(agents)

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve extension agents."
        )

        return error_response(
            "EXTENSION_AGENT_LIST_ERROR",
            "Unable to retrieve extension agents.",
            500,
        )


# =========================================================
# USER MANAGEMENT
# =========================================================

@admin_bp.get("/users")
@jwt_required()
@roles_required("admin")
def get_users():
    """
    Return users filtered by optional role, region, kebele, and text search.
    """

    role = request.args.get("role", "").strip().lower()
    region = request.args.get("region", "").strip()
    kebele = request.args.get("kebele", "").strip()
    search = request.args.get("search", "").strip()

    if role and role not in {"farmer", "extension_agent", "admin"}:
        return error_response(
            "INVALID_ROLE_FILTER",
            "Role must be farmer, extension_agent, or admin.",
            400,
        )

    try:

        users = (
            AdminService
            .get_all_users(
                role=role or None,
                region=region or None,
                kebele=kebele or None,
                search=search or None,
            )
        )

        return success_response(users)

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve users."
        )

        return error_response(
            "USER_LIST_ERROR",
            "Unable to retrieve users.",
            500,
        )


@admin_bp.patch("/users/<int:user_id>/status")
@jwt_required()
@roles_required("admin")
def update_user_status(
    user_id: int,
):
    """
    Activate or deactivate a user.

    Expected JSON:

    {
        "is_active": true
    }
    """

    payload = request.get_json(
        silent=True
    ) or {}

    if "is_active" not in payload:

        return error_response(
            "MISSING_IS_ACTIVE",
            "is_active is required.",
            400,
        )

    is_active = payload["is_active"]

    if not isinstance(
        is_active,
        bool,
    ):

        return error_response(
            "INVALID_IS_ACTIVE",
            "is_active must be a boolean.",
            400,
        )

    try:

        # AdminService already returns the
        # serialized user dictionary.
        user = (
            AdminService
            .set_user_status(
                user_id=user_id,
                is_active=is_active,
            )
        )

        return success_response(user)

    except Exception as exc:

        message = str(exc)

        if "not found" in message.lower():

            return error_response(
                "USER_NOT_FOUND",
                message,
                404,
            )

        current_app.logger.exception(
            "Failed to update user status."
        )

        return error_response(
            "USER_STATUS_UPDATE_ERROR",
            "Unable to update user status.",
            500,
        )


# =========================================================
# FARMER MANAGEMENT
# =========================================================

@admin_bp.get("/farmers")
@jwt_required()
@roles_required("admin")
def get_farmers():
    """
    Return all farmers together with their farmer
    profiles, including regional and coordinate data.
    """

    try:

        search = request.args.get("search", "").strip() or None
        region = request.args.get("region", "").strip() or None
        woreda = request.args.get("woreda", "").strip() or None
        kebele = request.args.get("kebele", "").strip() or None

        farmers = (
            AdminService
            .get_all_farmers(
                search=search,
                region=region,
                woreda=woreda,
                kebele=kebele,
            )
        )

        return success_response(farmers)

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve farmers."
        )

        return error_response(
            "FARMER_LIST_ERROR",
            "Unable to retrieve farmers.",
            500,
        )


# =========================================================
# DIAGNOSIS MONITORING
# =========================================================

@admin_bp.get("/diagnoses")
@jwt_required()
@roles_required("admin")
def get_diagnoses():
    """
    Return all diagnosis records.
    """

    try:

        diagnoses = (
            AdminService
            .get_all_diagnoses()
        )

        return success_response(diagnoses)

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve diagnoses."
        )

        return error_response(
            "DIAGNOSIS_LIST_ERROR",
            "Unable to retrieve diagnoses.",
            500,
        )


# =========================================================
# EXTENSION COMMENT MONITORING
# =========================================================

@admin_bp.get("/comments")
@jwt_required()
@roles_required("admin")
def get_comments():
    """
    Return all extension comments.

    This endpoint is retained for existing
    administrative functionality.
    """

    try:

        comments = (
            AdminService
            .get_all_extension_comments()
        )

        return success_response(comments)

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve extension comments."
        )

        return error_response(
            "COMMENT_LIST_ERROR",
            "Unable to retrieve extension comments.",
            500,
        )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@admin_bp.get("/dashboard")
@jwt_required()
@roles_required("admin")
def get_dashboard():
    """
    Return the complete administrator dashboard.

    The dashboard includes:

        - User statistics
        - Diagnosis statistics
        - Healthy/diseased summary
        - Disease distribution
        - Advisory count
        - Extension comment count
        - Regional statistics
        - Geo-disease statistics
        - Recent diagnoses
        - Recent users
    """

    try:

        dashboard = (
            AdminService
            .get_dashboard_statistics()
        )

        return success_response(
            dashboard
        )

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve admin dashboard."
        )

        return error_response(
            "DASHBOARD_ERROR",
            "Unable to retrieve admin dashboard statistics.",
            500,
        )


# =========================================================
# REGIONAL STATISTICS
# =========================================================

@admin_bp.get("/regional-statistics")
@jwt_required()
@roles_required("admin")
def get_regional_statistics():
    """
    Return global regional disease statistics.

    Optional query parameters:

        disease_class
            Example:
                Blight

        start_date
            Format:
                YYYY-MM-DD

        end_date
            Format:
                YYYY-MM-DD
    """

    disease_class = request.args.get(
        "disease_class"
    )

    start_date = request.args.get(
        "start_date"
    )

    end_date = request.args.get(
        "end_date"
    )
    try:

        statistics = (
            AdminService
            .get_regional_statistics(
                disease_class=disease_class,
                start_date=start_date,
                end_date=end_date,
            )
        )

        return success_response(
            statistics
        )

    except InvalidDateFilterError as exc:

        return error_response(
            "INVALID_DATE_FILTER",
            str(exc),
            400,
        )

    except ValueError as exc:

        return error_response(
            "INVALID_FILTER",
            str(exc),
            400,
        )

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve regional statistics."
        )

        return error_response(
            "REGIONAL_STATISTICS_ERROR",
            "Unable to retrieve regional statistics.",
            500,
        )


# =========================================================
# GEO-DISEASE MAP
# =========================================================

@admin_bp.get("/geo-diseases")
@jwt_required()
@roles_required("admin")
def get_geo_diseases():
    """
    Return diagnosis cases that contain valid farmer
    latitude and longitude coordinates.

    Optional query parameters:

        disease_class
            Example:
                Blight

        start_date
            Format:
                YYYY-MM-DD

        end_date
            Format:
                YYYY-MM-DD

    Cases without coordinates are intentionally excluded.
    """

    disease_class = request.args.get(
        "disease_class"
    )

    start_date = request.args.get(
        "start_date"
    )

    end_date = request.args.get(
        "end_date"
    )
    include_coverage = request.args.get(
        "include_coverage", "false"
    ).strip().lower() in {"1", "true", "yes"}

    try:

        cases = (
            AdminService
            .get_geo_disease_cases(
                disease_class=disease_class,
                start_date=start_date,
                end_date=end_date,
                include_coverage=include_coverage,
            )
        )

        return success_response(cases)

    except InvalidDateFilterError as exc:

        return error_response(
            "INVALID_DATE_FILTER",
            str(exc),
            400,
        )

    except ValueError as exc:

        return error_response(
            "INVALID_FILTER",
            str(exc),
            400,
        )

    except Exception:

        current_app.logger.exception(
            "Failed to retrieve geo-disease cases."
        )

        return error_response(
            "GEO_DISEASE_ERROR",
            "Unable to retrieve geo-disease cases.",
            500,
        )
