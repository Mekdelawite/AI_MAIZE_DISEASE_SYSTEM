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

import re
import secrets
from datetime import datetime, timezone
from typing import Any

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.extension_agent_activation import ExtensionAgentActivation
from backend.app.models.extension_agent_assignment_history import ExtensionAgentAssignmentHistory
from backend.app.models.administrative_division import (
    GeographyRegion,
    GeographyZone,
    GeographyWoreda,
)
from backend.app.services.auth_service import (
    AuthService,
    AuthServiceError,
    UserAlreadyExistsError,
)
from sqlalchemy.exc import IntegrityError


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
            raise ValueError(
                "Region must be a string."
            )

        region = region.strip()

        if not region:
            raise ValueError(
                "Region is required."
            )

        if len(region) > 50:
            raise ValueError(
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
            raise ValueError(
                "Woreda must be a string."
            )

        woreda = woreda.strip()

        if not woreda:
            return None

        if len(woreda) > 50:
            raise ValueError(
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
            raise ValueError(
                "Specialization must be a string."
            )

        specialization = specialization.strip()

        if not specialization:
            return None

        if len(specialization) > 50:
            raise ValueError(
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
            raise ValueError(
                "Certification number must be a string."
            )

        certification_number = (
            certification_number.strip()
        )

        if not certification_number:
            return None

        if len(certification_number) > 50:
            raise ValueError(
                "Certification number must not exceed "
                "50 characters."
            )

        return certification_number

    @classmethod
    def create_pending_agent(
        cls,
        *,
        phone_number: str,
        full_name: str,
        email: str,
        employee_id: str,
        organization: str,
        region_id: str,
        zone_id: str,
        woreda_id: str,
        verification_method: str,
        professional_info_verified: bool,
        verified_by_admin_id: int,
        specialization: str | None = None,
        certification_number: str | None = None,
        preferred_language: str = "en",
    ) -> User:
        if professional_info_verified is not True:
            raise ValueError(
                "Professional information must be verified before account creation."
            )

        phone_number = AuthService.normalize_phone(phone_number)
        full_name = AuthService.validate_full_name(full_name)
        preferred_language = AuthService.validate_language(preferred_language)

        if not isinstance(email, str):
            raise ValueError("Official email address is required.")
        email = email.strip().lower()
        if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Enter a valid official email address.")
        if not isinstance(employee_id, str) or not employee_id.strip():
            raise ValueError("Employee ID is required.")
        employee_id = employee_id.strip().upper()
        if len(employee_id) > 80:
            raise ValueError("Employee ID must not exceed 80 characters.")
        if not isinstance(organization, str) or not organization.strip():
            raise ValueError("Organization or agricultural office is required.")
        organization = organization.strip()
        if len(organization) > 150:
            raise ValueError("Organization must not exceed 150 characters.")

        verification_method = (
            verification_method.strip().lower()
            if isinstance(verification_method, str)
            else ""
        )
        if verification_method not in {"email", "sms"}:
            raise ValueError("Verification method must be email or sms.")

        if not all(isinstance(value, str) and value.strip() for value in (region_id, zone_id, woreda_id)):
            raise ValueError("Region, zone, and woreda are required.")
        region = db.session.get(GeographyRegion, region_id.strip())
        zone = db.session.get(GeographyZone, zone_id.strip())
        woreda = db.session.get(GeographyWoreda, woreda_id.strip())
        if (
            region is None
            or zone is None
            or woreda is None
            or zone.region_id != region.id
            or woreda.zone_id != zone.id
        ):
            raise ValueError(
                "The selected region, zone, and woreda do not form a valid hierarchy."
            )

        if not isinstance(verified_by_admin_id, int) or verified_by_admin_id < 1:
            raise ValueError("The verifying administrator is invalid.")

        specialization = cls.validate_specialization(specialization)
        certification_number = cls.validate_certification_number(certification_number)

        phone_formats = {
            phone_number,
            "0" + phone_number[4:],
            phone_number[1:],
        }
        if User.query.filter(User.phone_number.in_(phone_formats)).first():
            raise UserAlreadyExistsError(
                "A user with this phone number already exists."
            )
        if ExtensionAgent.query.filter_by(email=email).first():
            raise ExtensionAgentAlreadyExistsError(
                "An extension agent with this email already exists."
            )
        if ExtensionAgent.query.filter_by(employee_id=employee_id).first():
            raise ExtensionAgentAlreadyExistsError(
                "An extension agent with this employee ID already exists."
            )
        if certification_number and ExtensionAgent.query.filter_by(
            certification_number=certification_number,
        ).first():
            raise ExtensionAgentAlreadyExistsError(
                "An extension agent with this certification number already exists."
            )

        user = User(
            phone_number=phone_number,
            full_name=full_name,
            role="extension_agent",
            preferred_language=preferred_language,
            is_active=False,
        )
        user.set_password(secrets.token_urlsafe(48))
        verified_at = datetime.now(timezone.utc)

        try:
            db.session.add(user)
            db.session.flush()
            agent = ExtensionAgent(
                user_id=user.id,
                region=region.name_en,
                zone=zone.name_en,
                woreda=woreda.name_en,
                region_id=region.id,
                zone_id=zone.id,
                woreda_id=woreda.id,
                email=email,
                employee_id=employee_id,
                organization=organization,
                professional_info_verified=True,
                professional_info_verified_by_id=verified_by_admin_id,
                professional_info_verified_at=verified_at,
                account_status="pending_activation",
                specialization=specialization,
                certification_number=certification_number,
            )
            db.session.add(agent)
            db.session.add(
                ExtensionAgentActivation(
                    user_id=user.id,
                    verification_method=verification_method,
                )
            )
            db.session.add(
                ExtensionAgentAssignmentHistory(
                    user_id=user.id,
                    previous_woreda_id=None,
                    new_woreda_id=woreda.id,
                    changed_by_admin_id=verified_by_admin_id,
                )
            )
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise ExtensionAgentAlreadyExistsError(
                "An account with the supplied phone, email, or employee ID already exists."
            ) from error
        except Exception:
            db.session.rollback()
            raise

        return user

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
        Reject the retired immediate-activation flow.
        """
        raise ExtensionAgentServiceError(
            "Extension agents must be created through the pending-activation workflow."
        )

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
    # CREATE EXTENSION AGENT FROM PAYLOAD
    # =====================================================

    @classmethod
    def create_extension_agent(
        cls,
        payload: dict[str, Any],
    ) -> User:
        """
        Create an extension agent from an admin payload.
        """

        required_fields = (
            "phone_number",
            "full_name",
            "password",
            "region",
        )

        missing_fields = [
            field
            for field in required_fields
            if not payload.get(field)
        ]

        if missing_fields:
            raise ExtensionAgentServiceError(
                "Missing required fields: "
                + ", ".join(missing_fields)
            )

        return cls.create_agent(
            phone_number=payload["phone_number"],
            full_name=payload["full_name"],
            password=payload["password"],
            region=payload["region"],
            woreda=payload.get("woreda"),
            specialization=payload.get("specialization"),
            certification_number=payload.get(
                "certification_number"
            ),
            preferred_language=payload.get(
                "preferred_language",
                "en",
            ),
        )

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
            "zone": agent.zone,
            "woreda": agent.woreda,
            "region_id": agent.region_id,
            "zone_id": agent.zone_id,
            "woreda_id": agent.woreda_id,
            "email": agent.email,
            "employee_id": agent.employee_id,
            "organization": agent.organization,
            "professional_info_verified": bool(
                agent.professional_info_verified
            ),
            "professional_info_verified_by_id": (
                agent.professional_info_verified_by_id
            ),
            "professional_info_verified_by": (
                agent.professional_info_verified_by.full_name
                if agent.professional_info_verified_by
                else None
            ),
            "professional_info_verified_at": (
                agent.professional_info_verified_at.isoformat()
                if agent.professional_info_verified_at
                else None
            ),
            "account_status": agent.account_status,
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
