
"""
=========================================================
Complete Diagnosis API Route
=========================================================

Provides the complete authenticated farmer workflow:

    Image
      ↓
    JWT Authentication
      ↓
    AI Diagnosis
      ↓
    Disease + Confidence
      ↓
    PostgreSQL Diagnosis Record
      ↓
    Agricultural Advisory
      ↓
    PostgreSQL Advisory Record
      ↓
    Complete Response

The route delegates processing to:

    DiagnosisAdvisoryIntegrationService

=========================================================
"""

from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from backend.app.services.diagnosis_advisory_service import (
    DiagnosisAdvisoryError,
    DiagnosisAdvisoryIntegrationService,
)
from backend.app.services.upload_rate_limit_service import (
    UploadRateLimitService,
)


# =========================================================
# BLUEPRINT
# =========================================================

complete_diagnosis_bp = Blueprint(
    "complete_diagnosis",
    __name__,
    url_prefix="/api",
)


# =========================================================
# SERVICE
# =========================================================

_integration_service: (
    DiagnosisAdvisoryIntegrationService | None
) = None


def get_integration_service() -> DiagnosisAdvisoryIntegrationService:
    """
    Return the shared diagnosis + advisory service.

    The service is initialized lazily so importing this
    route does not immediately load TensorFlow.
    """

    global _integration_service

    if _integration_service is None:
        _integration_service = (
            DiagnosisAdvisoryIntegrationService()
        )

    return _integration_service


# =========================================================
# UPLOAD CONFIGURATION
# =========================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parents[3]
)

UPLOAD_DIR = PROJECT_ROOT / "uploads"

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


# =========================================================
# HELPERS
# =========================================================

def _allowed_file(filename: str) -> bool:
    """
    Check whether the uploaded file has an allowed
    image extension.
    """

    suffix = Path(filename).suffix.lower()

    return suffix in ALLOWED_EXTENSIONS


# =========================================================
# COMPLETE DIAGNOSIS ENDPOINT
# =========================================================

@complete_diagnosis_bp.post(
    "/diagnosis/complete"
)
@jwt_required()
def complete_diagnosis():
    """
    Run the complete authenticated farmer diagnosis
    workflow.

    Expected request:

        multipart/form-data

    Required:

        image

    Optional:

        language
        explain

    Authentication:

        Authorization: Bearer <JWT>

    The authenticated user's ID is extracted from the JWT
    and associated with the diagnosis and advisory records.
    """

    # =====================================================
    # GET AUTHENTICATED USER
    # =====================================================

    try:
        user_id = int(
            get_jwt_identity()
        )

    except (
        TypeError,
        ValueError,
    ) as error:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN_ID",
                    "message": (
                        "The authenticated user ID "
                        "contained in the token is invalid."
                    ),
                },
            }
        ), 401

    # =====================================================
    # CHECK IMAGE FIELD
    # =====================================================

    if "image" not in request.files:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "IMAGE_REQUIRED",
                    "message": (
                        "No image file was provided. "
                        "Use the 'image' form field."
                    ),
                },
            }
        ), 400

    image = request.files["image"]
        # =====================================================
    # UPLOAD RATE LIMIT
    # =====================================================

    try:

        upload_limit = (
            UploadRateLimitService.check_and_record(
                user_id=user_id,
                upload_count=1,
            )
        )

    except ValueError as error:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_UPLOAD_RATE_LIMIT_REQUEST",
                    "message": str(error),
                },
            }
        ), 400

    if not upload_limit["allowed"]:

        response = jsonify(
            {
                "success": False,
                "error": {
                    "code": "UPLOAD_RATE_LIMIT_EXCEEDED",
                    "message": (
                        "Too many image uploads. "
                        "Please wait before uploading "
                        "another image."
                    ),
                    "current_count": (
                        upload_limit["current_count"]
                    ),
                    "remaining": (
                        upload_limit["remaining"]
                    ),
                    "retry_after_seconds": (
                        upload_limit["retry_after_seconds"]
                    ),
                },
            }
        )

        response.headers["Retry-After"] = str(
            upload_limit["retry_after_seconds"]
        )

        return response, 429


    # =====================================================
    # CHECK FILENAME
    # =====================================================

    if not image.filename:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_FILENAME",
                    "message": (
                        "The uploaded image has no filename."
                    ),
                },
            }
        ), 400

    # =====================================================
    # CHECK IMAGE TYPE
    # =====================================================

    if not _allowed_file(image.filename):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_IMAGE_TYPE",
                    "message": (
                        "Unsupported image type. "
                        "Allowed types: "
                        "JPG, JPEG, PNG, WEBP."
                    ),
                },
            }
        ), 400

    # =====================================================
    # LANGUAGE
    # =====================================================

    language = (
        request.form.get(
            "language",
            "en",
        )
        .lower()
        .strip()
    )

    # =====================================================
    # EXPLAIN FLAG
    # =====================================================

    explain_value = (
        request.form.get(
            "explain",
            "false",
        )
        .lower()
        .strip()
    )

    explain = explain_value in {
        "1",
        "true",
        "yes",
    }

    # =====================================================
    # PREPARE UPLOAD DIRECTORY
    # =====================================================

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =====================================================
    # SAFE UPLOAD FILENAME
    # =====================================================

    extension = Path(
        image.filename
    ).suffix.lower()

    filename = (
        "complete_diagnosis_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    image_path = (
        UPLOAD_DIR / filename
    )

    diagnosis_succeeded = False

    # =====================================================
    # SAVE + PROCESS
    # =====================================================

    try:

        # -------------------------------------------------
        # SAVE UPLOADED IMAGE
        # -------------------------------------------------

        image.save(
            image_path
        )

        # -------------------------------------------------
        # RUN COMPLETE WORKFLOW
        # -------------------------------------------------

        service = (
            get_integration_service()
        )

        result = (
            service.diagnose_and_advise(
                image_path=image_path,
                language=language,
                explain=explain,
                user_id=user_id,
            )
        )
        diagnosis_succeeded = True

        # -------------------------------------------------
        # SUCCESS RESPONSE
        # -------------------------------------------------

        return jsonify(
            {
                "success": True,
                "data": result,
            }
        ), 200

    # =====================================================
    # KNOWN INTEGRATION ERROR
    # =====================================================

    except DiagnosisAdvisoryError as error:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "DIAGNOSIS_ADVISORY_ERROR"
                    ),
                    "message": str(error),
                },
            }
        ), 500

    # =====================================================
    # UNEXPECTED ERROR
    # =====================================================

    except Exception as error:

        # Keep the API response safe while allowing the
        # actual exception to appear in the Flask console.

        print(
            "Complete diagnosis unexpected error:",
            repr(error),
        )

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        "An unexpected error occurred "
                        "while processing the image."
                    ),
                },
            }
        ), 500

    # =====================================================
    # REMOVE FAILED UPLOADS
    # =====================================================

    finally:

        try:

            # History records reference this file, so keep successful
            # uploads available for the farmer's diagnosis history.
            if not diagnosis_succeeded and image_path.exists():

                image_path.unlink()

        except Exception:

            pass

