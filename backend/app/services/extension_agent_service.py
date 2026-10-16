"""
=========================================================
Extension Agent Service
=========================================================

Handles creation and retrieval of agricultural extension
agent accounts.

Responsibilities:
    - Validate extension-agent information
    - Create extension-agent User account
    - Create ExtensionAgent professional profile
    - Maintain database transaction integrity
    - Retrieve extension-agent profiles

Security:
    Extension-agent accounts must NOT be created through
    public farmer registration.

=========================================================
"""

from __future__ import annotations

from typing import Any

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.services.auth_service import (
    AuthService,
    AuthServiceError,
    UserAlreadyExistsError,
)


# =========================================================
# EXCEPTIONS
# =========================================================

class ExtensionAgentServiceError(Exception):
    """
    Base exception for extension-agent service errors.
    """


class ExtensionAgentAlreadyExistsError(
    ExtensionAgentServiceError
):
    """
    Raised when an extension-agent profile already exists.
    """


# =========================================================
# SERVICE
# =========================================================

class ExtensionAgentService:
    """
    Business logic for agricultural extension agents.
    """

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def validate_region(
        region: str,
    ) -> str:
        """
        Validate the assigned region.
        """

        if not isinstance(region, str):
            raise ExtensionAgentServiceError(
                "Region must be a string."
            )

        region = region.strip()

        if not region:
            raise ExtensionAgentServiceError(
                "Region is required."
            )

        if len(region) > 50:
            raise ExtensionAgentServiceError(
                "Region must not exceed 50 characters."
            )

        return region

    @staticmethod
    def validate_woreda(
        woreda: str | None,
    ) -> str | None:
        """
        Validate the assigned woreda.
        """

        if woreda is None:
            return None

        if not isinstance(woreda, str):
            raise ExtensionAgentServiceError(
                "Woreda must be a string."
            )

        woreda = woreda.strip()

        if not woreda:
            return None

        if len(woreda) > 50:
            raise ExtensionAgentServiceError(
                "Woreda must not exceed 50 characters."
            )

        return woreda

    @staticmethod
    def validate_specialization(
        specialization: str | None,
    ) -> str | None:
        """
        Validate the crop specialization.
        """

        if specialization is None:
            return None

        if not isinstance(specialization, str):
            raise ExtensionAgentServiceError(
                "Specialization must be a string."
            )

        specialization = specialization.strip()

        if not specialization:
            return None

        if len(specialization) > 50:
            raise ExtensionAgentServiceError(
                "Specialization must not exceed 50 characters."
            )

        return specialization

    @staticmethod
    def validate_certification_number(
        certification_number: str | None,
    ) -> str | None:
        """
        Validate professional certification number.
        """

        if certification_number is None:
            return None

        if not isinstance(certification_number, str):
            raise ExtensionAgentServiceError(
                "Certification number must be a string."
            )

        certification_number = (
            certification_number.strip()
        )

        if not certification_number:
            return None

        if len(certification_number) > 50:
            raise ExtensionAgentServiceError(
                "Certification number must not exceed "
                "50 characters."
            )

        return certification_number

    # =====================================================
    # CREATE EXTENSION AGENT
    # =====================================================

    @classmethod
    def create_agent(
        cls,
        phone_number: str,
        full_name: str,
        password: str,
        region: str,
        woreda: str | None = None,
        specialization: str | None = None,
        certification_number: str | None = None,
        preferred_language: str = "en",
    ) -> User:
        """
        Create an extension-agent account.

        Creates:

            1. User authentication record
            2. ExtensionAgent professional profile

        Both records are committed as one database
        transaction.
        """

        # -------------------------------------------------
        # VALIDATE COMMON USER INFORMATION
        # -------------------------------------------------

        phone_number = AuthService.normalize_phone(
            phone_number
        )

        full_name = AuthService.validate_full_name(
            full_name
        )

        password = AuthService.validate_password(
            password
        )

        preferred_language = (
            AuthService.validate_language(
                preferred_language
            )
        )

        # -------------------------------------------------
        # VALIDATE PROFESSIONAL INFORMATION
        # -------------------------------------------------

        region = cls.validate_region(region)

        woreda = cls.validate_woreda(
            woreda
        )

        specialization = cls.validate_specialization(
            specialization
        )

        certification_number = (
            cls.validate_certification_number(
                certification_number
            )
        )

        # -------------------------------------------------
        # DUPLICATE PHONE CHECK
        # -------------------------------------------------

        existing_user = AuthService.get_user_by_phone(
            phone_number
        )

        if existing_user is not None:
            raise UserAlreadyExistsError(
                "A user with this phone number "
                "already exists."
            )

        # -------------------------------------------------
        # DUPLICATE CERTIFICATION CHECK
        # -------------------------------------------------

        if certification_number:

            existing_agent = (
                ExtensionAgent.query
                .filter_by(
                    certification_number=(
                        certification_number
                    )
                )
                .first()
            )

            if existing_agent is not None:
                raise ExtensionAgentAlreadyExistsError(
                    "An extension agent with this "
                    "certification number already exists."
                )

        # -------------------------------------------------
        # CREATE USER
        # -------------------------------------------------

        user = User(
            phone_number=phone_number,
            full_name=full_name,
            role="extension_agent",
            preferred_language=preferred_language,
            is_active=True,
        )

        user.set_password(password)

        # -------------------------------------------------
        # DATABASE TRANSACTION
        # -------------------------------------------------

        try:

            db.session.add(user)

            # Flush assigns user.id before creating
            # the extension-agent profile.
            db.session.flush()

            agent = ExtensionAgent(
                user_id=user.id,
                region=region,
                woreda=woreda,
                specialization=specialization,
                certification_number=(
                    certification_number
                ),
            )

            db.session.add(agent)

            db.session.commit()

        except Exception as error:

            db.session.rollback()

            raise ExtensionAgentServiceError(
                "Failed to create extension agent: "
                f"{error}"
            ) from error

        return user

    # =====================================================
    # GET AGENT PROFILE
    # =====================================================

    @staticmethod
    def get_agent_by_user_id(
        user_id: int,
    ) -> ExtensionAgent | None:
        """
        Retrieve an extension-agent profile by user ID.
        """

        return (
            ExtensionAgent.query
            .filter_by(
                user_id=int(user_id)
            )
            .first()
        )

    # =====================================================
    # SERIALIZATION
    # =====================================================

    @staticmethod
    def agent_to_dict(
        agent: ExtensionAgent,
    ) -> dict[str, Any]:
        """
        Convert an extension-agent profile into a safe
        API response.

        Password hashes are never returned.
        """

        user = agent.user

        return {
            "agent_id": agent.user_id,
            "full_name": (
                user.full_name
                if user
                else None
            ),
            "phone_number": (
                user.phone_number
                if user
                else None
            ),
            "role": (
                user.role
                if user
                else "extension_agent"
            ),
            "region": agent.region,
            "woreda": agent.woreda,
            "specialization": agent.specialization,
            "certification_number": (
                agent.certification_number
            ),
            "preferred_language": (
                user.preferred_language
                if user
                else None
            ),
            "is_active": (
                bool(user.is_active)
                if user
                else False
            ),
            "created_at": (
                user.created_at.isoformat()
                if user and user.created_at
                else None
            ),
            "last_login_at": (
                user.last_login_at.isoformat()
                if user and user.last_login_at
                else None
            ),
        }