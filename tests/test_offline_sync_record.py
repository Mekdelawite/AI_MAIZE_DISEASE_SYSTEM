import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models import OfflineSyncRecord, User


def create_user(database):
    user = User(
        phone_number="0900000201",
        full_name="Offline Test Farmer",
        password_hash="test-hash",
        role="farmer",
        preferred_language="en",
    )
    database.session.add(user)
    database.session.commit()
    return user


def test_offline_sync_record_persists(database):
    user = create_user(database)

    record = OfflineSyncRecord(
        operation_id="offline-op-001",
        user_id=user.id,
        operation_type="diagnosis",
        status="pending",
        image_path="uploads/offline-op-001.jpg",
        diagnosis_id=None,
        error_message=None,
        attempts=0,
    )

    database.session.add(record)
    database.session.commit()

    saved = database.session.get(OfflineSyncRecord, record.id)

    assert saved is not None
    assert saved.operation_id == "offline-op-001"
    assert saved.user_id == user.id
    assert saved.operation_type == "diagnosis"
    assert saved.status == "pending"
    assert saved.attempts == 0
    assert saved.created_at is not None
    assert saved.updated_at is not None


def test_offline_sync_operation_id_must_be_unique(database):
    user = create_user(database)

    first = OfflineSyncRecord(
        operation_id="offline-op-unique",
        user_id=user.id,
        operation_type="diagnosis",
        status="pending",
        attempts=0,
    )
    database.session.add(first)
    database.session.commit()

    duplicate = OfflineSyncRecord(
        operation_id="offline-op-unique",
        user_id=user.id,
        operation_type="diagnosis",
        status="pending",
        attempts=0,
    )
    database.session.add(duplicate)

    with pytest.raises(IntegrityError):
        database.session.commit()

    database.session.rollback()


def test_offline_sync_record_can_store_failure_and_retry_state(database):
    user = create_user(database)

    record = OfflineSyncRecord(
        operation_id="offline-op-failed",
        user_id=user.id,
        operation_type="diagnosis",
        status="failed",
        error_message="Temporary processing failure",
        attempts=2,
    )

    database.session.add(record)
    database.session.commit()

    saved = database.session.get(OfflineSyncRecord, record.id)

    assert saved.status == "failed"
    assert saved.error_message == "Temporary processing failure"
    assert saved.attempts == 2
