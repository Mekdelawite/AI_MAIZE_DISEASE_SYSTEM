from backend.app.main import app
from backend.app.models import OfflineSyncRecord
from backend.app.services.offline_sync_service import (
    OfflineSyncService,
    OfflineSyncError,
)


OPERATION_ID = "offline-test-001"

OWNER_USER_ID = 1
ATTACKER_USER_ID = 2

IMAGE_PATH = "ml_model/inference/test_images/sample.jpg"


with app.app_context():

    service = OfflineSyncService()

    record = (
        OfflineSyncRecord.query
        .filter_by(operation_id=OPERATION_ID)
        .first()
    )

    print(
        "EXISTING OPERATION:",
        record.operation_id if record else None,
    )

    print(
        "OWNER USER ID:",
        record.user_id if record else None,
    )

    print(
        "ATTACKER USER ID:",
        ATTACKER_USER_ID,
    )

    try:

        result = service.synchronize_diagnosis(
            operation_id=OPERATION_ID,
            user_id=ATTACKER_USER_ID,
            image_path=IMAGE_PATH,
            language="en",
        )

        print(
            "SECURITY FAILURE:",
            result,
        )

    except OfflineSyncError as error:

        print(
            "SECURITY TEST RESULT:",
            str(error),
        )

    final_record = (
        OfflineSyncRecord.query
        .filter_by(operation_id=OPERATION_ID)
        .first()
    )

    print(
        "FINAL OWNER USER ID:",
        final_record.user_id
        if final_record
        else None,
    )

    print(
        "FINAL STATUS:",
        final_record.status
        if final_record
        else None,
    )

    print(
        "FINAL ATTEMPTS:",
        final_record.attempts
        if final_record
        else None,
    )