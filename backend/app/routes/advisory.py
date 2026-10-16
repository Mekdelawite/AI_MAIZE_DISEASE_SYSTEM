"""
=========================================================
Advisory API Routes
=========================================================

Flask API routes for farmer advisory generation.

This route does not implement advisory logic itself.
It delegates advisory generation to the already-tested
AdvisorIntegrationService.

=========================================================
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.app.services.advisor_service import (
    AdvisorIntegrationService,
    BackendAdvisorError,
)


# =========================================================
# BLUEPRINT
# =========================================================

advisory_bp = Blueprint(
    "advisory",
    __name__,
    url_prefix="/api",
)


# =========================================================
# SERVICE
# =========================================================

_advisor_service: AdvisorIntegrationService | None = None


def get_advisor_service() -> AdvisorIntegrationService:
    """
    Return the shared backend advisor service.

    The service is initialized lazily so importing the
    Flask route does not immediately initialize the
    advisory system.
    """

    global _advisor_service

    if _advisor_service is None:
        _advisor_service = AdvisorIntegrationService()

    return _advisor_service


# =========================================================
# ADVISORY ENDPOINT
# =========================================================

@advisory_bp.post("/advisory")
def generate_advisory():
    """
    Generate a farmer advisory from an existing
    AI diagnosis result.

    Expected JSON:

    {
        "diagnosis": {
            "prediction": {
                "class_name": "Blight",
                "confidence": 89.47
            }
        },
        "language": "en"
    }
    """

    # -----------------------------------------------------
    # CHECK JSON BODY
    # -----------------------------------------------------

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": (
                        "Request body must contain "
                        "valid JSON."
                    ),
                },
            }
        ), 400

    # -----------------------------------------------------
    # GET DIAGNOSIS
    # -----------------------------------------------------

    diagnosis = data.get(
        "diagnosis"
    )

    if not isinstance(diagnosis, dict):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "DIAGNOSIS_REQUIRED",
                    "message": (
                        "A valid diagnosis object "
                        "is required."
                    ),
                },
            }
        ), 400

    # -----------------------------------------------------
    # GET LANGUAGE
    # -----------------------------------------------------

    language = str(
        data.get(
            "language",
            "en",
        )
    ).lower().strip()

    # -----------------------------------------------------
    # GENERATE ADVISORY
    # -----------------------------------------------------

    try:

        service = get_advisor_service()

        result = (
            service.get_advisory_from_diagnosis(
                diagnosis=diagnosis,
                language=language,
            )
        )

        # -------------------------------------------------
        # SUCCESS RESPONSE
        # -------------------------------------------------

        return jsonify(
            {
                "success": True,
                "data": result,
            }
        ), 200

    except BackendAdvisorError as error:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "ADVISORY_ERROR",
                    "message": str(error),
                },
            }
        ), 400

    except Exception:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        "An unexpected error occurred "
                        "while generating the advisory."
                    ),
                },
            }
        ), 500