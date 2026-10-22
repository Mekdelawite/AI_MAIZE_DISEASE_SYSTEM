
"""Secure OTP verification for new farmer registrations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import re

from flask import current_app

from backend.app.extensions import db
from backend.app.models.pending_registration import PendingRegistration
from backend.app.services.auth_service import AuthService
from backend.app.services.sms_service import SMSService


class RegistrationOTPError(Exception):
    """Base registration OTP error."""


class RegistrationOTPValidationError(RegistrationOTPError):
    """Invalid phone number or verification code."""


class RegistrationOTPCooldownError(RegistrationOTPError):
    """OTP resend cooldown is active."""


class RegistrationOTPDeliveryError(RegistrationOTPError):
    """OTP delivery failed."""


class RegistrationOTPService:
    OTP_EXPIRES_MINUTES = 5
    RESEND_COOLDOWN_SECONDS = 60
    MAX_ATTEMPTS = 5
    REGISTRATION_VALID_MINUTES = 15

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def normalize_phone(phone_number: str) -> str:
        """Validate and normalize Ethiopian mobile numbers."""
        if not isinstance(phone_number, str):
            raise RegistrationOTPValidationError(
                "Enter a valid Ethiopian mobile number."
            )

        phone = re.sub(r"[\s\-()]", "", phone_number)

        if phone.startswith("09") and len(phone) == 10:
            phone = "+251" + phone[1:]
        elif phone.startswith("251") and len(phone) == 12:
            phone = "+" + phone

        # This flow is intentionally limited to Ethiopian mobile numbers.
        if not re.fullmatch(r"\+2519\d{8}", phone):
            raise RegistrationOTPValidationError(
                "Use an Ethiopian mobile number, such as 0911998877."
            )

        return phone

    @staticmethod
    def _hash_otp(otp: str) -> str:
        """Hash an OTP using the application's secret."""
        secret = current_app.config.get("JWT_SECRET_KEY")

        if (
            not isinstance(secret, str)
            or secret.strip() in {"", "dev-change-this-jwt-secret-key"}
            or len(secret.encode("utf-8")) < 32
        ):
            raise RegistrationOTPError(
                "OTP verification is not configured securely."
            )

        return hmac.new(
            secret.encode("utf-8"),
            otp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _generate_otp() -> str:
        return str(secrets.randbelow(1_000_000)).zfill(6)

    @classmethod
    def request_otp(cls, phone_number: str) -> dict:
        """Create a pending registration and send a verification code."""
        phone = cls.normalize_phone(phone_number)

        # Check canonical format first. Existing accounts might historically
        # contain local-format numbers, so check common equivalent formats too.
        possible_formats = {
            phone,
            "0" + phone[4:],
            phone[1:],
        }

        from backend.app.models.user import User

        existing_user = User.query.filter(
            User.phone_number.in_(possible_formats)
        ).first()

        if existing_user:
            raise RegistrationOTPValidationError(
                "An account already exists for this phone number. Please log in."
            )

        now = cls._now()
        record = PendingRegistration.query.filter_by(
            phone_number=phone
        ).with_for_update().first()

        if record and record.last_sent_at:
            last_sent = record.last_sent_at
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)

            elapsed = (now - last_sent).total_seconds()
            if elapsed < cls.RESEND_COOLDOWN_SECONDS:
                remaining = max(
                    1,
                    int(cls.RESEND_COOLDOWN_SECONDS - elapsed),
                )
                raise RegistrationOTPCooldownError(
                    f"Please wait {remaining} seconds before requesting another code."
                )

        otp = cls._generate_otp()
        otp_hash = cls._hash_otp(otp)

        if record is None:
            record = PendingRegistration(phone_number=phone)
            db.session.add(record)

        # Commit the new OTP state before calling SMSService, which commits
        # its own SMS history record using the same SQLAlchemy session.
        record.otp_hash = otp_hash
        record.otp_expires_at = now + timedelta(
            minutes=cls.OTP_EXPIRES_MINUTES
        )
        record.attempts = 0
        record.max_attempts = cls.MAX_ATTEMPTS
        record.last_sent_at = now
        record.verified_at = None
        record.registration_expires_at = None

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise RegistrationOTPError(
                "Could not prepare phone verification. Please try again."
            ) from exc

        message = (
            f"Your MaizeCare registration code is {otp}. "
            f"It expires in {cls.OTP_EXPIRES_MINUTES} minutes. "
            "Do not share this code with anyone."
        )

        try:
            sms_result = SMSService.send_sms(
                phone,
                message,
                recipient_type="farmer",
                notification_type="registration_otp",
                language="en",
            )
        except Exception as exc:
            db.session.rollback()
            raise RegistrationOTPDeliveryError(
                "Unable to send the verification code. Please try again later."
            ) from exc

        if not sms_result.get("success"):
            raise RegistrationOTPDeliveryError(
                "The SMS provider did not accept the verification message. Please try again later."
            )

        return {
            "phone_number": phone,
            "expires_in_seconds": cls.OTP_EXPIRES_MINUTES * 60,
            "resend_after_seconds": cls.RESEND_COOLDOWN_SECONDS,
            "message": "Verification code submitted for delivery.",
        }

    @classmethod
    def verify_otp(cls, phone_number: str, otp: str) -> dict:
        """Verify the code and mark the pending registration as verified."""
        phone = cls.normalize_phone(phone_number)

        if not isinstance(otp, str) or not re.fullmatch(r"\d{6}", otp):
            raise RegistrationOTPValidationError(
                "Enter the six-digit verification code."
            )

        record = PendingRegistration.query.filter_by(
            phone_number=phone
        ).with_for_update().first()

        if record is None or not record.otp_hash:
            raise RegistrationOTPValidationError(
                "Request a new verification code first."
            )

        now = cls._now()
        expires_at = record.otp_expires_at

        if expires_at is None:
            raise RegistrationOTPValidationError(
                "Request a new verification code first."
            )

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now >= expires_at:
            record.otp_hash = None
            record.verified_at = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "The verification code has expired. Request a new code."
            )

        if record.attempts >= record.max_attempts:
            record.otp_hash = None
            record.verified_at = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "Too many incorrect attempts. Request a new code."
            )

        supplied_hash = cls._hash_otp(otp)

        if not hmac.compare_digest(supplied_hash, record.otp_hash):
            record.attempts += 1

            if record.attempts >= record.max_attempts:
                record.otp_hash = None
                record.verified_at = None

            db.session.commit()
            raise RegistrationOTPValidationError(
                "The verification code is incorrect."
            )

        record.verified_at = now
        record.registration_expires_at = now + timedelta(
            minutes=cls.REGISTRATION_VALID_MINUTES
        )

        # Make the code single-use after successful verification.
        record.otp_hash = None
        db.session.commit()

        return {
            "phone_number": phone,
            "verified": True,
            "registration_expires_in_seconds": (
                cls.REGISTRATION_VALID_MINUTES * 60
            ),
            "message": "Phone verified. You can complete registration.",
        }

    @classmethod
    def complete_registration(
        cls,
        *,
        phone_number: str,
        full_name: str,
        password: str,
        preferred_language: str = "en",
        region: str | None = None,
        woreda: str | None = None,
        kebele: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        sms_opt_in: bool = False,
    ):
        """Create a farmer account only after phone verification."""
        from backend.app.models.user import User

        phone = cls.normalize_phone(phone_number)

        record = PendingRegistration.query.filter_by(
            phone_number=phone
        ).with_for_update().first()

        if record is None or record.verified_at is None:
            raise RegistrationOTPValidationError(
                "Verify your phone number before completing registration."
            )

        now = cls._now()
        verified_at = record.verified_at
        expires_at = record.registration_expires_at

        if verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=timezone.utc)

        if expires_at is None:
            raise RegistrationOTPValidationError(
                "Phone verification has expired. Verify your phone again."
            )

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now >= expires_at:
            record.verified_at = None
            record.registration_expires_at = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "Phone verification has expired. Request a new code."
            )

        if now - verified_at > timedelta(
            minutes=cls.REGISTRATION_VALID_MINUTES
        ):
            record.verified_at = None
            record.registration_expires_at = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "Phone verification has expired. Request a new code."
            )

        # Re-check immediately before account creation.
        existing_user = User.query.filter_by(
            phone_number=phone
        ).first()

        if existing_user:
            raise RegistrationOTPValidationError(
                "An account already exists for this phone number. Please log in."
            )

        try:
            user = AuthService.register_user(
                phone_number=phone,
                full_name=full_name,
                password=password,
                preferred_language=preferred_language,
                role="farmer",
                region=region,
                woreda=woreda,
                kebele=kebele,
                latitude=latitude,
                longitude=longitude,
                sms_opt_in=sms_opt_in,
            )

            db.session.delete(record)
            db.session.commit()
            return user

        except Exception:
            db.session.rollback()
            raise
