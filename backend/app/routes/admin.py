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

from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from backend.app.extensions import db
from backend.app.models.administrative_division import (
    GeographyRegion,
    GeographyZone,
    GeographyWoreda,
)
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.user import User

from backend.app.routes.auth import roles_required

from backend.app.services.admin_service import (
    AdminService,
    InvalidDateFilterError,
)

from backend.app.services.auth_service import (
    AuthServiceError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)

from backend.app.services.extension_agent_service import (
    ExtensionAgentAlreadyExistsError,
    ExtensionAgentService,
)
from backend.app.services.registration_otp_service import (
    RegistrationOTPService,
    RegistrationOTPError,
    RegistrationOTPCooldownError,
    RegistrationOTPDeliveryError,
    RegistrationOTPValidationError,
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

def _legacy_create_extension_agent():
    """
    Create a new extension-agent account and professional
    extension-agent profile.
    """

    payload = request.get_json(silent=True) or {}

    try:

        user = ExtensionAgentService.create_agent(
            phone_number=payload.get("phone_number"),
            full_name=payload.get("full_name"),
            password=payload.get("password"),
            region=payload.get("region"),
            woreda=payload.get("woreda"),
            specialization=payload.get("specialization"),
            certification_number=payload.get("certification_number"),
            preferred_language=payload.get("preferred_language", "en"),
        )

        profile = ExtensionAgentService.get_agent_by_user_id(user.id)
        agent = ExtensionAgentService.agent_to_dict(profile) if profile else None

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

    except ExtensionAgentAlreadyExistsError as exc:

        return error_response(
            "EXTENSION_AGENT_ALREADY_EXISTS",
            str(exc),
            409,
        )

    except (AuthServiceError, ValueError) as exc:

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


@admin_bp.post("/extension-agents")
@jwt_required()
@roles_required("admin")
def create_extension_agent():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response(
            "INVALID_REQUEST",
            "Request body must contain valid JSON.",
            400,
        )

    try:
        admin_id = int(get_jwt_identity())
        user = ExtensionAgentService.create_pending_agent(
            phone_number=payload.get("phone_number"),
            full_name=payload.get("full_name"),
            email=payload.get("email"),
            employee_id=payload.get("employee_id"),
            organization=payload.get("organization"),
            region_id=payload.get("region_id"),
            zone_id=payload.get("zone_id"),
            woreda_id=payload.get("woreda_id"),
            verification_method=payload.get("verification_method"),
            professional_info_verified=payload.get(
                "professional_info_verified"
            ),
            verified_by_admin_id=admin_id,
            specialization=payload.get("specialization"),
            certification_number=payload.get("certification_number"),
            preferred_language=payload.get("preferred_language", "en"),
        )
    except UserAlreadyExistsError as exc:
        return error_response("USER_ALREADY_EXISTS", str(exc), 409)
    except ExtensionAgentAlreadyExistsError as exc:
        return error_response("EXTENSION_AGENT_ALREADY_EXISTS", str(exc), 409)
    except (AuthServiceError, ValueError, TypeError) as exc:
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to provision extension agent.")
        return error_response(
            "EXTENSION_AGENT_CREATE_ERROR",
            "Unable to create extension agent.",
            500,
        )

    try:
        delivery = RegistrationOTPService.send_extension_agent_activation_code(
            user.id
        )
    except RegistrationOTPCooldownError as exc:
        return error_response(
            "EXTENSION_AGENT_CREATED_DELIVERY_FAILED",
            f"Agent account is pending activation, but code delivery was rate limited: {exc}",
            503,
        )
    except (RegistrationOTPDeliveryError, RegistrationOTPError) as exc:
        current_app.logger.warning(
            "Extension-agent account %s was created, but activation delivery failed: %s",
            user.id,
            exc,
        )
        return error_response(
            "EXTENSION_AGENT_CREATED_DELIVERY_FAILED",
            "Agent account is pending activation, but the code could not be delivered. Use the resend action.",
            503,
        )

    profile = ExtensionAgentService.get_agent_by_user_id(user.id)
    agent = ExtensionAgentService.agent_to_dict(profile) if profile else None
    if agent is None:
        current_app.logger.error(
            "Created extension-agent account %s has no profile.",
            user.id,
        )
        return error_response(
            "EXTENSION_AGENT_CREATE_ERROR",
            "Unable to load the newly created extension-agent profile.",
            500,
        )
    agent["activation_delivery"] = {
        "status": "submitted",
        "expires_in_seconds": delivery["expires_in_seconds"],
        "resend_after_seconds": delivery["resend_after_seconds"],
    }
    return success_response(agent, 201)


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
        account_status = request.args.get("account_status", "").strip() or None
        if account_status not in {
            None,
            "pending_activation",
            "active",
            "suspended",
        }:
            return error_response(
                "INVALID_ACCOUNT_STATUS_FILTER",
                "account_status must be pending_activation, active, or suspended.",
                400,
            )
        verified_value = request.args.get("professional_info_verified")
        professional_info_verified = None
        if verified_value is not None:
            if verified_value not in {"true", "false"}:
                return error_response(
                    "INVALID_VERIFICATION_FILTER",
                    "professional_info_verified must be true or false.",
                    400,
                )
            professional_info_verified = verified_value == "true"

        agents = (
            AdminService
            .get_all_extension_agents(
                search=search,
                region=region,
                woreda=woreda,
                account_status=account_status,
                professional_info_verified=professional_info_verified,
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


@admin_bp.get("/extension-agent-geography")
@jwt_required()
@roles_required("admin")
def get_extension_agent_geography():
    level = request.args.get("level", "").strip().lower()
    parent_id = request.args.get("parent_id", "").strip()
    if level not in {"regions", "zones", "woredas"}:
        return error_response(
            "INVALID_GEOGRAPHY_LEVEL",
            "level must be regions, zones, or woredas.",
            400,
        )
    if level == "regions":
        rows = GeographyRegion.query.order_by(GeographyRegion.name_en).all()
        data = [
            {"id": row.id, "name_en": row.name_en, "name_local": row.name_local}
            for row in rows
        ]
    elif level == "zones":
        if not parent_id:
            return error_response(
                "MISSING_GEOGRAPHY_PARENT",
                "parent_id is required for zones.",
                400,
            )
        rows = (
            GeographyZone.query
            .filter_by(region_id=parent_id)
            .order_by(GeographyZone.name_en)
            .all()
        )
        data = [
            {
                "id": row.id,
                "name_en": row.name_en,
                "name_local": row.name_local,
                "parent_id": row.region_id,
            }
            for row in rows
        ]
    else:
        if not parent_id:
            return error_response(
                "MISSING_GEOGRAPHY_PARENT",
                "parent_id is required for woredas.",
                400,
            )
        rows = (
            GeographyWoreda.query
            .filter_by(zone_id=parent_id)
            .order_by(GeographyWoreda.name_en)
            .all()
        )
        data = [
            {
                "id": row.id,
                "name_en": row.name_en,
                "name_local": row.name_local,
                "parent_id": row.zone_id,
            }
            for row in rows
        ]
    return success_response(data)


@admin_bp.post("/extension-agents/<int:user_id>/activation-code")
@jwt_required()
@roles_required("admin")
def resend_extension_agent_activation(user_id: int):
    profile = ExtensionAgentService.get_agent_by_user_id(user_id)
    if profile is None:
        return error_response("EXTENSION_AGENT_NOT_FOUND", "Extension agent not found.", 404)
    try:
        result = RegistrationOTPService.send_extension_agent_activation_code(
            user_id
        )
        return success_response(
            {
                "message": "Activation code submitted for delivery.",
                "expires_in_seconds": result["expires_in_seconds"],
                "resend_after_seconds": result["resend_after_seconds"],
            }
        )
    except RegistrationOTPCooldownError as exc:
        return error_response("EXTENSION_AGENT_ACTIVATION_COOLDOWN", str(exc), 429)
    except RegistrationOTPValidationError as exc:
        return error_response("EXTENSION_AGENT_ACTIVATION_INVALID", str(exc), 400)
    except RegistrationOTPDeliveryError:
        current_app.logger.warning(
            "Could not resend activation code for extension agent %s.",
            user_id,
        )
        return error_response(
            "EXTENSION_AGENT_ACTIVATION_DELIVERY_FAILED",
            "Unable to deliver the activation code.",
            503,
        )
    except RegistrationOTPError:
        current_app.logger.warning(
            "Could not prepare activation code for extension agent %s.",
            user_id,
        )
        return error_response(
            "EXTENSION_AGENT_ACTIVATION_ERROR",
            "Unable to prepare the activation code.",
            500,
        )


@admin_bp.patch("/extension-agents/<int:user_id>/status")
@jwt_required()
@roles_required("admin")
def update_extension_agent_status(user_id: int):
    payload = request.get_json(silent=True)
    status = payload.get("account_status") if isinstance(payload, dict) else None
    try:
        result = AdminService.set_extension_agent_status(
            user_id,
            account_status=status,
        )
        return success_response(result)
    except ValueError as exc:
        return error_response("INVALID_ACCOUNT_STATUS", str(exc), 400)
    except Exception as exc:
        if "not found" in str(exc).lower():
            return error_response("EXTENSION_AGENT_NOT_FOUND", str(exc), 404)
        if "status" in str(exc).lower() or "reactivated" in str(exc).lower():
            return error_response("INVALID_ACCOUNT_STATUS", str(exc), 400)
        current_app.logger.exception(
            "Failed to update extension-agent status for %s.",
            user_id,
        )
        return error_response(
            "EXTENSION_AGENT_STATUS_UPDATE_ERROR",
            "Unable to update extension-agent status.",
            500,
        )


@admin_bp.patch("/extension-agents/<int:user_id>/assignment")
@jwt_required()
@roles_required("admin")
def transfer_extension_agent(user_id: int):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response(
            "INVALID_REQUEST",
            "Request body must contain valid JSON.",
            400,
        )
    try:
        admin_id = int(get_jwt_identity())
        result = AdminService.transfer_extension_agent(
            user_id=user_id,
            region_id=payload.get("region_id"),
            zone_id=payload.get("zone_id"),
            woreda_id=payload.get("woreda_id"),
            admin_id=admin_id,
        )
        return success_response(result)
    except ValueError as exc:
        return error_response("INVALID_ASSIGNMENT", str(exc), 400)
    except Exception as exc:
        if "not found" in str(exc).lower():
            return error_response("EXTENSION_AGENT_NOT_FOUND", str(exc), 404)
        current_app.logger.exception(
            "Failed to transfer extension agent %s.",
            user_id,
        )
        return error_response(
            "EXTENSION_AGENT_TRANSFER_ERROR",
            "Unable to transfer extension agent.",
            500,
        )


@admin_bp.get("/extension-agents/<int:user_id>/assignment-history")
@jwt_required()
@roles_required("admin")
def get_extension_agent_assignment_history(user_id: int):
    profile = ExtensionAgentService.get_agent_by_user_id(user_id)
    if profile is None:
        return error_response("EXTENSION_AGENT_NOT_FOUND", "Extension agent not found.", 404)
    return success_response(
        AdminService.get_extension_agent_assignment_history(user_id)
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

        account = AdminService.get_user_by_id(user_id)
        if account.role == "extension_agent":
            user = AdminService.set_extension_agent_status(
                user_id,
                account_status="active" if is_active else "suspended",
            )
        else:
            user = AdminService.set_user_status(
                user_id=user_id,
                is_active=is_active,
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
