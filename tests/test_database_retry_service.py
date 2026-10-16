import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from backend.app.services.database_retry_service import DatabaseRetryService


def test_database_retry_retries_operational_error_three_times(monkeypatch):
    calls = []

    def operation():
        calls.append(1)
        raise OperationalError("SELECT 1", {}, Exception("connection timeout"))

    monkeypatch.setattr(DatabaseRetryService, "RETRY_DELAY_SECONDS", 0)

    with pytest.raises(OperationalError):
        DatabaseRetryService.execute(operation)

    assert len(calls) == 3


def test_database_retry_does_not_retry_integrity_error(monkeypatch):
    calls = []

    def operation():
        calls.append(1)
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    monkeypatch.setattr(DatabaseRetryService, "RETRY_DELAY_SECONDS", 0)

    with pytest.raises(IntegrityError):
        DatabaseRetryService.execute(operation)

    assert len(calls) == 1


def test_database_retry_returns_success_on_first_attempt(monkeypatch):
    calls = []

    def operation():
        calls.append(1)
        return "database operation successful"

    monkeypatch.setattr(DatabaseRetryService, "RETRY_DELAY_SECONDS", 0)

    result = DatabaseRetryService.execute(operation)

    assert result["success"] is True
    assert result["attempts"] == 1
    assert result["result"] == "database operation successful"
    assert len(calls) == 1


def test_database_retry_respects_custom_attempt_limit(monkeypatch):
    calls = []

    def operation():
        calls.append(1)
        raise OperationalError("SELECT 1", {}, Exception("temporary database failure"))

    monkeypatch.setattr(DatabaseRetryService, "RETRY_DELAY_SECONDS", 0)

    with pytest.raises(OperationalError):
        DatabaseRetryService.execute(operation, max_attempts=2)

    assert len(calls) == 2
