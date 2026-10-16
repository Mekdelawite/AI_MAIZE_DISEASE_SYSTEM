"""
=========================================================
Diagnosis API Routes
=========================================================

Flask API routes for maize disease diagnosis.

Responsibilities:

    - Authenticate the requesting user.
    - Accept maize leaf images.
    - Delegate AI inference to DiagnosisIntegrationService.
    - Save diagnosis under the authenticated user.
    - Return diagnosis results.
    - Provide authenticated diagnosis history.
    - Provide one diagnosis with its advisory.
    - Serve generated Grad-CAM heatmaps.

The route does not perform ML inference itself.

It delegates diagnosis processing to:

    DiagnosisIntegrationService

=========================================================
"""

from __future__ import annotations

import uuid
import json
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    send_from_directory,
)

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from backend.app.extensions import db

from backend.app.models.diagnosis_record import (
    DiagnosisRecord,
)
from backend.app.models.offline_sync_record import (
    OfflineSyncRecord,
)

from backend.app.services.diagnosis_service import (
    BackendDiagnosisError,
    DiagnosisIntegrationService,
)
from backend.app.services.upload_rate_limit_service import (
    UploadRateLimitService,
)


# =========================================================
# BLUEPRINT
# =========================================================

diagnosis_bp = Blueprint(
    "diagnosis",
    __name__,
    url_prefix="/api",
)


# =========================================================
# SERVICE
# =========================================================

_diagnosis_service: (
    DiagnosisIntegrationService | None
) = None


def get_diagnosis_service() -> DiagnosisIntegrationService:
    """
    Return the shared backend diagnosis service.

    The service is initialized lazily so importing this
    Flask route does not immediately load TensorFlow.
    """

    global _diagnosis_service

    if _diagnosis_service is None:
        _diagnosis_service = DiagnosisIntegrationService()

    return _diagnosis_service


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)


# =========================================================
# UPLOAD CONFIGURATION
# =========================================================

UPLOAD_DIR = (
    PROJECT_ROOT
    / "uploads"
)


ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


# =========================================================
# GRAD-CAM CONFIGURATION
# =========================================================

HEATMAP_DIR = (
    PROJECT_ROOT
    / "ml_model"
    / "explainability"
    / "outputs"
)


# =========================================================
# HELPERS
# =========================================================

def _allowed_file(
    filename: str,
) -> bool:
    """
    Check whether the uploaded file has an allowed
    image extension.
    """

    suffix = (
        Path(filename)
        .suffix
        .lower()
    )

    return suffix in ALLOWED_EXTENSIONS


def _extract_heatmap_filename(
    heatmap_path: str | None,
) -> str | None:
    """
    Extract only the filename from a heatmap path.

    Supports both Windows and Linux-style paths.

    Example Windows path:

        D:\\Projects\\AI_MAIZE_DISEASE_SYSTEM\\
        ml_model\\explainability\\outputs\\
        complete_diagnosis_xxx_heatmap.jpg

    Returns:

        complete_diagnosis_xxx_heatmap.jpg
    """

    if not heatmap_path:
        return None

    # Normalize Windows separators.
    normalized = str(
        heatmap_path
    ).replace(
        "\\",
        "/",
    )

    filename = normalized.split("/")[-1]

    if not filename:
        return None

    return filename


def _serialize_diagnosis(
    record: DiagnosisRecord,
    include_advisory: bool = False,
) -> dict[str, Any]:
    """
    Convert a DiagnosisRecord into a JSON-safe dictionary.

    The database may contain an absolute filesystem path
    for the heatmap. The API additionally provides a clean
    frontend-accessible heatmap URL.
    """

    # -----------------------------------------------------
    # HEATMAP INFORMATION
    # -----------------------------------------------------

    heatmap_filename = _extract_heatmap_filename(
        record.heatmap_path
    )

    heatmap_url = None

    if heatmap_filename:
        heatmap_url = (
            f"/api/heatmaps/"
            f"{heatmap_filename}"
        )

    # -----------------------------------------------------
    # BASIC DATA
    # -----------------------------------------------------

    data: dict[str, Any] = {
        "id": record.id,

        "user_id": record.user_id,

        "image_filename": (
            record.image_filename
        ),

        # Authenticated endpoint for the original uploaded leaf image.
        "image_url": (
            f"/api/diagnosis/history/{record.id}/image"
            if record.image_filename
            else None
        ),

        "disease_class": (
            record.disease_class
        ),

        "confidence": (
            record.confidence
        ),

        "model_name": (
            record.model_name
        ),

        "model_version": (
            record.model_version
        ),

        "prediction_time": (
            record.prediction_time
        ),

        "explainability_requested": (
            record.explainability_requested
        ),

        # Original database filesystem path.
        "heatmap_path": (
            record.heatmap_path
        ),

        # Filename only.
        "heatmap_filename": (
            heatmap_filename
        ),

        # Frontend-accessible API path.
        "heatmap_url": (
            heatmap_url
        ),

        "created_at": (
            record.created_at.isoformat()
            if record.created_at
            else None
        ),
    }

    # =====================================================
    # INCLUDE ADVISORY
    # =====================================================

    if include_advisory:

        advisory_records = getattr(
            record,
            "advisory_records",
            [],
        )

        if advisory_records:

            advisory = max(
                advisory_records,
                key=lambda item: (
                    item.created_at
                    if item.created_at
                    else 0
                ),
            )

            stored_advisory_text = advisory.advisory_text
            advisory_payload = None
            payload_marker = "\n\n__MAIZECARE_ADVISORY_PAYLOAD_V1__\n"
            if payload_marker in stored_advisory_text:
                readable_text, _, serialized_payload = stored_advisory_text.partition(payload_marker)
                try:
                    parsed_payload = json.loads(serialized_payload)
                    if isinstance(parsed_payload, dict):
                        advisory_payload = parsed_payload
                        stored_advisory_text = readable_text
                except (TypeError, ValueError):
                    pass

            data["advisory"] = {
                **(advisory_payload or {}),
                "id": (
                    advisory.id
                ),

                "advisory_id": (
                    advisory.id
                ),

                "diagnosis_id": (
                    advisory.diagnosis_id
                ),

                "language": (
                    advisory.language
                ),

                "advisory_text": (
                    stored_advisory_text
                ),

                "source": (
                    advisory.source
                ),

                "created_at": (
                    advisory.created_at.isoformat()
                    if advisory.created_at
                    else None
                ),
            }

        else:

            data["advisory"] = None

    return data


# =========================================================
# GRAD-CAM HEATMAP FILE SERVER
# =========================================================

@diagnosis_bp.get(
    "/heatmaps/<path:filename>"
)
def serve_heatmap(
    filename: str,
):
    """
    Serve generated Grad-CAM heatmap images.

    Frontend URL:

        /api/heatmaps/<filename>

    Example:

        /api/heatmaps/
        complete_diagnosis_xxx_heatmap.jpg
    """

    try:

        # -------------------------------------------------
        # SECURITY
        # -------------------------------------------------
        #
        # Only use the final filename.
        #
        # This prevents a filesystem path such as:
        #
        # D:/Projects/...
        #
        # from being interpreted as part of the URL.
        # -------------------------------------------------

        safe_filename = (
            Path(filename)
            .name
        )

        # -------------------------------------------------
        # CHECK FILE
        # -------------------------------------------------

        heatmap_file = (
            HEATMAP_DIR
            / safe_filename
        )

        if not heatmap_file.is_file():

            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": (
                            "HEATMAP_NOT_FOUND"
                        ),
                        "message": (
                            "Heatmap image could "
                            "not be found."
                        ),
                    },
                }
            ), 404

        # -------------------------------------------------
        # SERVE IMAGE
        # -------------------------------------------------

        return send_from_directory(
            HEATMAP_DIR,
            safe_filename,
        )

    except Exception:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "HEATMAP_ERROR"
                    ),
                    "message": (
                        "Unable to serve "
                        "heatmap image."
                    ),
                },
            }
        ), 500


# =========================================================
# DIAGNOSIS ENDPOINT
# =========================================================

@diagnosis_bp.post(
    "/diagnosis"
)
@jwt_required()
def diagnose_image():
    """
    Diagnose a maize leaf image.

    Authentication:
        Required.

    Expected request:
        multipart/form-data

    Required field:
        image

    Optional field:
        explain
    """

    # =====================================================
    # AUTHENTICATED USER
    # =====================================================

    identity = get_jwt_identity()

    try:

        user_id = int(
            identity
        )

    except (
        TypeError,
        ValueError,
    ):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INVALID_USER_ID"
                    ),
                    "message": (
                        "Authenticated user "
                        "identity is invalid."
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
                    "code": (
                        "IMAGE_REQUIRED"
                    ),
                    "message": (
                        "No image file was "
                        "provided. Use the "
                        "'image' form field."
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

    # =====================================================
    # CHECK FILENAME
    # =====================================================

    if not image.filename:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INVALID_FILENAME"
                    ),
                    "message": (
                        "The uploaded image "
                        "has no filename."
                    ),
                },
            }
        ), 400

    # =====================================================
    # CHECK EXTENSION
    # =====================================================

    if not _allowed_file(
        image.filename
    ):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INVALID_IMAGE_TYPE"
                    ),
                    "message": (
                        "Unsupported image "
                        "type. Allowed types: "
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
    # SAFE TEMPORARY FILENAME
    # =====================================================

    extension = (
        Path(
            image.filename
        )
        .suffix
        .lower()
    )

    filename = (
        "diagnosis_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    image_path = (
        UPLOAD_DIR
        / filename
    )

    diagnosis_succeeded = False

    # =====================================================
    # SAVE + PROCESS
    # =====================================================

    try:

        # -------------------------------------------------
        # SAVE IMAGE
        # -------------------------------------------------

        image.save(
            image_path
        )

        # -------------------------------------------------
        # EXPLAIN FLAG
        # -------------------------------------------------

        explain_value = (
            request.form.get(
                "explain",
                "false",
            )
            .lower()
            .strip()
        )

        explain = (
            explain_value
            in {
                "1",
                "true",
                "yes",
            }
        )

        # -------------------------------------------------
        # RUN DIAGNOSIS
        # -------------------------------------------------

        service = (
            get_diagnosis_service()
        )

        result = service.diagnose(
            image_path=image_path,
            explain=explain,
            user_id=user_id,
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

    except BackendDiagnosisError as error:

        current_app.logger.warning(
            "Diagnosis completion failed: %s",
            error,
        )

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "DIAGNOSIS_ERROR"
                    ),
                    "message": str(error),
                },
            }
        ), 500

    except Exception:

        current_app.logger.exception(
            "Unexpected error while completing diagnosis."
        )

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INTERNAL_ERROR"
                    ),
                    "message": (
                        "An unexpected error "
                        "occurred while "
                        "processing the image."
                    ),
                },
            }
        ), 500

    finally:

        # -------------------------------------------------
        # Keep successful uploads because diagnosis history links to them.
        # Failed uploads remain temporary and are cleaned up here.
        # -------------------------------------------------

        try:

            if not diagnosis_succeeded and image_path.exists():

                image_path.unlink()

        except Exception:

            pass


# =========================================================
# DIAGNOSIS HISTORY
# =========================================================

@diagnosis_bp.get(
    "/diagnosis/history"
)
@jwt_required()
def diagnosis_history():
    """
    Return diagnosis history for the authenticated user.

    Users can only see their own diagnosis records.
    """

    # =====================================================
    # AUTHENTICATED USER
    # =====================================================

    identity = get_jwt_identity()

    try:

        user_id = int(
            identity
        )

    except (
        TypeError,
        ValueError,
    ):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INVALID_USER_ID"
                    ),
                    "message": (
                        "Authenticated user "
                        "identity is invalid."
                    ),
                },
            }
        ), 401

    # =====================================================
    # OPTIONAL LIMIT
    # =====================================================

    limit_value = (
        request.args.get(
            "limit",
            "20",
        )
    )

    try:

        limit = int(
            limit_value
        )

    except ValueError:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INVALID_LIMIT"
                    ),
                    "message": (
                        "The limit must be "
                        "a valid integer."
                    ),
                },
            }
        ), 400

    # -----------------------------------------------------
    # PROTECT DATABASE
    # -----------------------------------------------------

    limit = max(
        1,
        min(
            limit,
            100,
        ),
    )

    # =====================================================
    # QUERY USER RECORDS
    # =====================================================

    try:

        user_diagnoses = DiagnosisRecord.query.filter(
            DiagnosisRecord.user_id == user_id
        )
        total_count = user_diagnoses.count()

        records = (
            user_diagnoses
            .order_by(
                DiagnosisRecord.created_at.desc()
            )
            .limit(
                limit
            )
            .all()
        )

    except Exception:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "DATABASE_ERROR"
                    ),
                    "message": (
                        "Unable to retrieve "
                        "diagnosis history."
                    ),
                },
            }
        ), 500

    # =====================================================
    # SERIALIZE
    # =====================================================

    history = [
        _serialize_diagnosis(
            record
        )
        for record in records
    ]

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify(
        {
            "success": True,
            "data": {
                "user_id": user_id,
                "count": len(history),
                "total_count": total_count,
                "diagnoses": history,
            },
        }
    ), 200


# =========================================================
# SINGLE DIAGNOSIS
# =========================================================

@diagnosis_bp.get(
    "/diagnosis/history/<int:diagnosis_id>/image"
)
@jwt_required()
def get_diagnosis_history_image(diagnosis_id: int):
    """Serve the authenticated user's original leaf upload."""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_USER_ID",
                "message": "Authenticated user identity is invalid.",
            },
        }), 401

    record = DiagnosisRecord.query.filter_by(
        id=diagnosis_id,
        user_id=user_id,
    ).first()
    if record is None:
        return jsonify({
            "success": False,
            "error": {
                "code": "DIAGNOSIS_NOT_FOUND",
                "message": "Diagnosis not found.",
            },
        }), 404

    filename = record.image_filename
    if (
        not filename
        or Path(filename).name != filename
        or Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS
    ):
        return jsonify({
            "success": False,
            "error": {
                "code": "IMAGE_NOT_FOUND",
                "message": "Original leaf image could not be found.",
            },
        }), 404

    upload_dir = Path(current_app.config["UPLOAD_DIR"]).resolve()
    image_path = (upload_dir / filename).resolve()
    if not image_path.is_relative_to(upload_dir) or not image_path.is_file():
        return jsonify({
            "success": False,
            "error": {
                "code": "IMAGE_NOT_FOUND",
                "message": "Original leaf image could not be found.",
            },
        }), 404

    return send_from_directory(upload_dir, filename, conditional=True, max_age=3600)

@diagnosis_bp.get(
    "/diagnosis/history/<int:diagnosis_id>"
)
@jwt_required()
def get_diagnosis_history_item(
    diagnosis_id: int,
):
    """
    Return one diagnosis belonging to the authenticated
    user.

    The advisory associated with the diagnosis is also
    returned when available.
    """

    # =====================================================
    # AUTHENTICATED USER
    # =====================================================

    identity = get_jwt_identity()

    try:

        user_id = int(
            identity
        )

    except (
        TypeError,
        ValueError,
    ):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INVALID_USER_ID"
                    ),
                    "message": (
                        "Authenticated user "
                        "identity is invalid."
                    ),
                },
            }
        ), 401

    # =====================================================
    # QUERY WITH USER OWNERSHIP
    # =====================================================

    record = (
        DiagnosisRecord.query
        .filter(
            DiagnosisRecord.id
            == diagnosis_id,
            DiagnosisRecord.user_id
            == user_id,
        )
        .first()
    )

    # =====================================================
    # NOT FOUND
    # =====================================================

    if record is None:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "DIAGNOSIS_NOT_FOUND"
                    ),
                    "message": (
                        "Diagnosis not found."
                    ),
                },
            }
        ), 404

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify(
        {
            "success": True,
            "data": _serialize_diagnosis(
                record,
                include_advisory=True,
            ),
        }
    ), 200


# =========================================================
# DELETE DIAGNOSIS HISTORY ITEM
# =========================================================

@diagnosis_bp.delete(
    "/diagnosis/history/<int:diagnosis_id>"
)
@jwt_required()
def delete_diagnosis_history_item(
    diagnosis_id: int,
):
    """
    Delete one diagnosis belonging to the authenticated
    user.

    Because advisory_records use ON DELETE CASCADE,
    the associated advisory will also be removed.
    """

    # =====================================================
    # AUTHENTICATED USER
    # =====================================================

    identity = get_jwt_identity()

    try:

        user_id = int(
            identity
        )

    except (
        TypeError,
        ValueError,
    ):

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "INVALID_USER_ID"
                    ),
                    "message": (
                        "Authenticated user "
                        "identity is invalid."
                    ),
                },
            }
        ), 401

    # =====================================================
    # FIND USER RECORD
    # =====================================================

    record = (
        DiagnosisRecord.query
        .filter(
            DiagnosisRecord.id
            == diagnosis_id,
            DiagnosisRecord.user_id
            == user_id,
        )
        .first()
    )

    if record is None:

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "DIAGNOSIS_NOT_FOUND"
                    ),
                    "message": (
                        "Diagnosis not found."
                    ),
                },
            }
        ), 404

    # =====================================================
    # DELETE
    # =====================================================

    try:

        # Keep the offline sync audit row, but detach its optional diagnosis
        # reference so the foreign key does not block history deletion.
        OfflineSyncRecord.query.filter(
            OfflineSyncRecord.diagnosis_id == diagnosis_id,
            OfflineSyncRecord.user_id == user_id,
        ).update(
            {OfflineSyncRecord.diagnosis_id: None},
            synchronize_session=False,
        )

        db.session.delete(
            record
        )

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": (
                        "DATABASE_ERROR"
                    ),
                    "message": (
                        "Unable to delete "
                        "diagnosis."
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
                    "Diagnosis deleted "
                    "successfully."
                ),
                "diagnosis_id": (
                    diagnosis_id
                ),
            },
        }
    ), 200
