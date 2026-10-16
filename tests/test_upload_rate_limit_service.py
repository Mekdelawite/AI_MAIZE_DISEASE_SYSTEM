from backend.app.services.upload_rate_limit_service import UploadRateLimitService


def test_upload_rate_limit_allows_first_ten_uploads():
    UploadRateLimitService.clear_all()
    user_id = 1001

    assert UploadRateLimitService.MAX_UPLOADS == 10
    assert UploadRateLimitService.WINDOW_SECONDS == 60

    for i in range(10):
        result = UploadRateLimitService.check_and_record(user_id)
        assert result["allowed"] is True
        assert result["current_count"] == i + 1

    blocked = UploadRateLimitService.check_and_record(user_id)

    assert blocked["allowed"] is False
    assert blocked["current_count"] == 10
    assert blocked["remaining"] == 0
    assert blocked["retry_after_seconds"] >= 1

    UploadRateLimitService.clear_all()


def test_upload_rate_limit_supports_multiple_uploads_in_one_request():
    UploadRateLimitService.clear_all()
    user_id = 1002

    result = UploadRateLimitService.check_and_record(user_id, upload_count=5)

    assert result["allowed"] is True
    assert result["current_count"] == 5
    assert result["remaining"] == 5

    result = UploadRateLimitService.check_and_record(user_id, upload_count=5)

    assert result["allowed"] is True
    assert result["current_count"] == 10
    assert result["remaining"] == 0

    blocked = UploadRateLimitService.check_and_record(user_id, upload_count=1)

    assert blocked["allowed"] is False
    assert blocked["current_count"] == 10
    assert blocked["remaining"] == 0

    UploadRateLimitService.clear_all()


def test_upload_rate_limit_is_separate_per_user():
    UploadRateLimitService.clear_all()
    user_a = 1003
    user_b = 1004

    for _ in range(10):
        result = UploadRateLimitService.check_and_record(user_a)
        assert result["allowed"] is True

    blocked_a = UploadRateLimitService.check_and_record(user_a)
    allowed_b = UploadRateLimitService.check_and_record(user_b)

    assert blocked_a["allowed"] is False
    assert allowed_b["allowed"] is True
    assert allowed_b["current_count"] == 1

    UploadRateLimitService.clear_all()
