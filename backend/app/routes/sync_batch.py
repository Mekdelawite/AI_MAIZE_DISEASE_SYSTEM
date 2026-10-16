"""
=========================================================
Offline Batch Synchronization API Route
=========================================================

Synchronizes multiple offline diagnosis operations.

Each operation is processed independently through the
existing OfflineSyncService.

A failure in one operation does not stop the remaining
operations from being processed.

=========================================================
"""

from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

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


sync_batch_bp = Blueprint(
    "sync_batch",
    __name__,
    url_prefix="/api",
)


_sync_service: OfflineSyncService | None = None


def get_sync_service() -> OfflineSyncService:
    global _sync_service

    if _sync_service is None:
        _sync_service = OfflineSyncService()

    return _sync_service


PROJECT_ROOT = Path(__file__).resolve().parents[3]

UPLOAD_DIR = PROJECT_ROOT / "uploads"

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MAX_BATCH_SIZE = 10


def _allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _parse_bool(value: str) -> bool:
    return value.lower().strip() in {
        "1",
        "true",
        "yes",
    }


@sync_batch_bp.post("/sync/batch")
@jwt_required()
def synchronize_batch():
    """
    Synchronize multiple offline diagnosis operations.

    Expected multipart/form-data:

        operation_ids
        images

    Optional:

        operation_type
        language
        explain

    operation_ids and images must be supplied in the
    same order.

    Example:

        operation_ids=op1
        operation_ids=op2

        images=image1
        images=image2
    """

    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
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

    operation_ids = [
        value.strip()
        for value in request.form.getlist("operation_ids")
        if value.strip()
    ]

    images = request.files.getlist("images")

    if not operation_ids:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "OPERATION_IDS_REQUIRED",
                    "message": (
                        "At least one operation_id is required."
                    ),
                },
            }
        ), 400

    if not images:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "IMAGES_REQUIRED",
                    "message": (
                        "At least one image is required."
                    ),
                },
            }
        ), 400

    if len(operation_ids) != len(images):
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "BATCH_SIZE_MISMATCH",
                    "message": (
                        "The number of operation_ids must "
                        "match the number of images."
                    ),
                },
            }
        ), 400

    if len(operation_ids) > MAX_BATCH_SIZE:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "BATCH_TOO_LARGE",
                    "message": (
                        f"A maximum of {MAX_BATCH_SIZE} "
                        "operations can be synchronized "
                        "at once."
                    ),
                },
            }
        ), 400

    if len(set(operation_ids)) != len(operation_ids):
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "DUPLICATE_OPERATION_ID",
                    "message": (
                        "Each operation_id must be unique "
                        "within the batch."
                    ),
                },
            }
        ), 400
            # =====================================================
    # UPLOAD RATE LIMIT
    # =====================================================

    try:

        upload_limit = (
            UploadRateLimitService.check_and_record(
                user_id=user_id,
                upload_count=len(images),
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
                        "more images."
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


    operation_type = (
        request.form.get(
            "operation_type",
            "diagnosis",
        )
        .lower()
        .strip()
    )

    language = (
        request.form.get(
            "language",
            "en",
        )
        .lower()
        .strip()
    )

    explain = _parse_bool(
        request.form.get(
            "explain",
            "false",
        )
    )

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []

    completed = 0
    failed = 0

    for operation_id, image in zip(
        operation_ids,
        images,
    ):
        image_path: Path | None = None

        try:
            # -------------------------------------------------
            # FILENAME VALIDATION
            # -------------------------------------------------

            if not image.filename:
                raise OfflineSyncError(
                    "The uploaded image has no filename."
                )

            if not _allowed_file(
                image.filename
            ):
                raise OfflineSyncError(
                    "Unsupported image type. "
                    "Allowed types: JPG, JPEG, PNG, WEBP."
                )

            # -------------------------------------------------
            # TEMPORARY FILE
            # -------------------------------------------------

            extension = Path(
                image.filename
            ).suffix.lower()

            filename = (
                "sync_batch_"
                f"{uuid.uuid4().hex}"
                f"{extension}"
            )

            image_path = (
                UPLOAD_DIR / filename
            )

            image.save(image_path)

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
                failed += 1

                results.append(
                    {
                        "operation_id": operation_id,
                        "success": False,
                        "error": {
                            "code": "INVALID_SYNC_IMAGE",
                            "message": str(error),
                        },
                    }
                )

                continue

            # -------------------------------------------------
            # SYNCHRONIZATION
            # -------------------------------------------------

            service = get_sync_service()

            result = service.synchronize_diagnosis(
                operation_id=operation_id,
                user_id=user_id,
                image_path=validated_image_path,
                language=language,
                explain=explain,
                operation_type=operation_type,
            )

            completed += 1

            results.append(
                {
                    "operation_id": operation_id,
                    "success": True,
                    "data": result,
                }
            )

        except OfflineSyncError as error:
            failed += 1

            results.append(
                {
                    "operation_id": operation_id,
                    "success": False,
                    "error": {
                        "code": "OFFLINE_SYNC_ERROR",
                        "message": str(error),
                    },
                }
            )

        except Exception:
            failed += 1

            print(
                "Batch synchronization unexpected error "
                f"for operation {operation_id!r}"
            )

            results.append(
                {
                    "operation_id": operation_id,
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": (
                            "An unexpected error occurred "
                            "during synchronization."
                        ),
                    },
                }
            )

        finally:
            if (
                image_path is not None
                and image_path.exists()
            ):
                try:
                    image_path.unlink()
                except Exception:
                    pass

    return jsonify(
        {
            "success": True,
            "data": {
                "total": len(operation_ids),
                "completed": completed,
                "failed": failed,
                "results": results,
            },
        }
    ), 200