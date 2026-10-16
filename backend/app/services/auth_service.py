
"""
=========================================================
Authentication Service
=========================================================

Handles application authentication logic.

Responsibilities:
    - User registration
    - Password hashing
    - Password verification
    - User login validation
    - User lookup
    - Account status validation
    - Role validation
    - Farmer location/profile creation

JWT token creation is handled by the authentication route
using Flask-JWT-Extended.

Supported roles:
    - farmer
    - extension_agent
    - admin

Supported languages:
    - en
    - am
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.extensions import db
from backend.app.models.user import User


# =========================================================
# EXCEPTIONS
# =========================================================

class AuthServiceError(Exception):
    """Base authentication service error."""


class UserAlreadyExistsError(AuthServiceError):
    """Raised when a phone number is already registered."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials are invalid."""


class UserNotFoundError(AuthServiceError):
    """Raised when a requested user does not exist."""


class InactiveUserError(AuthServiceError):
    """Raised when an inactive account attempts to authenticate."""


# =========================================================
# SERVICE
# =========================================================

class AuthService:
    """
    Application authentication service.

    This class contains authentication business logic
    and database operations.

    It does not handle HTTP requests or JWT transport.
    """

    SUPPORTED_ROLES = (
        "farmer",
        "extension_agent",
        "admin",
    )

    SUPPORTED_LANGUAGES = (
        "en",
        "am",
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    
    @staticmethod
    def normalize_phone(
        phone_number: str,
    ) -> str:
        """
        Normalize Ethiopian mobile numbers to +251 format.
        Existing database records are not modified.
        """

        if not isinstance(phone_number, str):
            raise AuthServiceError(
                "Phone number must be a string."
            )

        phone = phone_number.strip()

        if not phone:
            raise AuthServiceError(
                "Phone number is required."
            )

        # Remove common formatting characters.
        for char in (" ", "-", "(", ")", "."):
            phone = phone.replace(char, "")

        # Convert common Ethiopian mobile formats.
        if phone.startswith("09") and len(phone) == 10:
            phone = "+251" + phone[1:]

        elif phone.startswith("9") and len(phone) == 9:
            phone = "+251" + phone

        elif phone.startswith("00251"):
            phone = "+" + phone[2:]

        # Validate the canonical Ethiopian mobile format.
        if (
            len(phone) != 13
            or not phone.startswith("+2519")
            or not phone[1:].isdigit()
        ):
            raise AuthServiceError(
                "Enter a valid Ethiopian mobile number, "
                "such as 0910112233 or +251910112233."
            )

        return phone

    # =====================================================
    # FULL NAME
    # =====================================================

    @staticmethod
    def validate_full_name(
        full_name: str,
    ) -> str:
        """
        Validate and normalize the user's full name.
        """

        if not isinstance(
            full_name,
            str,
        ):
            raise AuthServiceError(
                "Full name must be a string."
            )

        full_name = full_name.strip()

        if not full_name:
            raise AuthServiceError(
                "Full name is required."
            )

        if len(full_name) > 150:
            raise AuthServiceError(
                "Full name is too long."
            )

        return full_name

    # =====================================================
    # ROLE
    # =====================================================

    @classmethod
    def validate_role(
        cls,
        role: str,
    ) -> str:
        """
        Validate a user role.

        Public registration should normally create
        farmers only. Administrative role creation should
        be handled separately.
        """

        if not isinstance(
            role,
            str,
        ):
            raise AuthServiceError(
                "Role must be a string."
            )

        role = role.strip().lower()

        if role not in cls.SUPPORTED_ROLES:
            raise AuthServiceError(
                f"Unsupported role: {role}. "
                f"Supported roles: "
                f"{list(cls.SUPPORTED_ROLES)}"
            )

        return role

    # =====================================================
    # LANGUAGE
    # =====================================================

    @classmethod
    def validate_language(
        cls,
        language: str,
    ) -> str:
        """
        Validate the preferred language.
        """

        if not isinstance(
            language,
            str,
        ):
            raise AuthServiceError(
                "Language must be a string."
            )

        language = language.strip().lower()

        if language not in cls.SUPPORTED_LANGUAGES:
            raise AuthServiceError(
                f"Unsupported language: {language}. "
                f"Supported languages: "
                f"{list(cls.SUPPORTED_LANGUAGES)}"
            )

        return language

    # =====================================================
    # PASSWORD
    # =====================================================

    @staticmethod
    def validate_password(
        password: str,
    ) -> str:
        """
        Validate a user password.

        Minimum length is eight characters.
        """

        if not isinstance(
            password,
            str,
        ):
            raise AuthServiceError(
                "Password must be a string."
            )

        if not password:
            raise AuthServiceError(
                "Password is required."
            )

        if len(password) < 8:
            raise AuthServiceError(
                "Password must contain at least "
                "8 characters."
            )

        return password

    # =====================================================
    # FARMER PROFILE VALIDATION
    # =====================================================

    @staticmethod
    def validate_region(
        region: str,
    ) -> str:
        """
        Validate and normalize farmer region.
        """

        if not isinstance(
            region,
            str,
        ):
            raise AuthServiceError(
                "Region must be a string."
            )

        region = region.strip()

        if not region:
            raise AuthServiceError(
                "Region is required for farmer registration."
            )

        if len(region) > 50:
            raise AuthServiceError(
                "Region is too long."
            )

        return region

    @staticmethod
    def validate_woreda(
        woreda: str,
    ) -> str:
        """
        Validate and normalize farmer woreda.
        """

        if not isinstance(
            woreda,
            str,
        ):
            raise AuthServiceError(
                "Woreda must be a string."
            )

        woreda = woreda.strip()

        if not woreda:
            raise AuthServiceError(
                "Woreda is required for farmer registration."
            )

        if len(woreda) > 50:
            raise AuthServiceError(
                "Woreda is too long."
            )

        return woreda

    @staticmethod
    def validate_kebele(
        kebele: str | None,
    ) -> str | None:
        """
        Validate and normalize farmer kebele.

        Kebele is optional.
        """

        if kebele is None:
            return None

        if not isinstance(
            kebele,
            str,
        ):
            raise AuthServiceError(
                "Kebele must be a string or null."
            )

        kebele = kebele.strip()

        if not kebele:
            return None

        if len(kebele) > 50:
            raise AuthServiceError(
                "Kebele is too long."
            )

        return kebele

    @staticmethod
    def validate_latitude(
        latitude: float | int | str | None,
    ) -> float | None:
        """
        Validate farmer latitude.

        Valid range:
            -90 to 90

        Latitude is optional.
        """

        if latitude is None:
            return None

        try:
            latitude = float(latitude)

        except (TypeError, ValueError) as error:
            raise AuthServiceError(
                "Latitude must be a valid number or null."
            ) from error

        if not -90 <= latitude <= 90:
            raise AuthServiceError(
                "Latitude must be between -90 and 90."
            )

        return latitude

    @staticmethod
    def validate_longitude(
        longitude: float | int | str | None,
    ) -> float | None:
        """
        Validate farmer longitude.

        Valid range:
            -180 to 180

        Longitude is optional.
        """

        if longitude is None:
            return None

        try:
            longitude = float(longitude)

        except (TypeError, ValueError) as error:
            raise AuthServiceError(
                "Longitude must be a valid number or null."
            ) from error

        if not -180 <= longitude <= 180:
            raise AuthServiceError(
                "Longitude must be between -180 and 180."
            )

        return longitude

    @staticmethod
    def validate_sms_opt_in(
        sms_opt_in: bool,
    ) -> bool:
        """
        Validate farmer SMS notification preference.
        """

        if not isinstance(
            sms_opt_in,
            bool,
        ):
            raise AuthServiceError(
                "sms_opt_in must be true or false."
            )

        return sms_opt_in

    # =====================================================
    # USER LOOKUP
    # =====================================================

    @staticmethod
    def get_user_by_id(
        user_id: int,
    ) -> User:
        """
        Retrieve a user by database ID.
        """

        try:
            user_id = int(user_id)

        except (
            TypeError,
            ValueError,
        ) as error:

            raise UserNotFoundError(
                "Invalid user ID."
            ) from error

        user = db.session.get(
            User,
            user_id,
        )

        if user is None:
            raise UserNotFoundError(
                "User not found."
            )

        return user

    
    @classmethod
    def get_user_by_phone(
        cls,
        phone_number: str,
    ) -> User | None:
        """
        Retrieve a user by phone number, supporting both
        canonical international and legacy local formats.
        """

        phone = cls.normalize_phone(phone_number)

        # First, search using the canonical format.
        user = User.query.filter_by(
            phone_number=phone
        ).first()

        if user is not None:
            return user

        # Fall back to the legacy Ethiopian local format.
        local_phone = "0" + phone[4:]

        return User.query.filter_by(
            phone_number=local_phone
        ).first()

    # =====================================================
    # REGISTRATION
    # =====================================================

    @classmethod
    def register_user(
        cls,
        phone_number: str,
        full_name: str,
        password: str,
        preferred_language: str = "en",
        role: str = "farmer",
        region: str | None = None,
        woreda: str | None = None,
        kebele: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        sms_opt_in: bool = False,
    ) -> User:
        """
        Register a new user.

        Public registration is restricted to farmers.

        Farmers must provide:
            - region
            - woreda

        Optional farmer profile information:
            - kebele
            - latitude
            - longitude
            - sms_opt_in

        A FarmerProfile is automatically created for the
        newly registered farmer.

        Extension-agent and admin accounts must be created
        through controlled administrative procedures.
        """

        # =================================================
        # BASIC USER VALIDATION
        # =================================================

        phone_number = cls.normalize_phone(
            phone_number
        )

        full_name = cls.validate_full_name(
            full_name
        )

        password = cls.validate_password(
            password
        )

        preferred_language = cls.validate_language(
            preferred_language
        )

        role = cls.validate_role(
            role
        )

        # =================================================
        # PUBLIC REGISTRATION SECURITY
        # =================================================

        if role != "farmer":

            raise AuthServiceError(
                "Public registration is only available "
                "for the farmer role."
            )

        # =================================================
        # FARMER PROFILE VALIDATION
        # =================================================

        region = cls.validate_region(
            region
        )

        woreda = cls.validate_woreda(
            woreda
        )

        kebele = cls.validate_kebele(
            kebele
        )

        latitude = cls.validate_latitude(
            latitude
        )

        longitude = cls.validate_longitude(
            longitude
        )

        sms_opt_in = cls.validate_sms_opt_in(
            sms_opt_in
        )

        # =================================================
        # DUPLICATE CHECK
        # =================================================

        existing_user = cls.get_user_by_phone(
            phone_number
        )

        if existing_user is not None:

            raise UserAlreadyExistsError(
                "A user with this phone number "
                "already exists."
            )

        # =================================================
        # CREATE USER
        # =================================================

        user = User(
            phone_number=phone_number,
            full_name=full_name,
            role=role,
            preferred_language=preferred_language,
            is_active=True,
        )

        user.set_password(
            password
        )

        # =================================================
        # CREATE COMPLETE FARMER PROFILE
        # =================================================

        from backend.app.models.farmer_profile import (
            FarmerProfile,
        )

        farmer_profile = FarmerProfile(
            user=user,
            region=region,
            woreda=woreda,
            kebele=kebele,
            latitude=latitude,
            longitude=longitude,
            sms_opt_in=sms_opt_in,
        )

        # =================================================
        # DATABASE TRANSACTION
        # =================================================

        try:

            db.session.add(
                user
            )

            db.session.add(
                farmer_profile
            )

            db.session.commit()

        except Exception as error:

            db.session.rollback()

            raise AuthServiceError(
                "Failed to create farmer account: "
                f"{error}"
            ) from error

        return user

    # =====================================================
    # LOGIN
    # =====================================================

    @classmethod
    def authenticate_user(
        cls,
        phone_number: str,
        password: str,
    ) -> User:
        """
        Authenticate a user using phone number and
        password.
        """

        phone_number = cls.normalize_phone(
            phone_number
        )

        password = cls.validate_password(
            password
        )

        user = cls.get_user_by_phone(
            phone_number
        )

        # -------------------------------------------------
        # INVALID USER
        # -------------------------------------------------

        # Use the same public error for both cases so
        # the API does not reveal whether a phone number
        # exists.

        if user is None:

            raise InvalidCredentialsError(
                "Invalid phone number or password."
            )

        # -------------------------------------------------
        # INACTIVE ACCOUNT
        # -------------------------------------------------

        if not user.is_active:

            raise InactiveUserError(
                "This account is inactive."
            )

        # -------------------------------------------------
        # PASSWORD VERIFICATION
        # -------------------------------------------------

        if not user.check_password(
            password
        ):

            raise InvalidCredentialsError(
                "Invalid phone number or password."
            )

        # -------------------------------------------------
        # UPDATE LAST LOGIN TIME
        # -------------------------------------------------

        user.last_login_at = datetime.now(
            timezone.utc
        )

        try:

            db.session.commit()

        except Exception as error:

            db.session.rollback()

            print(
                "Last login update error:",
                error,
            )

            raise AuthServiceError(
                "Failed to update last login time."
            ) from error

        return user

    # =====================================================
    # SERIALIZATION
    # =====================================================

    @staticmethod
    def user_to_dict(
        user: User,
    ) -> dict[str, Any]:
        """
        Convert a User model into a safe API response.

        The password hash is NEVER returned.
        """

        return {
            "id": user.id,

            "phone_number": (
                user.phone_number
            ),

            "full_name": (
                user.full_name
            ),

            "role": (
                user.role
            ),

            "preferred_language": (
                user.preferred_language
            ),

            "is_active": bool(
                user.is_active
            ),

            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else None
            ),

            "updated_at": (
                user.updated_at.isoformat()
                if user.updated_at
                else None
            ),

            "last_login_at": (
                user.last_login_at.isoformat()
                if user.last_login_at
                else None
            ),
        }

    # =====================================================
    # ACCOUNT STATUS
    # =====================================================

    @classmethod
    def ensure_active(
        cls,
        user: User,
    ) -> User:
        """
        Ensure that the supplied account is active.
        """

        if not user.is_active:

            raise InactiveUserError(
                "This account is inactive."
            )

        return user