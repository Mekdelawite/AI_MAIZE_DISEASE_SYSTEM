from backend.app.services.login_attempt_service import LoginAttemptService


def test_login_attempt_limit_and_lockout():
    LoginAttemptService.clear_all()
    phone = "0900000020"
    client_ip = "127.0.0.1"

    assert LoginAttemptService.MAX_ATTEMPTS == 5
    assert LoginAttemptService.LOCKOUT_MINUTES == 5

    locked, attempts = LoginAttemptService.is_locked(phone, client_ip)
    assert locked is False
    assert attempts == 0

    for _ in range(4):
        result = LoginAttemptService.record_failure(phone, client_ip)
        assert result["locked"] is False

    result = LoginAttemptService.record_failure(phone, client_ip)
    assert result["locked"] is True

    locked, attempts = LoginAttemptService.is_locked(phone, client_ip)
    assert locked is True
    assert attempts >= LoginAttemptService.MAX_ATTEMPTS


def test_success_clears_failed_attempts():
    LoginAttemptService.clear_all()
    phone = "0900000021"
    client_ip = "127.0.0.1"

    first_failure = LoginAttemptService.record_failure(phone, client_ip)
    second_failure = LoginAttemptService.record_failure(phone, client_ip)

    assert first_failure["attempts"] == 1
    assert second_failure["attempts"] == 2
    assert first_failure["locked"] is False
    assert second_failure["locked"] is False

    locked, remaining_seconds = LoginAttemptService.is_locked(phone, client_ip)
    assert locked is False
    assert remaining_seconds == 0

    LoginAttemptService.record_success(phone, client_ip)

    locked, remaining_seconds = LoginAttemptService.is_locked(phone, client_ip)
    assert locked is False
    assert remaining_seconds == 0
