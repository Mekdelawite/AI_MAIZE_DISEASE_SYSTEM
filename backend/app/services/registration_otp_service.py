
"""Secure OTP verification for new farmer registrations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import re


from flask import current_app
from sqlalchemy import func

from backend.app.extensions import db
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.extension_agent_activation import ExtensionAgentActivation
from backend.app.models.pending_registration import PendingRegistration
from backend.app.models.user import User
from backend.app.services.auth_service import (
    AuthService,
    AuthServiceError,
    UserAlreadyExistsError,
)
from backend.app.services.email_service import EmailService
from backend.app.services.sms_service import SMSService
from html import escape

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
    ACTIVATION_RESENDS_PER_HOUR = 5
    ACTIVATION_SESSION_MINUTES = 15

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
            raise UserAlreadyExistsError(
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
            raise UserAlreadyExistsError(
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


    @classmethod
    def send_extension_agent_activation_code(
        cls,
        user_id: int,
    ) -> dict:
        """Create and deliver an activation code to a pending extension agent."""
        activation = (
            ExtensionAgentActivation.query
            .filter_by(user_id=user_id)
            .with_for_update()
            .first()
        )
        agent = db.session.get(ExtensionAgent, user_id)
        user = db.session.get(User, user_id)

        if (
            activation is None
            or agent is None
            or user is None
            or agent.account_status != "pending_activation"
            or not agent.professional_info_verified
            or user.is_active
        ):
            raise RegistrationOTPValidationError(
                "This extension-agent account is not eligible for activation."
            )

        now = cls._now()

        if activation.last_sent_at:
            last_sent = activation.last_sent_at
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)

            elapsed = (now - last_sent).total_seconds()
            if elapsed < cls.RESEND_COOLDOWN_SECONDS:
                raise RegistrationOTPCooldownError(
                    f"Please wait {max(1, int(cls.RESEND_COOLDOWN_SECONDS - elapsed))} "
                    "seconds before requesting another code."
                )

        window_start = activation.resend_window_started_at
        if window_start and window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=timezone.utc)

        if window_start is None or now - window_start >= timedelta(hours=1):
            activation.resend_window_started_at = now
            activation.resend_count = 0
        elif activation.resend_count >= cls.ACTIVATION_RESENDS_PER_HOUR:
            remaining = max(
                1,
                int((window_start + timedelta(hours=1) - now).total_seconds()),
            )
            raise RegistrationOTPCooldownError(
                f"Too many activation codes were sent. Try again in {remaining} seconds."
            )

        code = cls._generate_otp()
        activation.otp_hash = cls._hash_otp(code)
        activation.otp_expires_at = now + timedelta(
            minutes=cls.OTP_EXPIRES_MINUTES
        )
        activation.attempts = 0
        activation.max_attempts = cls.MAX_ATTEMPTS
        activation.last_sent_at = now
        activation.resend_count += 1
        activation.activation_token_hash = None
        activation.activation_token_expires_at = None

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise RegistrationOTPError(
                "Could not prepare the activation code."
            ) from exc

        activation_url = (
            current_app.config.get(
                "ACTIVATION_FRONTEND_URL",
                "http://localhost:5173",
            ).strip().rstrip("/")
            + "/activate-extension-agent"
        )

        try:
            if activation.verification_method == "email":
                EmailService.send_email(
                    recipient=agent.email or "",
                    subject="MaizeCare extension-agent account activation",
                    message=(
                        f"Your MaizeCare extension-agent activation code is {code}.\n\n"
                        f"Open this link to activate your account:\n"
                        f"{activation_url}\n\n"
                        f"The code expires in {cls.OTP_EXPIRES_MINUTES} minutes.\n"
                        "Do not share this code with anyone."
                    ),
                    html_message=(
                        "<html><body>"
                        "<h2>MaizeCare Extension Agent Activation</h2>"
                        "<p>Your activation code is:</p>"
                        f"<h2>{escape(code)}</h2>"
                        "<p>Open the following link to activate your account:</p>"
                        f'<p><a href="{escape(activation_url, quote=True)}">'
                        "Activate Extension Agent Account</a></p>"
                        f"<p>Your code expires in {cls.OTP_EXPIRES_MINUTES} minutes.</p>"
                        "<p>Do not share this code with anyone.</p>"
                        "</body></html>"
                    ),
                )

            elif activation.verification_method == "sms":
                result = SMSService.send_sms(
                    user.phone_number,
                    (
                        f"MaizeCare extension-agent activation code is {code}. "
                        f"Expires in {cls.OTP_EXPIRES_MINUTES} minutes. "
                        f"Activate: {activation_url}. "
                        "Do not share this code."
                    ),
                    recipient_type="extension_agent",
                    notification_type="extension_agent_activation",
                    language=user.preferred_language,
                    user_id=user.id,
                    redact_message=True,
                )

                if not result.get("success"):
                    raise RegistrationOTPDeliveryError(
                        "The SMS provider did not accept the activation code."
                    )

            else:
                raise RegistrationOTPError(
                    "The selected activation method is not supported."
                )

        except RegistrationOTPError:
            raise
        except Exception as exc:
            raise RegistrationOTPDeliveryError(
                "Unable to deliver the activation code. An administrator can resend it."
            ) from exc

        return {
            "expires_in_seconds": cls.OTP_EXPIRES_MINUTES * 60,
            "resend_after_seconds": cls.RESEND_COOLDOWN_SECONDS,
        }


    @classmethod
    def verify_extension_agent_activation_code(
        cls,
        *,
        contact: str,
        code: str,
    ) -> dict:
        """Verify an agent code once and issue a short-lived activation capability."""
        if not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
            raise RegistrationOTPValidationError(
                "Enter the six-digit verification code."
            )
        agent, user = cls._get_agent_by_contact(contact, lock=True)
        if agent is None or user is None:
            raise RegistrationOTPValidationError(
                "The activation details are invalid or expired."
            )
        activation = (
            ExtensionAgentActivation.query
            .filter_by(user_id=user.id)
            .with_for_update()
            .first()
        )
        if (
            activation is None
            or not activation.otp_hash
            or agent.account_status != "pending_activation"
            or user.is_active
            or not agent.professional_info_verified
        ):
            raise RegistrationOTPValidationError(
                "The activation details are invalid or expired."
            )
        submitted_contact_is_email = "@" in contact.strip()
        if (
            activation.verification_method == "email"
            and not submitted_contact_is_email
        ) or (
            activation.verification_method == "sms"
            and submitted_contact_is_email
        ):
            raise RegistrationOTPValidationError(
                "Use the contact method selected by the administrator."
            )

        now = cls._now()
        expires_at = activation.otp_expires_at
        if expires_at is None:
            raise RegistrationOTPValidationError(
                "Request a new activation code from the administrator."
            )
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now >= expires_at:
            activation.otp_hash = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "The activation code has expired. Ask the administrator to resend it."
            )
        if activation.attempts >= activation.max_attempts:
            activation.otp_hash = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "Too many incorrect attempts. Ask the administrator to resend the code."
            )

        supplied_hash = cls._hash_otp(code)
        if not hmac.compare_digest(supplied_hash, activation.otp_hash):
            activation.attempts += 1
            if activation.attempts >= activation.max_attempts:
                activation.otp_hash = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "The activation code is incorrect."
            )

        activation_token = secrets.token_urlsafe(32)
        activation.otp_hash = None
        activation.otp_expires_at = None
        activation.activation_token_hash = cls._hash_otp(activation_token)
        activation.activation_token_expires_at = now + timedelta(
            minutes=cls.ACTIVATION_SESSION_MINUTES
        )
        db.session.commit()
        return {
            "activation_token": activation_token,
            "expires_in_seconds": cls.ACTIVATION_SESSION_MINUTES * 60,
        }

    @classmethod
    def complete_extension_agent_activation(
        cls,
        *,
        activation_token: str,
        password: str,
    ) -> None:
        """Set the agent's password and atomically activate the account."""
        if not isinstance(activation_token, str) or not activation_token:
            raise RegistrationOTPValidationError(
                "Verify the activation code before setting a password."
            )
        password = AuthService.validate_password(password)
        activation_hash = cls._hash_otp(activation_token)
        activation = (
            ExtensionAgentActivation.query
            .filter_by(activation_token_hash=activation_hash)
            .with_for_update()
            .first()
        )
        if activation is None:
            raise RegistrationOTPValidationError(
                "The activation session is invalid or expired."
            )

        agent = db.session.get(ExtensionAgent, activation.user_id)
        user = db.session.get(User, activation.user_id)
        expires_at = activation.activation_token_expires_at
        now = cls._now()
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if (
            agent is None
            or user is None
            or expires_at is None
            or now >= expires_at
            or agent.account_status != "pending_activation"
            or user.is_active
            or not agent.professional_info_verified
            or not agent.woreda_id
        ):
            activation.activation_token_hash = None
            activation.activation_token_expires_at = None
            db.session.commit()
            raise RegistrationOTPValidationError(
                "The activation session is invalid or expired."
            )

        try:
            user.set_password(password)
            user.is_active = True
            agent.account_status = "active"
            activation.activation_token_hash = None
            activation.activation_token_expires_at = None
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def _get_agent_by_contact(
        cls,
        contact: str,
        *,
        lock: bool = False,
    ) -> tuple[ExtensionAgent | None, User | None]:
        if not isinstance(contact, str) or not contact.strip():
            return None, None
        normalized = contact.strip()
        query = (
            ExtensionAgent.query
            .join(User, ExtensionAgent.user_id == User.id)
        )
        if "@" in normalized:
            query = query.filter(func.lower(ExtensionAgent.email) == normalized.lower())
        else:
            try:
                phone = AuthService.normalize_phone(normalized)
            except AuthServiceError:
                return None, None
            possible_formats = {phone, "0" + phone[4:], phone[1:]}
            query = query.filter(User.phone_number.in_(possible_formats))
        if lock:
            query = query.with_for_update()
        agent = query.first()
        return (agent, agent.user) if agent else (None, None)
