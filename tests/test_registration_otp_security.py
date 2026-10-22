import pytest
from flask import Flask

from backend.app.services.registration_otp_service import (
    RegistrationOTPError,
    RegistrationOTPService,
)


@pytest.mark.parametrize(
    "secret",
    [None, "", "   ", "dev-change-this-jwt-secret-key", "too-short"],
)
def test_hash_otp_rejects_missing_or_weak_secret(secret):
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = secret

    with app.app_context(), pytest.raises(
        RegistrationOTPError,
        match="OTP verification is not configured securely",
    ):
        RegistrationOTPService._hash_otp("123456")


def test_hash_otp_accepts_configured_secret():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "a" * 32

    with app.app_context():
        result = RegistrationOTPService._hash_otp("123456")

    assert len(result) == 64
    assert result != "123456"
