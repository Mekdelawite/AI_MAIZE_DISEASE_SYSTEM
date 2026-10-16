"""
=========================================================
Authentication Routes
=========================================================

HTTP API endpoints for user authentication.

Endpoints:
    POST /api/auth/register
    POST /api/auth/login
    GET  /api/auth/me
    GET  /api/auth/health

Authentication:
    JWT Bearer tokens

Roles:
    - farmer
    - extension_agent
    - admin

=========================================================
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from backend.app.services.auth_service import (
    AuthService,
    AuthServiceError,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from backend.app.services.login_attempt_service import (
    LoginAttemptService,
)
from backend.app.services.password_recovery_service import (
    PasswordRecoveryService,
    PasswordRecoveryError,
    PasswordResetCooldownError,
    PasswordResetVerificationError,
    PasswordResetExpiredError,
    PasswordResetAttemptsExceededError,
    PasswordResetDeliveryError,
)

from backend.app.services.registration_otp_service import (
    RegistrationOTPService,
    RegistrationOTPError,
    RegistrationOTPValidationError,
    RegistrationOTPCooldownError,
    RegistrationOTPDeliveryError,
)



# =========================================================
# BLUEPRINT
# =========================================================

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth",
)


# =========================================================
# RESPONSE HELPERS
# =========================================================

def success_response(
    data: Any,
    status_code: int = 200,
):
    """
    Standard successful API response.
    """
    return jsonify(
        {
            "success": True,
            "data": data,
        }
    ), status_code


def error_response(
    code: str,
    message: str,
    status_code: int,
):
    """
    Standard error API response.
    """
    return jsonify(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        }
    ), status_code


# =========================================================
# ROLE DECORATOR
# =========================================================

def roles_required(
    *allowed_roles: str,
) -> Callable:
    """
    Restrict an endpoint to specific JWT roles.

    Usage:

        @jwt_required()
        @roles_required("admin")
        def endpoint():
            ...
    """

    normalized_roles = {
        role.strip().lower()
        for role in allowed_roles
    }

    def decorator(
        function: Callable,
    ) -> Callable:

        @wraps(function)
        def wrapper(
            *args,
            **kwargs,
        ):
            claims = get_jwt()

            role = str(
                claims.get(
                    "role",
                    "",
                )
            ).lower().strip()

            if role not in normalized_roles:
                return error_response(
                    "FORBIDDEN",
                    "You do not have permission "
                    "to access this resource.",
                    403,
                )

            return function(
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


# =========================================================
# REGISTER
# =========================================================


@auth_bp.post("/register")
def register():
    """
    Create a farmer account after phone OTP verification.
    """
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "INVALID_REQUEST",
            "Request body must contain valid JSON.",
            400,
        )

    required_fields = (
        "phone_number",
        "full_name",
        "password",
        "region",
        "woreda",
    )

    missing_fields = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return error_response(
            "VALIDATION_ERROR",
            "Missing required fields: "
            + ", ".join(missing_fields),
            400,
        )

    try:
        user = RegistrationOTPService.complete_registration(
            phone_number=data["phone_number"],
            full_name=data["full_name"],
            password=data["password"],
            preferred_language=data.get(
                "preferred_language", "en"
            ),
            region=data["region"],
            woreda=data["woreda"],
            kebele=data.get("kebele"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            sms_opt_in=data.get("sms_opt_in", False),
        )

    except UserAlreadyExistsError as exc:
        return error_response(
            "USER_ALREADY_EXISTS",
            str(exc),
            409,
        )

    except RegistrationOTPError as exc:
        return error_response(
            "REGISTRATION_NOT_VERIFIED",
            str(exc),
            400,
        )

    except AuthServiceError as exc:
        return error_response(
            "REGISTRATION_ERROR",
            str(exc),
            400,
        )

    # Use the same JWT identity and claims as the login endpoint.
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
            "phone_number": user.phone_number,
            "preferred_language": user.preferred_language,
        },
    )

    return success_response(
        {
            "message": "Registration successful.",
            "access_token": access_token,
            "token_type": "Bearer",
            "user": AuthService.user_to_dict(user),
        },
        201,
    )


# =========================================================
# FARMER REGISTRATION OTP
# =========================================================

@auth_bp.post("/registration-otp/request")
def request_registration_otp():
    """Send an OTP to a phone number before registration."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "INVALID_REQUEST",
            "Request body must contain valid JSON.",
            400,
        )

    phone_number = data.get("phone_number")

    if not phone_number:
        return error_response(
            "VALIDATION_ERROR",
            "Phone number is required.",
            400,
        )

    try:
        result = RegistrationOTPService.request_otp(
            phone_number=phone_number,
        )

        return success_response(
            {
                "message": result["message"],
                "phone_number": result["phone_number"],
                "expires_in_seconds": result["expires_in_seconds"],
                "resend_after_seconds": result["resend_after_seconds"],
            }
        )

    except RegistrationOTPCooldownError as exc:
        return error_response(
            "REGISTRATION_OTP_COOLDOWN",
            str(exc),
            429,
        )

    except RegistrationOTPDeliveryError:
        return error_response(
            "REGISTRATION_OTP_DELIVERY_FAILED",
            "Unable to deliver the registration code. Please try again later.",
            503,
        )

    except RegistrationOTPValidationError as exc:
        return error_response(
            "VALIDATION_ERROR",
            str(exc),
            400,
        )

    except RegistrationOTPError as exc:
        return error_response(
            "REGISTRATION_OTP_ERROR",
            str(exc),
            400,
        )


@auth_bp.post("/registration-otp/verify")
def verify_registration_otp():
    """Verify the OTP before allowing account creation."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "INVALID_REQUEST",
            "Request body must contain valid JSON.",
            400,
        )

    phone_number = data.get("phone_number")
    otp = data.get("otp")

    if not phone_number or not otp:
        return error_response(
            "VALIDATION_ERROR",
            "Phone number and OTP are required.",
            400,
        )

    try:
        result = RegistrationOTPService.verify_otp(
            phone_number=phone_number,
            otp=otp,
        )

        return success_response(
            {
                "message": "Phone number verified successfully.",
                "verified": result["verified"],
                "registration_expires_in_seconds": (
                    result.get("registration_expires_in_seconds", 900)
                ),
            }
        )

    except RegistrationOTPValidationError as exc:
        return error_response(
            "REGISTRATION_OTP_VERIFICATION_FAILED",
            str(exc),
            400,
        )

    except RegistrationOTPError as exc:
        return error_response(
            "REGISTRATION_OTP_ERROR",
            str(exc),
            400,
        )


# =========================================================
# LOGIN
# =========================================================

@auth_bp.post("/login")
def login():
    """
    Authenticate a user and return a JWT access token.

    Expected JSON:

    {
        "phone_number": "+2519XXXXXXXX",
        "password": "password123"
    }
    """

    data = request.get_json(
        silent=True
    )

    if not isinstance(
        data,
        dict,
    ):
        return error_response(
            "INVALID_REQUEST",
            "Request body must contain valid JSON.",
            400,
        )

    phone_number = data.get(
        "phone_number"
    )

    password = data.get(
        "password"
    )
        # -----------------------------------------------------
    # LOGIN ATTEMPT PROTECTION
    # -----------------------------------------------------

    client_ip = request.remote_addr

    locked, remaining_seconds = (
        LoginAttemptService.is_locked(
            phone_number=phone_number,
            client_ip=client_ip,
        )
    )

    if locked:
        minutes = max(
            1,
            (remaining_seconds + 59) // 60,
        )

        return error_response(
            "LOGIN_ATTEMPTS_EXCEEDED",
            (
                "Too many failed login attempts. "
                f"Please try again in {minutes} minute(s) "
                "or reset your password."
            ),
            429,
        )

    # -----------------------------------------------------
    # AUTHENTICATE THROUGH AUTH SERVICE
    # -----------------------------------------------------

    try:
        user = AuthService.authenticate_user(
            phone_number=phone_number,
            password=password,
        )

    except InvalidCredentialsError as error:

        attempt_result = (
            LoginAttemptService.record_failure(
                phone_number=phone_number,
                client_ip=client_ip,
            )
        )

        if attempt_result["locked"]:

            return error_response(
                "LOGIN_ATTEMPTS_EXCEEDED",
                (
                    "Too many failed login attempts. "
                    "Please try again in 5 minutes "
                    "or reset your password."
                ),
                429,
            )

        return error_response(
            "INVALID_CREDENTIALS",
            str(error),
            401,
        )

    except InactiveUserError as error:
        return error_response(
            "ACCOUNT_INACTIVE",
            str(error),
            403,
        )

    except AuthServiceError as error:
        return error_response(
            "LOGIN_ERROR",
            str(error),
            400,
        )
    
    # -----------------------------------------------------
    # CLEAR FAILED ATTEMPTS AFTER SUCCESSFUL LOGIN
    # -----------------------------------------------------

    LoginAttemptService.record_success(
        phone_number=phone_number,
        client_ip=client_ip,
    )

    # -----------------------------------------------------
    # JWT CLAIMS
    # -----------------------------------------------------

    additional_claims = {
        "role": user.role,
        "phone_number": user.phone_number,
        "preferred_language": user.preferred_language,
    }

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims,
    )
    
    # -----------------------------------------------------
    # SUCCESS RESPONSE
    # -----------------------------------------------------

    return success_response(
        {
            "message": "Login successful.",
            "access_token": access_token,
            "token_type": "Bearer",
            "user": AuthService.user_to_dict(
                user
            ),
        }
    )


# =========================================================
# CURRENT USER
# =========================================================

@auth_bp.get("/me")
@jwt_required()
def current_user():
    """
    Return the currently authenticated user.
    """

    identity = get_jwt_identity()

    # -----------------------------------------------------
    # VALIDATE JWT IDENTITY
    # -----------------------------------------------------

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return error_response(
            "INVALID_TOKEN",
            "The token contains an invalid user identity.",
            401,
        )

    # -----------------------------------------------------
    # LOAD USER
    # -----------------------------------------------------

    try:
        user = AuthService.get_user_by_id(
            user_id
        )

        AuthService.ensure_active(
            user
        )

    except UserNotFoundError as error:
        return error_response(
            "USER_NOT_FOUND",
            str(error),
            404,
        )

    except InactiveUserError as error:
        return error_response(
            "ACCOUNT_INACTIVE",
            str(error),
            403,
        )

    # -----------------------------------------------------
    # SUCCESS RESPONSE
    # -----------------------------------------------------

    return success_response(
        {
            "user": AuthService.user_to_dict(
                user
            ),
        }
    )


# =========================================================
# AUTHENTICATION HEALTH
# =========================================================

@auth_bp.get("/health")
def auth_health():
    """
    Authentication subsystem health endpoint.
    """

    return success_response(
        {
            "service": "authentication",
            "status": "ready",
            "supported_roles": list(
                AuthService.SUPPORTED_ROLES
            ),
            "supported_languages": list(
                AuthService.SUPPORTED_LANGUAGES
            ),
        }
    )
@auth_bp.post("/password-reset/request")
def request_password_reset():
    """
    Request a password reset OTP.

    The response is intentionally generic for unknown or
    inactive phone numbers to prevent account enumeration.
    """
    data = request.get_json(silent=True) or {}

    phone_number = data.get("phone_number")

    if not phone_number:
        return error_response(
            "VALIDATION_ERROR",
            "Phone number is required.",
            400,
        )

    try:
        result = PasswordRecoveryService.request_password_reset(
            phone_number=phone_number,
        )

        response_data = {
            "message": result["message"],
        }

        if "expires_in_minutes" in result:
            response_data["expires_in_minutes"] = (
                result["expires_in_minutes"]
            )

        return success_response(response_data, 200)

    except PasswordResetCooldownError as exc:
        return error_response(
            "PASSWORD_RESET_COOLDOWN",
            str(exc),
            429,
        )

    except PasswordResetDeliveryError:
        return error_response(
            "PASSWORD_RESET_DELIVERY_FAILED",
            "Unable to deliver the password reset code.",
            503,
        )

    except PasswordRecoveryError:
        return error_response(
            "PASSWORD_RESET_ERROR",
            "Unable to process the password reset request.",
            400,
        )


@auth_bp.post("/password-reset/confirm")
def confirm_password_reset():
    """
    Confirm a password reset using the OTP.
    """
    data = request.get_json(silent=True) or {}

    phone_number = data.get("phone_number")
    otp = data.get("otp")
    new_password = data.get("new_password")

    if not phone_number or not otp or not new_password:
        return error_response(
            "VALIDATION_ERROR",
            "Phone number, OTP, and new password are required.",
            400,
        )

    try:
        result = PasswordRecoveryService.confirm_password_reset(
            phone_number=phone_number,
            otp=otp,
            new_password=new_password,
        )

        response_data = {
          "message": "Password reset successfully.",
                        } 

        return success_response(response_data, 200)


    except PasswordResetAttemptsExceededError as exc:
        return error_response(
            "PASSWORD_RESET_ATTEMPTS_EXCEEDED",
            str(exc),
            429,
        )

    except PasswordResetExpiredError as exc:
        return error_response(
            "PASSWORD_RESET_EXPIRED",
            str(exc),
            400,
        )

    except PasswordResetVerificationError as exc:
        return error_response(
            "PASSWORD_RESET_VERIFICATION_FAILED",
            str(exc),
            400,
        )

    except PasswordRecoveryError as exc:
        return error_response(
            "PASSWORD_RESET_ERROR",
            str(exc),
            400,
        )