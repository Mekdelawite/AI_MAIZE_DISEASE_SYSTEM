
"""
Password Recovery Service

Handles password-reset OTP generation, verification,
expiration, cooldown, and password updates.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from flask import current_app

from backend.app.extensions import db
from backend.app.models.password_reset_otp import PasswordResetOTP
from backend.app.models.user import User
from backend.app.services.auth_service import AuthService
from backend.app.services.sms_service import SMSService


# =========================================================
# EXCEPTIONS
# =========================================================

class PasswordRecoveryError(Exception):
    """Base password recovery error."""


class PasswordResetCooldownError(PasswordRecoveryError):
    """Raised when a new OTP is requested too soon."""


class PasswordResetVerificationError(PasswordRecoveryError):
    """Raised when OTP verification fails."""


class PasswordResetExpiredError(PasswordRecoveryError):
    """Raised when an OTP has expired."""


class PasswordResetAttemptsExceededError(PasswordRecoveryError):
    """Raised when too many OTP attempts are made."""


class PasswordResetDeliveryError(PasswordRecoveryError):
    """Raised when OTP SMS delivery fails."""


# =========================================================
# PASSWORD RECOVERY SERVICE
# =========================================================

class PasswordRecoveryService:
    """Service responsible for password-reset operations."""

    # -----------------------------------------------------
    # PHONE NUMBER LOOKUP
    # -----------------------------------------------------

    @staticmethod
    def _find_user_by_phone(phone_number: str) -> User | None:
        """
        Find an account using either the supplied phone format
        or the equivalent Ethiopian local/international format.

        Existing database values are not modified.
        """

        normalized_phone = AuthService.normalize_phone(
            phone_number
        )

        user = AuthService.get_user_by_phone(
            normalized_phone
        )

        if user is not None:
            return user

        # Ethiopian local format: 09XXXXXXXX
        # International format: +2519XXXXXXXX
        if normalized_phone.startswith("+251"):
            local_phone = "0" + normalized_phone[4:]

            return AuthService.get_user_by_phone(
                local_phone
            )

        # Support local-format input when the database contains
        # the equivalent international-format number.
        if (
            normalized_phone.startswith("0")
            and len(normalized_phone) == 10
        ):
            international_phone = (
                "+251" + normalized_phone[1:]
            )

            return AuthService.get_user_by_phone(
                international_phone
            )

        return None

    # -----------------------------------------------------
    # OTP GENERATION
    # -----------------------------------------------------

    @staticmethod
    def _generate_otp() -> str:
        """Generate a cryptographically secure numeric OTP."""

        length = int(
            current_app.config.get(
                "PASSWORD_RESET_OTP_LENGTH",
                6,
            )
        )

        if length < 4:
            length = 6

        upper_bound = 10 ** length

        return str(
            secrets.randbelow(upper_bound)
        ).zfill(length)

    # -----------------------------------------------------
    # OTP HASHING
    # -----------------------------------------------------

    @staticmethod
    def _hash_otp(otp: str) -> str:
        """Hash the OTP before database storage."""

        secret = str(
            current_app.config.get(
                "JWT_SECRET_KEY",
                "",
            )
        )

        return hmac.new(
            secret.encode("utf-8"),
            otp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def _verify_otp(
        cls,
        otp: str,
        stored_hash: str,
    ) -> bool:
        """Safely compare the supplied OTP with its hash."""

        calculated_hash = cls._hash_otp(otp)

        return hmac.compare_digest(
            calculated_hash,
            stored_hash,
        )

    # -----------------------------------------------------
    # INVALIDATE PREVIOUS OTPS
    # -----------------------------------------------------

    @staticmethod
    def _invalidate_previous_otps(user_id: int) -> None:
        """Invalidate all previous unused OTPs for a user."""

        active_otps = (
            PasswordResetOTP.query
            .filter(
                PasswordResetOTP.user_id == user_id,
                PasswordResetOTP.used_at.is_(None),
            )
            .all()
        )

        now = datetime.now(timezone.utc)

        for otp_record in active_otps:
            otp_record.used_at = now

    # -----------------------------------------------------
    # REQUEST COOLDOWN
    # -----------------------------------------------------

    @staticmethod
    def _check_cooldown(user_id: int) -> None:
        """Prevent repeated OTP requests within the cooldown."""

        cooldown_seconds = int(
            current_app.config.get(
                "PASSWORD_RESET_COOLDOWN_SECONDS",
                60,
            )
        )

        latest_otp = (
            PasswordResetOTP.query
            .filter_by(user_id=user_id)
            .order_by(
                PasswordResetOTP.created_at.desc()
            )
            .first()
        )

        if latest_otp is None:
            return

        now = datetime.now(timezone.utc)
        created_at = latest_otp.created_at

        # Handle databases returning naive datetime values.
        if created_at.tzinfo is None:
            created_at = created_at.replace(
                tzinfo=timezone.utc
            )

        elapsed = (now - created_at).total_seconds()

        if elapsed < cooldown_seconds:
            remaining = max(
                1,
                int(cooldown_seconds - elapsed),
            )

            raise PasswordResetCooldownError(
                f"Please wait {remaining} seconds before "
                "requesting another OTP."
            )

    # -----------------------------------------------------
    # CREATE OTP RECORD
    # -----------------------------------------------------

    @classmethod
    def _create_otp_record(
        cls,
        user: User,
    ) -> tuple[PasswordResetOTP, str]:
        """Generate and persist a new OTP record."""

        cls._check_cooldown(user.id)

        cls._invalidate_previous_otps(user.id)

        otp = cls._generate_otp()
        otp_hash = cls._hash_otp(otp)

        expires_minutes = int(
            current_app.config.get(
                "PASSWORD_RESET_OTP_EXPIRES_MINUTES",
                5,
            )
        )

        max_attempts = int(
            current_app.config.get(
                "PASSWORD_RESET_MAX_ATTEMPTS",
                5,
            )
        )

        now = datetime.now(timezone.utc)

        otp_record = PasswordResetOTP(
            user_id=user.id,
            otp_hash=otp_hash,
            expires_at=(
                now
                + timedelta(minutes=expires_minutes)
            ),
            attempts=0,
            max_attempts=max_attempts,
        )

        db.session.add(otp_record)
        db.session.flush()

        return otp_record, otp

    # -----------------------------------------------------
    # GENERIC RESPONSE
    # -----------------------------------------------------

    @staticmethod
    def _generic_reset_message() -> str:
        """Prevent account enumeration."""

        return (
            "If an account exists for this "
            "phone number, a password reset "
            "code has been sent."
        )

    # -----------------------------------------------------
    # REQUEST PASSWORD RESET
    # -----------------------------------------------------

    @classmethod
    def request_password_reset(
        cls,
        phone_number: str,
    ) -> dict:
        """Request a password-reset OTP."""

        phone_number = AuthService.normalize_phone(
            phone_number
        )

        user = cls._find_user_by_phone(
            phone_number
        )

        generic_message = cls._generic_reset_message()

        if user is None or not user.is_active:
            return {
                "success": True,
                "message": generic_message,
                "user_found": False,
            }

        try:
            otp_record, otp = cls._create_otp_record(
                user
            )

            language = (
                user.preferred_language
                or current_app.config.get(
                    "DEFAULT_LANGUAGE",
                    "en",
                )
            )

            expires_minutes = int(
                current_app.config.get(
                    "PASSWORD_RESET_OTP_EXPIRES_MINUTES",
                    5,
                )
            )

            if language == "am":
                message = (
                    "AI Maize Disease System: "
                    f"የይለፍ ቃል መቀየሪያ ኮድዎ "
                    f"{otp} ነው። "
                    f"ኮዱ ለ{expires_minutes} ደቂቃ "
                    "ብቻ ይሰራል።"
                )
            else:
                message = (
                    "AI Maize Disease System: "
                    f"Your password reset code is "
                    f"{otp}. This code expires in "
                    f"{expires_minutes} minutes."
                )

            profile = user.farmer_profile

            sms_result = SMSService.send_sms(
                user.phone_number,
                message,
                recipient_type=user.role,
                notification_type="password_reset",
                language=language,
                user_id=user.id,
                region=(
                    profile.region
                    if profile
                    else None
                ),
                woreda=(
                    profile.woreda
                    if profile
                    else None
                ),
                kebele=(
                    profile.kebele
                    if profile
                    else None
                ),
            )

            if not sms_result.get("success", False):
                # Invalidate the OTP if SMS delivery failed.
                otp_record.mark_used()
                db.session.commit()

                raise PasswordResetDeliveryError(
                    "Unable to deliver the password "
                    "reset code."
                )

            db.session.commit()

            return {
                "success": True,
                "message": generic_message,
                "user_found": True,
                "expires_in_minutes": expires_minutes,
                "sms_record_id": sms_result.get(
                    "sms_record_id"
                ),
            }

        except PasswordRecoveryError:
            db.session.rollback()
            raise

        except Exception as error:
            db.session.rollback()

            raise PasswordRecoveryError(
                "Failed to request password reset."
            ) from error

    # -----------------------------------------------------
    # CONFIRM PASSWORD RESET
    # -----------------------------------------------------

    @classmethod
    def confirm_password_reset(
        cls,
        phone_number: str,
        otp: str,
        new_password: str,
    ) -> User:
        """Verify the OTP and update the user's password."""

        phone_number = AuthService.normalize_phone(
            phone_number
        )

        if not isinstance(otp, str):
            raise PasswordResetVerificationError(
                "Invalid verification code."
            )

        otp = otp.strip()

        expected_length = int(
            current_app.config.get(
                "PASSWORD_RESET_OTP_LENGTH",
                6,
            )
        )

        if (
            len(otp) != expected_length
            or not otp.isdigit()
        ):
            raise PasswordResetVerificationError(
                "Invalid verification code."
            )

        try:
            new_password = AuthService.validate_password(
                new_password
            )
        except Exception as error:
            raise PasswordRecoveryError(
                str(error)
            ) from error

        user = cls._find_user_by_phone(
            phone_number
        )

        if user is None or not user.is_active:
            raise PasswordResetVerificationError(
                "Invalid verification code."
            )

        otp_record = (
            PasswordResetOTP.query
            .filter(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.used_at.is_(None),
            )
            .order_by(
                PasswordResetOTP.created_at.desc()
            )
            .first()
        )

        if otp_record is None:
            raise PasswordResetVerificationError(
                "Invalid or expired verification code."
            )

        if otp_record.is_expired:
            otp_record.mark_used()
            db.session.commit()

            raise PasswordResetExpiredError(
                "The verification code has expired."
            )

        if otp_record.attempts_exceeded:
            otp_record.mark_used()
            db.session.commit()

            raise PasswordResetAttemptsExceededError(
                "Too many verification attempts."
            )

        if not cls._verify_otp(
            otp,
            otp_record.otp_hash,
        ):
            otp_record.attempts += 1

            attempts_exceeded = (
                otp_record.attempts
                >= otp_record.max_attempts
            )

            if attempts_exceeded:
                otp_record.mark_used()

            db.session.commit()

            if attempts_exceeded:
                raise PasswordResetAttemptsExceededError(
                    "Too many verification attempts."
                )

            raise PasswordResetVerificationError(
                "Invalid verification code."
            )

        user.set_password(new_password)
        otp_record.mark_used()

        try:
            db.session.commit()
        except Exception as error:
            db.session.rollback()

            raise PasswordRecoveryError(
                "Failed to update password."
            ) from error

        return user
