
"""
=========================================================
Offline Synchronization Service
=========================================================

Handles synchronization of offline diagnosis operations.

Responsibilities:
    - Validate synchronization input
    - Enforce operation ownership
    - Enforce idempotency using operation_id
    - Enforce maximum retry attempts
    - Permanently store synchronization images
    - Preserve diagnosis history images
    - Track synchronization state
    - Reuse the existing diagnosis + advisory service
    - Preserve failed operations for retry/recovery
    - Recover interrupted processing operations
    - Clean up temporary synchronization images
=========================================================
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from flask import current_app

from backend.app.extensions import db
from backend.app.models.offline_sync_record import OfflineSyncRecord
from backend.app.services.diagnosis_advisory_service import (
    DiagnosisAdvisoryError,
    DiagnosisAdvisoryIntegrationService,
)
from backend.app.services.sync_storage_service import (
    SyncStorageError,
    SyncStorageService,
)


class OfflineSyncError(Exception):
    """Raised when an offline synchronization operation fails."""


class OfflineSyncService:
    """
    Service responsible for offline diagnosis synchronization.

    The service uses operation_id as an idempotency key so that
    retrying the same offline operation does not create duplicate
    synchronization operations.
    """

    VALID_OPERATION_TYPES = {
        "diagnosis",
    }

    VALID_LANGUAGES = {
        "en",
        "am",
    }

    MAX_ATTEMPTS = 3

    def __init__(self) -> None:
        """Initialize the offline synchronization service."""

        self._diagnosis_advisory_service = (
            DiagnosisAdvisoryIntegrationService()
        )

    # =====================================================
    # Validation helpers
    # =====================================================

    @staticmethod
    def _validate_operation_id(
        operation_id: str,
    ) -> str:
        """Validate and normalize operation ID."""

        if operation_id is None:
            raise OfflineSyncError(
                "Synchronization operation ID is required."
            )

        normalized = str(operation_id).strip()

        if not normalized:
            raise OfflineSyncError(
                "Synchronization operation ID is required."
            )

        if len(normalized) > 100:
            raise OfflineSyncError(
                "Synchronization operation ID must not exceed 100 characters."
            )

        return normalized

    @classmethod
    def _validate_operation_type(
        cls,
        operation_type: str,
    ) -> str:
        """Validate synchronization operation type."""

        normalized = (
            str(operation_type or "diagnosis")
            .strip()
            .lower()
        )

        if normalized not in cls.VALID_OPERATION_TYPES:
            raise OfflineSyncError(
                "Unsupported synchronization operation type."
            )

        return normalized

    @staticmethod
    def _validate_user_id(
        user_id: int,
    ) -> int:
        """Validate authenticated user ID."""

        try:
            normalized = int(user_id)
        except (TypeError, ValueError) as exc:
            raise OfflineSyncError(
                "Authenticated user ID is invalid."
            ) from exc

        if normalized <= 0:
            raise OfflineSyncError(
                "Authenticated user ID is invalid."
            )

        return normalized

    @staticmethod
    def _validate_image_path(
        image_path: str | Path,
    ) -> Path:
        """
        Validate synchronization image path.

        Detailed image validation such as extension, file size,
        and readable image content is handled by
        SyncImageValidator in the route layer.
        """

        if not image_path:
            raise OfflineSyncError(
                "Synchronization image is required."
            )

        path = Path(image_path)

        if not path.exists():
            raise OfflineSyncError(
                "Synchronization image was not found."
            )

        if not path.is_file():
            raise OfflineSyncError(
                "Synchronization image is not a valid file."
            )

        return path

    @classmethod
    def _validate_language(
        cls,
        language: str,
    ) -> str:
        """Validate diagnosis language."""

        normalized = (
            str(language or "en")
            .strip()
            .lower()
        )

        if normalized not in cls.VALID_LANGUAGES:
            raise OfflineSyncError(
                "Unsupported language. Supported languages are en and am."
            )

        return normalized

    # =====================================================
    # Diagnosis history image storage
    # =====================================================

    @staticmethod
    def _create_history_image_copy(
        source_path: str | Path,
        operation_id: str,
    ) -> Path:
        """
        Create a permanent image copy for diagnosis history.

        The history image is stored directly inside UPLOAD_DIR,
        because the diagnosis history image endpoint serves
        files from that directory.

        The operation ID produces a stable filename, allowing
        retries and crash recovery to reuse the same copy.

        This image must NOT be deleted during synchronization
        cleanup.
        """

        source = Path(source_path).resolve()

        if not source.is_file():
            raise OfflineSyncError(
                "The synchronization image was not found."
            )

        upload_dir = Path(
            current_app.config["UPLOAD_DIR"]
        ).resolve()

        upload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        operation_hash = hashlib.sha256(
            operation_id.encode("utf-8")
        ).hexdigest()[:24]

        extension = source.suffix.lower()

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        if extension not in allowed_extensions:
            raise OfflineSyncError(
                "The synchronization image format is unsupported."
            )

        history_path = (
            upload_dir
            / f"offline_diagnosis_{operation_hash}{extension}"
        )

        # Reuse an existing permanent copy during retries
        # and crash recovery.
        if not history_path.exists():
            shutil.copy2(
                source,
                history_path,
            )

        return history_path

    # =====================================================
    # Existing operation lookup
    # =====================================================

    @staticmethod
    def _get_existing_operation(
        operation_id: str,
        user_id: int,
    ) -> OfflineSyncRecord | None:
        """
        Find an existing synchronization operation.

        Ownership is checked here so one farmer cannot access
        another farmer's synchronization operation.
        """

        record = (
            OfflineSyncRecord.query
            .filter_by(
                operation_id=operation_id,
            )
            .first()
        )

        if record is None:
            return None

        if record.user_id != user_id:
            raise OfflineSyncError(
                "Synchronization operation does not belong "
                "to the authenticated user."
            )

        return record

    # =====================================================
    # Result builder
    # =====================================================

    @staticmethod
    def _build_result(
        record: OfflineSyncRecord,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a consistent synchronization response."""

        response: dict[str, Any] = {
            "operation_id": record.operation_id,
            "operation_type": record.operation_type,
            "status": record.status,
            "attempts": record.attempts,
            "diagnosis_id": record.diagnosis_id,
        }

        if result is not None:
            response["result"] = result

        if record.error_message:
            response["error"] = record.error_message

        return response

    # =====================================================
    # Synchronize diagnosis
    # =====================================================

    def synchronize_diagnosis(
        self,
        operation_id: str,
        operation_type: str,
        user_id: int,
        image_path: str | Path,
        language: str = "en",
        explain: bool = False,
    ) -> dict[str, Any]:
        """
        Synchronize one offline diagnosis operation.

        Flow:

            1. Validate request
            2. Check idempotency / ownership
            3. Store image for synchronization recovery
            4. Mark operation as processing
            5. Create/reuse a permanent history image
            6. Reuse diagnosis + advisory service
            7. Store diagnosis ID
            8. Mark operation completed
            9. Delete only the temporary sync image
        """

        # -------------------------------------------------
        # Validate input
        # -------------------------------------------------

        normalized_operation_id = (
            self._validate_operation_id(
                operation_id
            )
        )

        normalized_operation_type = (
            self._validate_operation_type(
                operation_type
            )
        )

        normalized_user_id = (
            self._validate_user_id(
                user_id
            )
        )

        path = self._validate_image_path(
            image_path
        )

        normalized_language = (
            self._validate_language(
                language
            )
        )

        # -------------------------------------------------
        # Check existing operation
        # -------------------------------------------------

        existing_record = (
            self._get_existing_operation(
                normalized_operation_id,
                normalized_user_id,
            )
        )

        if existing_record is not None:

            # Already completed: return previous result.
            if existing_record.status == "completed":
                return self._build_result(
                    existing_record
                )

            # Prevent concurrent processing.
            if existing_record.status == "processing":
                raise OfflineSyncError(
                    "This synchronization operation is already "
                    "being processed."
                )

            # Enforce retry limit.
            if existing_record.attempts >= self.MAX_ATTEMPTS:
                raise OfflineSyncError(
                    "Maximum synchronization attempts have "
                    "been reached."
                )

            record = existing_record

        else:

            # -------------------------------------------------
            # Create new synchronization record
            # -------------------------------------------------

            record = OfflineSyncRecord(
                operation_id=normalized_operation_id,
                user_id=normalized_user_id,
                operation_type=normalized_operation_type,
                status="pending",
                image_path=None,
                diagnosis_id=None,
                error_message=None,
                attempts=0,
            )

            db.session.add(record)
            db.session.commit()

        # =================================================
        # Synchronization image storage
        # =================================================

        try:

            # Reuse a previously stored recovery image
            # when it still exists.
            existing_stored_path = getattr(
                record,
                "image_path",
                None,
            )

            if existing_stored_path:
                stored_image_path = Path(
                    existing_stored_path
                )

                if not stored_image_path.exists():
                    stored_image_path = (
                        SyncStorageService.store(
                            source_path=path,
                            operation_id=normalized_operation_id,
                        )
                    )
            else:
                stored_image_path = (
                    SyncStorageService.store(
                        source_path=path,
                        operation_id=normalized_operation_id,
                    )
                )

            record.image_path = str(
                stored_image_path
            )

            record.status = "processing"
            record.attempts += 1
            record.error_message = None

            db.session.commit()

        except SyncStorageError as error:

            db.session.rollback()

            record = (
                self._get_existing_operation(
                    normalized_operation_id,
                    normalized_user_id,
                )
            )

            if record is not None:
                record.status = "failed"
                record.error_message = str(error)[:2000]

                db.session.commit()

            raise OfflineSyncError(
                f"Diagnosis synchronization failed: {error}"
            ) from error

        except Exception as error:

            db.session.rollback()

            record = (
                self._get_existing_operation(
                    normalized_operation_id,
                    normalized_user_id,
                )
            )

            if record is not None:
                record.status = "failed"
                record.error_message = (
                    "Synchronization storage failed."
                )

                db.session.commit()

            raise OfflineSyncError(
                "Diagnosis synchronization failed while "
                "storing the synchronization image."
            ) from error

        # =================================================
        # Diagnosis + advisory processing
        # =================================================

        try:

            # Create a separate permanent image for history.
            # The sync image remains available for recovery
            # until diagnosis processing finishes.
            history_image_path = (
                self._create_history_image_copy(
                    source_path=stored_image_path,
                    operation_id=normalized_operation_id,
                )
            )

            result = (
                self._diagnosis_advisory_service
                .diagnose_and_advise(
                    image_path=history_image_path,
                    language=normalized_language,
                    explain=explain,
                    user_id=normalized_user_id,
                )
            )

            diagnosis_id = (
                result
                .get("database", {})
                .get("diagnosis_id")
            )

            # Re-fetch the record after diagnosis processing.
            record = (
                self._get_existing_operation(
                    normalized_operation_id,
                    normalized_user_id,
                )
            )

            if record is None:
                raise OfflineSyncError(
                    "Synchronization record could not "
                    "be found after diagnosis."
                )

            record.diagnosis_id = diagnosis_id
            record.status = "completed"
            record.error_message = None

            db.session.commit()

            # ---------------------------------------------
            # Delete ONLY the temporary synchronization image.
            #
            # Do not delete history_image_path. The diagnosis
            # record uses that permanent image for history.
            # ---------------------------------------------

            SyncStorageService.delete(
                record.image_path
            )

            record.image_path = None

            db.session.commit()

            return self._build_result(
                record,
                result=result,
            )

        # =================================================
        # Known diagnosis/advisory failure
        # =================================================

        except DiagnosisAdvisoryError as error:

            db.session.rollback()

            record = (
                self._get_existing_operation(
                    normalized_operation_id,
                    normalized_user_id,
                )
            )

            if record is not None:
                record.status = "failed"
                record.error_message = str(error)[:2000]

                db.session.commit()

            raise OfflineSyncError(
                f"Diagnosis synchronization failed: {error}"
            ) from error

        # =================================================
        # Known synchronization failure
        # =================================================

        except OfflineSyncError:

            db.session.rollback()

            record = (
                self._get_existing_operation(
                    normalized_operation_id,
                    normalized_user_id,
                )
            )

            if record is not None:
                record.status = "failed"

                if not record.error_message:
                    record.error_message = (
                        "Synchronization operation failed."
                    )

                db.session.commit()

            raise

        # =================================================
        # Unexpected failure
        # =================================================

        except Exception as error:

            db.session.rollback()

            record = (
                self._get_existing_operation(
                    normalized_operation_id,
                    normalized_user_id,
                )
            )

            if record is not None:
                record.status = "failed"
                record.error_message = str(error)[:2000]

                db.session.commit()

            raise OfflineSyncError(
                "An unexpected synchronization error occurred."
            ) from error

    # =====================================================
    # Crash recovery
    # =====================================================

    def recover_processing_operations(
        self,
        user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recover synchronization operations left in processing
        state because the application stopped unexpectedly.

        Only operations with status == "processing" and
        image_path != NULL are eligible for recovery.

        Failed operations continue through the normal
        three-attempt retry mechanism.
        """

        query = OfflineSyncRecord.query.filter_by(
            status="processing"
        )

        if user_id is not None:
            normalized_user_id = (
                self._validate_user_id(
                    user_id
                )
            )

            query = query.filter_by(
                user_id=normalized_user_id
            )

        records = (
            query
            .order_by(
                OfflineSyncRecord.created_at.asc()
            )
            .all()
        )

        results: list[dict[str, Any]] = []

        for record in records:

            # ---------------------------------------------
            # Processing operation must have an image
            # ---------------------------------------------

            if not record.image_path:

                record.status = "failed"
                record.error_message = (
                    "Crash recovery failed because the "
                    "stored synchronization image path is missing."
                )

                db.session.commit()

                results.append(
                    self._build_result(
                        record
                    )
                )

                continue

            image_path = Path(
                record.image_path
            )

            # ---------------------------------------------
            # Verify recovery image exists
            # ---------------------------------------------

            if not image_path.exists():

                record.status = "failed"
                record.error_message = (
                    "Crash recovery failed because the "
                    "stored synchronization image no longer exists."
                )

                db.session.commit()

                results.append(
                    self._build_result(
                        record
                    )
                )

                continue

            # ---------------------------------------------
            # Resume diagnosis using the existing service.
            #
            # Do not increment attempts here. The operation
            # was counted when it entered processing.
            # ---------------------------------------------

            try:

                # Create/reuse a permanent image for history.
                history_image_path = (
                    self._create_history_image_copy(
                        source_path=image_path,
                        operation_id=record.operation_id,
                    )
                )

                result = (
                    self._diagnosis_advisory_service
                    .diagnose_and_advise(
                        image_path=history_image_path,
                        language="en",
                        explain=False,
                        user_id=record.user_id,
                    )
                )

                diagnosis_id = (
                    result
                    .get("database", {})
                    .get("diagnosis_id")
                )

                record.diagnosis_id = diagnosis_id
                record.status = "completed"
                record.error_message = None

                db.session.commit()

                # -----------------------------------------
                # Recovery successful.
                # Remove only the temporary recovery image.
                # Keep the permanent history image.
                # -----------------------------------------

                SyncStorageService.delete(
                    record.image_path
                )

                record.image_path = None

                db.session.commit()

                results.append(
                    self._build_result(
                        record,
                        result=result,
                    )
                )

            except DiagnosisAdvisoryError as error:

                db.session.rollback()

                record = (
                    self._get_existing_operation(
                        record.operation_id,
                        record.user_id,
                    )
                )

                if record is not None:

                    record.status = "failed"
                    record.error_message = (
                        str(error)[:2000]
                    )

                    db.session.commit()

                    results.append(
                        self._build_result(
                            record
                        )
                    )

            except Exception as error:

                db.session.rollback()

                record = (
                    self._get_existing_operation(
                        record.operation_id,
                        record.user_id,
                    )
                )

                if record is not None:

                    record.status = "failed"
                    record.error_message = (
                        str(error)[:2000]
                    )

                    db.session.commit()

                    results.append(
                        self._build_result(
                            record
                        )
                    )

        return results
