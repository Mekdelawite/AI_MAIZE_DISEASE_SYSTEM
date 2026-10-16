"""
=========================================================
Offline Synchronization API Route
=========================================================

Provides authenticated synchronization of offline
diagnosis operations.

Workflow:

    Offline Queue
         ↓
    POST /api/sync
         ↓
    JWT Authentication
         ↓
    Temporary Image
         ↓
    Sync Image Validation
         ↓
    OfflineSyncService
         ↓
    Existing DiagnosisAdvisoryIntegrationService
         ↓
    PostgreSQL

The route does not implement diagnosis logic.

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

from backend.app.services.offline_sync_service import (
    OfflineSyncError,
    OfflineSyncService,
)

from backend.app.services.sync_image_validator import (
    SyncImageValidationError,
    SyncImageValidator,
)
from backend.app.services.upload_rate_limit_service import (
    UploadRateLimitService,
)


# =========================================================
# BLUEPRINT
# =========================================================

sync_bp = Blueprint(
    "sync",
    __name__,
    url_prefix="/api",
)


# =========================================================
# SERVICE
# =========================================================

_sync_service: OfflineSyncService | None = None


def get_sync_service() -> OfflineSyncService:
    """
    Return the shared offline synchronization service.

    The service is initialized lazily.
    """
    global _sync_service

    if _sync_service is None:
        _sync_service = OfflineSyncService()

    return _sync_service


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

    This is an early filename-level check.

    The actual image is validated later by
    SyncImageValidator.
    """
    suffix = Path(filename).suffix.lower()

    return suffix in ALLOWED_EXTENSIONS


# =========================================================
# SYNCHRONIZATION ENDPOINT
# =========================================================

@sync_bp.post("/sync")
@jwt_required()
def synchronize():
    """
    Synchronize one offline diagnosis operation.

    Expected request:

        multipart/form-data

    Required:

        operation_id
        image

    Optional:

        operation_type
        language
        explain

    Authentication:

        Authorization: Bearer <JWT>
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
    ):
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
    # OPERATION ID
    # =====================================================

    operation_id = (
        request.form.get(
            "operation_id",
            "",
        )
        .strip()
    )

    if not operation_id:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "OPERATION_ID_REQUIRED",
                    "message": (
                        "operation_id is required."
                    ),
                },
            }
        ), 400

    # =====================================================
    # OPERATION TYPE
    # =====================================================

    operation_type = (
        request.form.get(
            "operation_type",
            "diagnosis",
        )
        .lower()
        .strip()
    )

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
    # EXPLAIN
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
    # IMAGE FIELD
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
    # FILENAME
    # =====================================================

    # =====================================================
    # FILENAME
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
    # IMAGE TYPE
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
    # PREPARE UPLOAD DIRECTORY
    # =====================================================

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =====================================================
    # TEMPORARY FILENAME
    # =====================================================

    extension = Path(
        image.filename
    ).suffix.lower()

    filename = (
        "sync_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    image_path = (
        UPLOAD_DIR / filename
    )

    # =====================================================
    # SAVE + VALIDATE + SYNCHRONIZE
    # =====================================================

    try:

        # -------------------------------------------------
        # SAVE IMAGE
        # -------------------------------------------------

        image.save(
            image_path
        )

        # -------------------------------------------------
        # ACTUAL IMAGE VALIDATION
        # -------------------------------------------------

        try:
            validated_image_path = (
                SyncImageValidator.validate(
                    image_path
                )
            )

        except SyncImageValidationError as error:

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_SYNC_IMAGE",
                        "message": str(error),
                    },
                }
            ), 400

        # -------------------------------------------------
        # SYNCHRONIZE
        # -------------------------------------------------

        service = get_sync_service()

        result = (
            service.synchronize_diagnosis(
                operation_id=operation_id,
                user_id=user_id,
                image_path=validated_image_path,
                language=language,
                explain=explain,
                operation_type=operation_type,
            )
        )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return jsonify(
            {
                "success": True,
                "data": result,
            }
        ), 200

    # =====================================================
    # KNOWN SYNCHRONIZATION ERROR
    # =====================================================

    except OfflineSyncError as error:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "OFFLINE_SYNC_ERROR",
                    "message": str(error),
                },
            }
        ), 400

    # =====================================================
    # UNEXPECTED ERROR
    # =====================================================

    except Exception as error:

        print(
            "Offline synchronization unexpected error:",
            repr(error),
        )

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        "An unexpected error occurred "
                        "during synchronization."
                    ),
                },
            }
        ), 500

    # =====================================================
    # CLEANUP
    # =====================================================

    finally:

        try:

            if image_path.exists():
                image_path.unlink()

        except Exception:
            pass