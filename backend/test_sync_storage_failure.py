"""
=========================================================
Offline Sync Storage Failure Test
=========================================================

Verifies that a permanently stored synchronization image
survives when diagnosis processing fails.

This test does not create a diagnosis record.
=========================================================
"""

from pathlib import Path

from backend.app.main import create_app
from backend.app.extensions import db
from backend.app.models import OfflineSyncRecord
from backend.app.services.offline_sync_service import (
    OfflineSyncError,
    OfflineSyncService,
)
from backend.app.services.diagnosis_advisory_service import (
    DiagnosisAdvisoryError,
)


OPERATION_ID = "crash-recovery-failure-001"

IMAGE_PATH = Path(
    "ml_model/inference/test_images/sample.jpg"
)


class ForcedFailureService:
    """
    Replaces the real diagnosis/advisory service only for
    this test so we can verify storage behavior.
    """

    def diagnose_and_advise(
        self,
        image_path,
        language,
        explain,
        user_id,
    ):
        print(
            "IMAGE RECEIVED BY DIAGNOSIS:",
            image_path,
        )

        print(
            "IMAGE EXISTS:",
            Path(image_path).exists(),
        )

        raise DiagnosisAdvisoryError(
            "CONTROLLED TEST FAILURE"
        )


app = create_app()


with app.app_context():

    # -----------------------------------------------------
    # Clean previous test record if it exists
    # -----------------------------------------------------

    old_record = (
        OfflineSyncRecord.query
        .filter_by(
            operation_id=OPERATION_ID
        )
        .first()
    )

    if old_record is not None:

        if old_record.image_path:

            stored_file = Path(
                old_record.image_path
            )

            if stored_file.exists():
                stored_file.unlink()

        db.session.delete(old_record)
        db.session.commit()

    # -----------------------------------------------------
    # Create service
    # -----------------------------------------------------

    service = OfflineSyncService()

    # Replace only the diagnosis implementation for this
    # controlled failure test.
    service._diagnosis_advisory_service = (
        ForcedFailureService()
    )

    # -----------------------------------------------------
    # Run synchronization
    # -----------------------------------------------------

    try:

        service.synchronize_diagnosis(
            operation_id=OPERATION_ID,
            operation_type="diagnosis",
            user_id=1,
            image_path=IMAGE_PATH,
            language="en",
            explain=False,
        )

    except OfflineSyncError as error:

        print(
            "EXPECTED ERROR:",
            error,
        )

    # -----------------------------------------------------
    # Reload synchronization record
    # -----------------------------------------------------

    record = (
        OfflineSyncRecord.query
        .filter_by(
            operation_id=OPERATION_ID
        )
        .first()
    )

    if record is None:
        raise RuntimeError(
            "TEST FAILED: synchronization record was not created."
        )

    print(
        "STATUS:",
        record.status,
    )

    print(
        "ATTEMPTS:",
        record.attempts,
    )

    print(
        "DIAGNOSIS_ID:",
        record.diagnosis_id,
    )

    print(
        "IMAGE_PATH:",
        record.image_path,
    )

    # -----------------------------------------------------
    # Verify permanent image survived failure
    # -----------------------------------------------------

    if record.status != "failed":
        raise RuntimeError(
            "TEST FAILED: expected status=failed."
        )

    if record.attempts != 1:
        raise RuntimeError(
            "TEST FAILED: expected attempts=1."
        )

    if record.diagnosis_id is not None:
        raise RuntimeError(
            "TEST FAILED: diagnosis_id should be NULL."
        )

    if not record.image_path:
        raise RuntimeError(
            "TEST FAILED: image_path was not stored."
        )

    stored_image = Path(
        record.image_path
    )

    if not stored_image.exists():
        raise RuntimeError(
            "TEST FAILED: permanent image does not exist."
        )

    print(
        "STORED IMAGE EXISTS: True"
    )

    print(
        "CRASH-RECOVERY STORAGE TEST PASSED"
    )