from backend.app.main import app
from backend.app.extensions import db
from backend.app.models import OfflineSyncRecord, DiagnosisRecord
from backend.app.services.offline_sync_service import (
    OfflineSyncService,
    OfflineSyncError,
)
from backend.app.services.diagnosis_advisory_service import (
    DiagnosisAdvisoryError,
)


OPERATION_ID = "retry-test-001"
IMAGE_PATH = "ml_model/inference/test_images/sample.jpg"
USER_ID = 1


with app.app_context():

    service = OfflineSyncService()

    def forced_failure(**kwargs):
        raise DiagnosisAdvisoryError(
            "TEST FAILURE FOR RETRY"
        )

    service._diagnosis_advisory_service.diagnose_and_advise = (
        forced_failure
    )

    print(
        "DIAGNOSES BEFORE:",
        DiagnosisRecord.query.count(),
    )

    for attempt in range(1, 5):

        try:

            result = service.synchronize_diagnosis(
                operation_id=OPERATION_ID,
                user_id=USER_ID,
                image_path=IMAGE_PATH,
                language="en",
            )

            print(
                f"ATTEMPT {attempt}:",
                result,
            )

        except OfflineSyncError as error:

            print(
                f"ATTEMPT {attempt} ERROR:",
                str(error),
            )

    record = (
        OfflineSyncRecord.query
        .filter_by(
            operation_id=OPERATION_ID
        )
        .first()
    )

    print(
        "FINAL STATUS:",
        record.status if record else None,
    )

    print(
        "FINAL ATTEMPTS:",
        record.attempts if record else None,
    )

    print(
        "FINAL ERROR:",
        record.error_message if record else None,
    )

    print(
        "DIAGNOSES AFTER:",
        DiagnosisRecord.query.count(),
    )