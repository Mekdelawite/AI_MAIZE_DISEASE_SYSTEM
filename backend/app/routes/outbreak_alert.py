"""
=========================================================
Outbreak Alert Routes
=========================================================

API endpoints for managing maize disease outbreak alerts.

Responsibilities:
- Admin manual outbreak alerts
- Automatic outbreak evaluation
- Outbreak alert history
- Individual outbreak alert details

Business logic is handled by OutbreakAlertService.
=========================================================
"""

from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from backend.app.extensions import db
from backend.app.models.outbreak_alert import OutbreakAlert
from backend.app.services.auth_service import AuthService
from backend.app.services.outbreak_alert_service import OutbreakAlertService


outbreak_alert_bp = Blueprint(
    "outbreak_alert",
    __name__,
    url_prefix="/api/outbreak-alerts",
)


# =========================================================
# Helpers
# =========================================================

def success_response(data=None, message="Success"):
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(message, status_code=400):
    return {
        "success": False,
        "message": message,
        "data": None,
    }, status_code


def get_authenticated_user():
    """
    Get the currently authenticated active user.
    """

    identity = get_jwt_identity()

    if identity is None:
        return None

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    user = AuthService.get_user_by_id(user_id)

    if user is None or not user.is_active:
        return None

    return user


def admin_required():
    """
    Check whether the current JWT belongs to an admin.
    """

    claims = get_jwt()

    return claims.get("role") == "admin"


# =========================================================
# Manual Outbreak Alert
# =========================================================

@outbreak_alert_bp.route("/manual", methods=["POST"])
@jwt_required()
def create_manual_outbreak_alert():
    """
    Create and send a manual outbreak alert.

    Admin provides:
        disease_class
        region
        optional woreda
        optional kebele
        optional risk_level
        optional risk_score
    """

    user = get_authenticated_user()

    if user is None:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    if not admin_required():
        return error_response(
            "Admin access required.",
            403,
        )

    data = request.get_json(silent=True) or {}

    disease_class = str(data.get("disease_class", "")).strip()
    region = str(data.get("region", "")).strip()

    woreda = data.get("woreda")
    kebele = data.get("kebele")

    if woreda is not None:
        woreda = str(woreda).strip() or None

    if kebele is not None:
        kebele = str(kebele).strip() or None

    risk_level = str(
        data.get("risk_level", "high")
    ).strip().lower()

    risk_score = data.get("risk_score", 0.0)

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if not disease_class:
        return error_response(
            "disease_class is required."
        )

    if not region:
        return error_response(
            "region is required."
        )

    allowed_risk_levels = {
        "low",
        "moderate",
        "high",
        "critical",
    }

    if risk_level not in allowed_risk_levels:
        return error_response(
            "risk_level must be one of: low, moderate, high, critical."
        )

    try:
        risk_score = float(risk_score)
    except (TypeError, ValueError):
        return error_response(
            "risk_score must be a number."
        )

    if risk_score < 0 or risk_score > 100:
        return error_response(
            "risk_score must be between 0 and 100."
        )

    # -----------------------------------------------------
    # Process alert
    # -----------------------------------------------------

    try:
        service = OutbreakAlertService()

        result = service.process_manual_alert(
            disease_class=disease_class,
            region=region,
            woreda=woreda,
            kebele=kebele,
            risk_level=risk_level,
            risk_score=risk_score,
            created_by=user.id,
        )

        return success_response(
            data=result,
            message="Manual outbreak alert processed successfully.",
        )

    except Exception as exc:
        db.session.rollback()

        return error_response(
            f"Failed to process outbreak alert: {str(exc)}",
            500,
        )


# =========================================================
# Automatic Outbreak Evaluation
# =========================================================

@outbreak_alert_bp.route("/automatic", methods=["POST"])
@jwt_required()
def process_automatic_outbreak_alert():
    """
    Run automatic outbreak detection for an area.

    Admin can use this endpoint to manually trigger an
    automatic outbreak evaluation.

    Required:
        disease_class
        region

    Optional:
        woreda
        kebele
        analysis_period_days
        recent_period_days
        cooldown_hours
    """

    user = get_authenticated_user()

    if user is None:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    if not admin_required():
        return error_response(
            "Admin access required.",
            403,
        )

    data = request.get_json(silent=True) or {}

    disease_class = str(data.get("disease_class", "")).strip()
    region = str(data.get("region", "")).strip()

    woreda = data.get("woreda")
    kebele = data.get("kebele")

    if woreda is not None:
        woreda = str(woreda).strip() or None

    if kebele is not None:
        kebele = str(kebele).strip() or None

    if not disease_class:
        return error_response(
            "disease_class is required."
        )

    if not region:
        return error_response(
            "region is required."
        )

    # -----------------------------------------------------
    # Optional numeric parameters
    # -----------------------------------------------------

    analysis_period_days = data.get(
        "analysis_period_days",
        7,
    )

    recent_period_days = data.get(
        "recent_period_days",
        2,
    )

    cooldown_hours = data.get(
        "cooldown_hours",
        24,
    )

    try:
        analysis_period_days = int(
            analysis_period_days
        )
        recent_period_days = int(
            recent_period_days
        )
        cooldown_hours = int(
            cooldown_hours
        )
    except (TypeError, ValueError):
        return error_response(
            "Analysis periods and cooldown_hours must be integers."
        )

    if analysis_period_days <= 0:
        return error_response(
            "analysis_period_days must be greater than 0."
        )

    if recent_period_days <= 0:
        return error_response(
            "recent_period_days must be greater than 0."
        )

    if recent_period_days > analysis_period_days:
        return error_response(
            "recent_period_days cannot exceed analysis_period_days."
        )

    if cooldown_hours < 0:
        return error_response(
            "cooldown_hours cannot be negative."
        )

    # -----------------------------------------------------
    # Process automatic detection
    # -----------------------------------------------------

    try:
        service = OutbreakAlertService()

        result = service.process_automatic_alert(
            disease_class=disease_class,
            region=region,
            woreda=woreda,
            kebele=kebele,
            analysis_period_days=analysis_period_days,
            recent_period_days=recent_period_days,
            cooldown_hours=cooldown_hours,
        )

        return success_response(
            data=result,
            message="Automatic outbreak evaluation completed.",
        )

    except Exception as exc:
        db.session.rollback()

        return error_response(
            f"Failed to process automatic outbreak evaluation: {str(exc)}",
            500,
        )


# =========================================================
# Outbreak Alert History
# =========================================================

@outbreak_alert_bp.route("", methods=["GET"])
@jwt_required()
def get_outbreak_alerts():
    """
    Get outbreak alert history.

    Admin only.

    Optional query parameters:

        disease_class
        region
        woreda
        kebele
        risk_level
        trigger_type
        status
    """

    user = get_authenticated_user()

    if user is None:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    if not admin_required():
        return error_response(
            "Admin access required.",
            403,
        )

    query = OutbreakAlert.query

    disease_class = request.args.get("disease_class", "").strip()

    region = request.args.get("region")
    woreda = request.args.get("woreda")
    kebele = request.args.get("kebele")
    risk_level = request.args.get("risk_level")
    trigger_type = request.args.get("trigger_type")
    status = request.args.get("status")

    if disease_class:
        query = query.filter(
            OutbreakAlert.disease_class.ilike(f"%{disease_class}%")
        )

    if region:
        query = query.filter(
            OutbreakAlert.region == region
        )

    if woreda:
        query = query.filter(
            OutbreakAlert.woreda == woreda
        )

    if kebele:
        query = query.filter(
            OutbreakAlert.kebele == kebele
        )

    if risk_level:
        query = query.filter(
            OutbreakAlert.risk_level == risk_level
        )

    if trigger_type:
        query = query.filter(
            OutbreakAlert.trigger_type == trigger_type
        )

    if status:
        query = query.filter(
            OutbreakAlert.status == status
        )

    alerts = (
        query
        .order_by(OutbreakAlert.created_at.desc())
        .all()
    )

    service = OutbreakAlertService()

    result = [
        service.serialize_alert(alert)
        for alert in alerts
    ]

    return success_response(
        data=result,
        message="Outbreak alerts retrieved successfully.",
    )


# =========================================================
# Single Outbreak Alert
# =========================================================

@outbreak_alert_bp.route("/<int:alert_id>", methods=["GET"])
@jwt_required()
def get_outbreak_alert(alert_id):
    """
    Get one outbreak alert by ID.

    Admin only.
    """

    user = get_authenticated_user()

    if user is None:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    if not admin_required():
        return error_response(
            "Admin access required.",
            403,
        )

    alert = OutbreakAlert.query.get(alert_id)

    if alert is None:
        return error_response(
            "Outbreak alert not found.",
            404,
        )

    service = OutbreakAlertService()

    return success_response(
        data=service.serialize_alert(alert),
        message="Outbreak alert retrieved successfully.",
    )
