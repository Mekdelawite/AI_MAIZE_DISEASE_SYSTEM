"""
=========================================================
SMS Routes
=========================================================

API endpoints for SMS notifications.

Authentication:
    JWT Bearer token

Authorized roles:
    - extension_agent
    - admin

The routes are intentionally thin:
    - authenticate the request
    - validate request data
    - obtain the authenticated user
    - call SMSService
    - return JSON response

Africa's Talking communication remains inside
sms_service.py.

=========================================================
"""

from __future__ import annotations

from typing import Any

from flask import (
    Blueprint,
    jsonify,
    request,
)

from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from backend.app.services.auth_service import (
    AuthService,
    AuthServiceError,
    InactiveUserError,
    UserNotFoundError,
)

from backend.app.services.sms_service import SMSService
from backend.app.services.sms_retry_service import SMSRetryService


# =========================================================
# BLUEPRINT
# =========================================================

sms_bp = Blueprint(
    "sms",
    __name__,
    url_prefix="/api/sms",
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
# ROLE AUTHORIZATION
# =========================================================

def sms_roles_required(
    *allowed_roles: str,
):
    """
    Restrict SMS endpoints to specific JWT roles.
    """

    allowed = {
        role.strip().lower()
        for role in allowed_roles
    }

    def decorator(function):

        def wrapper(*args, **kwargs):

            claims = get_jwt()

            role = str(
                claims.get(
                    "role",
                    "",
                )
            ).strip().lower()

            if role not in allowed:

                return error_response(
                    "FORBIDDEN",
                    "You do not have permission "
                    "to send SMS notifications.",
                    403,
                )

            return function(
                *args,
                **kwargs,
            )

        wrapper.__name__ = function.__name__

        return wrapper

    return decorator


# =========================================================
# CURRENT AUTHENTICATED USER
# =========================================================

def get_authenticated_user():
    """
    Retrieve and validate the authenticated user.

    The user ID comes from the JWT identity rather than
    from the request body.
    """

    identity = get_jwt_identity()

    try:

        user = AuthService.get_user_by_id(
            int(identity)
        )

        AuthService.ensure_active(
            user
        )

        return user, None

    except UserNotFoundError as error:

        return None, error_response(
            "USER_NOT_FOUND",
            str(error),
            404,
        )

    except InactiveUserError as error:

        return None, error_response(
            "ACCOUNT_INACTIVE",
            str(error),
            403,
        )

    except (
        ValueError,
        TypeError,
    ):

        return None, error_response(
            "INVALID_TOKEN_IDENTITY",
            "Invalid user identity in token.",
            401,
        )


# =========================================================
# SEND GENERAL SMS
# =========================================================

@sms_bp.post("/send")
@jwt_required()
@sms_roles_required(
    "admin",
    "extension_agent",
)
def send_sms():
    """
    Send a general SMS notification.

    Expected JSON:

    {
        "recipient_phone": "+2519XXXXXXXX",
        "message": "Test message",
        "recipient_type": "farmer",
        "notification_type": "general",
        "language": "en",
        "region": "Amhara",
        "woreda": "Bahir Dar Zuria",
        "kebele": "Example"
    }
    """

    user, error = get_authenticated_user()

    if error:
        return error

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

    recipient_phone = data.get(
        "recipient_phone"
    )

    message = data.get(
        "message"
    )

    if not recipient_phone:

        return error_response(
            "MISSING_PHONE",
            "Recipient phone number is required.",
            400,
        )

    if not message:

        return error_response(
            "MISSING_MESSAGE",
            "SMS message is required.",
            400,
        )

    try:

        result = SMSService.send_sms(
            recipient_phone=recipient_phone,
            message=message,
            recipient_type=data.get(
                "recipient_type",
                "farmer",
            ),
            notification_type=data.get(
                "notification_type",
                "general",
            ),
            language=data.get(
                "language",
                user.preferred_language,
            ),
            user_id=user.id,
            region=data.get(
                "region"
            ),
            woreda=data.get(
                "woreda"
            ),
            kebele=data.get(
                "kebele"
            ),
        )

    except ValueError as error:

        return error_response(
            "INVALID_SMS_REQUEST",
            str(error),
            400,
        )

    except RuntimeError as error:

        return error_response(
            "SMS_CONFIGURATION_ERROR",
            str(error),
            500,
        )

    except Exception as error:

        print(
            "SMS route error:",
            error,
        )

        return error_response(
            "SMS_ERROR",
            "Failed to process SMS request.",
            500,
        )

    if not result.get("success"):

        return error_response(
            "SMS_SEND_FAILED",
            result.get(
                "error",
                "SMS sending failed.",
            ),
            502,
        )

    return success_response(
        result
    )


# =========================================================
# SEND DISEASE ALERT
# =========================================================

@sms_bp.post("/disease-alert")
@jwt_required()
@sms_roles_required(
    "admin",
    "extension_agent",
)
def send_disease_alert():
    """
    Send a maize disease alert.
    """

    user, error = get_authenticated_user()

    if error:
        return error

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

    recipient_phone = data.get(
        "recipient_phone"
    )

    disease_name = data.get(
        "disease_name"
    )

    confidence = data.get(
        "confidence"
    )

    if not recipient_phone:

        return error_response(
            "MISSING_PHONE",
            "Recipient phone number is required.",
            400,
        )

    if not disease_name:

        return error_response(
            "MISSING_DISEASE",
            "Disease name is required.",
            400,
        )

    if confidence is None:

        return error_response(
            "MISSING_CONFIDENCE",
            "Confidence is required.",
            400,
        )

    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError,
    ):

        return error_response(
            "INVALID_CONFIDENCE",
            "Confidence must be a number.",
            400,
        )

    if not 0 <= confidence <= 100:

        return error_response(
            "INVALID_CONFIDENCE",
            "Confidence must be between 0 and 100.",
            400,
        )

    try:

        result = SMSService.send_disease_alert(
            recipient_phone=recipient_phone,
            disease_name=disease_name,
            confidence=confidence,
            language=data.get(
                "language",
                user.preferred_language,
            ),
            user_id=user.id,
            region=data.get(
                "region"
            ),
            woreda=data.get(
                "woreda"
            ),
            kebele=data.get(
                "kebele"
            ),
        )

    except Exception as error:

        print(
            "Disease alert error:",
            error,
        )

        return error_response(
            "SMS_ERROR",
            "Failed to process disease alert.",
            500,
        )

    if not result.get("success"):

        return error_response(
            "SMS_SEND_FAILED",
            result.get(
                "error",
                "Disease alert could not be sent.",
            ),
            502,
        )

    return success_response(
        result
    )


# =========================================================
# SEND OUTBREAK ALERT
# =========================================================

@sms_bp.post("/outbreak-alert")
@jwt_required()
@sms_roles_required(
    "admin",
    "extension_agent",
)
def send_outbreak_alert():
    """
    Send a disease outbreak alert.
    """

    user, error = get_authenticated_user()

    if error:
        return error

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

    recipient_phone = data.get(
        "recipient_phone"
    )

    disease_name = data.get(
        "disease_name"
    )

    location = data.get(
        "location"
    )

    if not recipient_phone:

        return error_response(
            "MISSING_PHONE",
            "Recipient phone number is required.",
            400,
        )

    if not disease_name:

        return error_response(
            "MISSING_DISEASE",
            "Disease name is required.",
            400,
        )

    if not location:

        return error_response(
            "MISSING_LOCATION",
            "Location is required.",
            400,
        )

    try:

        result = SMSService.send_outbreak_alert(
            recipient_phone=recipient_phone,
            disease_name=disease_name,
            location=location,
            language=data.get(
                "language",
                user.preferred_language,
            ),
            user_id=user.id,
            region=data.get(
                "region"
            ),
            woreda=data.get(
                "woreda"
            ),
            kebele=data.get(
                "kebele"
            ),
        )

    except Exception as error:

        print(
            "Outbreak alert error:",
            error,
        )

        return error_response(
            "SMS_ERROR",
            "Failed to process outbreak alert.",
            500,
        )

    if not result.get("success"):

        return error_response(
            "SMS_SEND_FAILED",
            result.get(
                "error",
                "Outbreak alert could not be sent.",
            ),
            502,
        )

    return success_response(
        result
    )
# =========================================================
# RETRY FAILED SMS
# =========================================================

@sms_bp.post("/retry")
@jwt_required()
@sms_roles_required(
    "admin",
    "extension_agent",
)
def retry_sms():
    """
    Retry a failed SMS notification.

    Expected JSON:

    {
        "sms_record_id": 123,
        "max_retries": 1
    }

    Only failed SMS records can be retried.

    The original SMSRecord is preserved and every retry
    submission creates a new SMSRecord.
    """

    user, error = get_authenticated_user()

    if error:
        return error

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

    sms_record_id = data.get(
        "sms_record_id"
    )

    if sms_record_id is None:

        return error_response(
            "MISSING_SMS_RECORD_ID",
            "SMS record ID is required.",
            400,
        )

    max_retries = data.get(
        "max_retries",
        SMSRetryService.MAX_RETRIES,
    )

    try:

        result = SMSRetryService.retry_sms(
            sms_record_id=sms_record_id,
            max_retries=max_retries,
        )

    except ValueError as error:

        return error_response(
            "INVALID_SMS_RETRY_REQUEST",
            str(error),
            400,
        )

    except Exception as error:

        print(
            "SMS retry route error:",
            error,
        )

        return error_response(
            "SMS_RETRY_ERROR",
            "Failed to process SMS retry request.",
            500,
        )

    if not result.get(
        "success"
    ):

        return error_response(
            "SMS_RETRY_FAILED",
            result.get(
                "last_result",
                {}
            ).get(
                "error",
                "SMS retry failed.",
            ),
            502,
        )

    return success_response(
        result
    )