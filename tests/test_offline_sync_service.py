import pytest
from backend.app.models import DiagnosisRecord, OfflineSyncRecord, User
from backend.app.services.offline_sync_service import OfflineSyncError, OfflineSyncService


def create_user(database, phone):
    user = User(phone_number=phone, full_name="Offline Sync Test Farmer", password_hash="test-hash", role="farmer", preferred_language="en")
    database.session.add(user)
    database.session.commit()
    return user


def create_diagnosis(database, user_id):
    diagnosis = DiagnosisRecord(
        user_id=user_id,
        image_filename="offline_test_leaf.jpg",
        image_path="uploads/offline_test_leaf.jpg",
        disease_class="Blight",
        confidence=0.90,
        model_name="MobileNetV2",
        model_version="test",
        prediction_time=0.2,
        explainability_requested=False,
    )
    database.session.add(diagnosis)
    database.session.commit()
    return diagnosis


def create_record(database, user_id, operation_id, status, attempts=0, diagnosis_id=None):
    record = OfflineSyncRecord(operation_id=operation_id, user_id=user_id, operation_type="diagnosis", status=status, attempts=attempts, diagnosis_id=diagnosis_id)
    database.session.add(record)
    database.session.commit()
    return record


def test_completed_operation_returns_existing_result_without_processing(database, tmp_path, monkeypatch):
    user = create_user(database, "0900000301")
    diagnosis = create_diagnosis(database, user.id)
    record = create_record(database, user.id, "completed-op-001", "completed", attempts=1, diagnosis_id=diagnosis.id)
    image_path = tmp_path / "unused.jpg"
    image_path.write_bytes(b"test image")
    service = OfflineSyncService()

    def unexpected_processing(**kwargs):
        pytest.fail("Completed operations must not run diagnosis again.")

    monkeypatch.setattr(service._diagnosis_advisory_service, "diagnose_and_advise", unexpected_processing)
    result = service.synchronize_diagnosis(record.operation_id, "diagnosis", user.id, image_path)
    assert result["operation_id"] == "completed-op-001"
    assert result["status"] == "completed"
    assert result["diagnosis_id"] == diagnosis.id
    assert result["attempts"] == 1


def test_operation_cannot_be_accessed_by_another_user(database, tmp_path):
    owner = create_user(database, "0900000302")
    other_user = create_user(database, "0900000303")
    diagnosis = create_diagnosis(database, owner.id)
    create_record(database, owner.id, "owned-op-001", "completed", attempts=1, diagnosis_id=diagnosis.id)
    image_path = tmp_path / "ownership.jpg"
    image_path.write_bytes(b"test image")
    service = OfflineSyncService()

    with pytest.raises(OfflineSyncError, match="does not belong"):
        service.synchronize_diagnosis("owned-op-001", "diagnosis", other_user.id, image_path)


def test_operation_at_maximum_attempts_is_rejected(database, tmp_path):
    user = create_user(database, "0900000304")
    create_record(database, user.id, "max-attempts-op", "failed", attempts=OfflineSyncService.MAX_ATTEMPTS)
    image_path = tmp_path / "retry.jpg"
    image_path.write_bytes(b"test image")
    service = OfflineSyncService()

    with pytest.raises(OfflineSyncError, match="Maximum synchronization attempts"):
        service.synchronize_diagnosis("max-attempts-op", "diagnosis", user.id, image_path)


def test_operation_already_processing_is_rejected(database, tmp_path):
    user = create_user(database, "0900000305")
    create_record(database, user.id, "processing-op", "processing", attempts=1)
    image_path = tmp_path / "processing.jpg"
    image_path.write_bytes(b"test image")
    service = OfflineSyncService()

    with pytest.raises(OfflineSyncError, match="already being processed"):
        service.synchronize_diagnosis("processing-op", "diagnosis", user.id, image_path)



def test_recovery_marks_operation_failed_when_image_path_is_missing(database):
    user = create_user(database, "0900000311")
    record = create_record(database, user.id, "recovery-no-path", "processing", attempts=1)
    results = OfflineSyncService().recover_processing_operations(user_id=user.id)
    database.session.refresh(record)
    assert record.status == "failed"
    assert "image path is missing" in record.error_message.lower()
    assert any(item.get("operation_id") == record.operation_id for item in results)


def test_recovery_marks_operation_failed_when_image_file_is_missing(database):
    user = create_user(database, "0900000312")
    record = create_record(database, user.id, "recovery-missing-file", "processing", attempts=1)
    record.image_path = "uploads/nonexistent_recovery_image.jpg"
    database.session.commit()
    results = OfflineSyncService().recover_processing_operations(user_id=user.id)
    database.session.refresh(record)
    assert record.status == "failed"
    assert "no longer exists" in record.error_message.lower()
    assert any(item.get("operation_id") == record.operation_id for item in results)


def test_recovery_processes_existing_image_successfully(database, tmp_path, monkeypatch):
    user = create_user(database, "0900000313")
    image_path = tmp_path / "recoverable_leaf.jpg"
    image_path.write_bytes(b"test image")
    record = create_record(database, user.id, "recovery-success", "processing", attempts=1)
    record.image_path = str(image_path)
    database.session.commit()
    service = OfflineSyncService()

    def fake_diagnose_and_advise(**kwargs):
        assert kwargs["user_id"] == user.id
        return {"database": {"diagnosis_id": None}, "status": "completed"}

    monkeypatch.setattr(service._diagnosis_advisory_service, "diagnose_and_advise", fake_diagnose_and_advise)
    results = service.recover_processing_operations(user_id=user.id)
    database.session.refresh(record)
    assert record.status == "completed"
    assert record.image_path is None
    assert not image_path.exists()
    assert any(item.get("operation_id") == record.operation_id and item.get("status") == "completed" for item in results)


def test_recovery_filters_by_user_id(database):
    user_one = create_user(database, "0900000314")
    user_two = create_user(database, "0900000315")
    record_one = create_record(database, user_one.id, "recovery-user-one", "processing", attempts=1)
    record_two = create_record(database, user_two.id, "recovery-user-two", "processing", attempts=1)
    results = OfflineSyncService().recover_processing_operations(user_id=user_one.id)
    database.session.refresh(record_one)
    database.session.refresh(record_two)
    assert record_one.status == "failed"
    assert record_two.status == "processing"
    assert all(item.get("operation_id") != record_two.operation_id for item in results)
