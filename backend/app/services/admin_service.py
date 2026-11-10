"""
=========================================================
Admin Service
=========================================================

Handles administrative business logic for the
AI Maize Disease Detection System.

Responsibilities:
    - Retrieve users
    - Retrieve farmers
    - Retrieve extension agents
    - Activate/deactivate accounts
    - Retrieve diagnosis records
    - Retrieve diagnosis statistics
    - Retrieve extension-agent comments
    - Provide complete dashboard statistics
    - Provide regional disease statistics
    - Provide geographic disease cases

Security:
    Authorization is handled by the route layer.

    This service assumes that the caller has already
    been authorized as an administrator.
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import joinedload

from backend.app.extensions import db

from backend.app.models.user import User
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.extension_comment import ExtensionComment
from backend.app.models.discussion_reply import DiscussionReply
from backend.app.models.advisory_record import AdvisoryRecord
from backend.app.models.extension_agent_assignment_history import ExtensionAgentAssignmentHistory
from backend.app.models.administrative_division import GeographyRegion, GeographyZone, GeographyWoreda
from backend.app.services.extension_agent_service import ExtensionAgentService


# =========================================================
# EXCEPTIONS
# =========================================================


class AdminServiceError(Exception):
    """Base exception for admin service errors."""


class AdminUserNotFoundError(AdminServiceError):
    """Raised when an administrative user lookup fails."""


class InvalidUserStatusError(AdminServiceError):
    """Raised when an invalid account status is supplied."""


class InvalidDateFilterError(AdminServiceError):
    """Raised when an invalid date filter is supplied."""


# =========================================================
# SERVICE
# =========================================================


class AdminService:
    """
    Business logic for administrator operations.

    HTTP requests and JWT authorization are handled by
    the route layer.
    """

    # =====================================================
    # USER LOOKUP
    # =====================================================

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """
        Retrieve a user by ID.
        """

        try:
            user_id = int(user_id)
        except (TypeError, ValueError) as error:
            raise AdminUserNotFoundError(
                "Invalid user ID."
            ) from error

        user = db.session.get(User, user_id)

        if user is None:
            raise AdminUserNotFoundError(
                "User not found."
            )

        return user

    # =====================================================
    # SERIALIZATION
    # =====================================================

    @staticmethod
    def user_to_dict(
        user: User,
    ) -> dict[str, Any]:
        """
        Safely serialize a user.

        Password hashes are never returned.
        """

        return {
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "role": user.role,
            "region": (
                user.farmer_profile.region
                if user.farmer_profile
                else user.extension_agent_profile.region
                if user.extension_agent_profile
                else None
            ),
            "kebele": (
                user.farmer_profile.kebele
                if user.farmer_profile
                else None
            ),
            "preferred_language": user.preferred_language,
            "is_active": bool(user.is_active),
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
    # LIST ALL USERS
    # =====================================================

    @classmethod
    def get_all_users(
        cls,
        *,
        role: str | None = None,
        region: str | None = None,
        kebele: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve users with optional role, region, and kebele filters plus
        search across name, phone, role, and region.
        """

        query = User.query.options(
            joinedload(User.farmer_profile),
            joinedload(User.extension_agent_profile),
        ).outerjoin(
            FarmerProfile,
            FarmerProfile.user_id == User.id,
        ).outerjoin(
            ExtensionAgent,
            ExtensionAgent.user_id == User.id,
        )

        if role:
            query = query.filter(User.role == role)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.full_name.ilike(pattern),
                    User.phone_number.ilike(pattern),
                    User.role.ilike(pattern),
                    FarmerProfile.region.ilike(pattern),
                    ExtensionAgent.region.ilike(pattern),
                )
            )

        if region:
            region_pattern = f"%{region}%"
            query = query.filter(
                db.or_(
                    FarmerProfile.region.ilike(region_pattern),
                    ExtensionAgent.region.ilike(region_pattern),
                )
            )

        if kebele:
            query = query.filter(
                FarmerProfile.kebele.ilike(f"%{kebele}%")
            )

        users = query.order_by(User.created_at.desc()).all()

        return [
            cls.user_to_dict(user)
            for user in users
        ]

    # =====================================================
    # LIST FARMERS
    # =====================================================

    @classmethod
    def get_all_farmers(
        cls,
        *,
        search: str | None = None,
        region: str | None = None,
        woreda: str | None = None,
        kebele: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all farmer accounts together with
        their agricultural profiles.
        """

        query = (
            User.query
            .outerjoin(
                FarmerProfile,
                FarmerProfile.user_id == User.id,
            )
            .filter(User.role == "farmer")
        )

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.full_name.ilike(pattern),
                    User.phone_number.ilike(pattern),
                    FarmerProfile.kebele.ilike(pattern),
                )
            )

        for field, value in ((FarmerProfile.region, region), (FarmerProfile.woreda, woreda), (FarmerProfile.kebele, kebele)):
            if value:
                query = query.filter(field.ilike(f"%{value}%"))

        users = query.order_by(User.created_at.desc()).all()

        farmers: list[dict[str, Any]] = []

        for user in users:

            profile = (
                FarmerProfile.query
                .filter_by(user_id=user.id)
                .first()
            )

            farmer = cls.user_to_dict(user)

            farmer["profile"] = (
                {
                    "region": profile.region,
                    "woreda": profile.woreda,
                    "kebele": profile.kebele,
                    "latitude": (
                        float(profile.latitude)
                        if profile.latitude is not None
                        else None
                    ),
                    "longitude": (
                        float(profile.longitude)
                        if profile.longitude is not None
                        else None
                    ),
                    "sms_opt_in": bool(
                        profile.sms_opt_in
                    ),
                }
                if profile
                else None
            )

            farmer["region"] = profile.region if profile else None
            farmer["woreda"] = profile.woreda if profile else None
            farmer["kebele"] = profile.kebele if profile else None
            farmer["sms_opt_in"] = bool(profile.sms_opt_in) if profile else False

            farmers.append(farmer)

        return farmers

    # =====================================================
    # LIST EXTENSION AGENTS
    # =====================================================

    @classmethod
    def get_all_extension_agents(
        cls,
        *,
        search: str | None = None,
        region: str | None = None,
        woreda: str | None = None,
        account_status: str | None = None,
        professional_info_verified: bool | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all extension-agent accounts together
        with their professional profiles.
        """

        agents = (
            ExtensionAgent.query
            .join(
                User,
                ExtensionAgent.user_id == User.id,
            )
        )

        if search:
            pattern = f"%{search}%"
            agents = agents.filter(
                db.or_(
                    User.full_name.ilike(pattern),
                    User.phone_number.ilike(pattern),
                    ExtensionAgent.email.ilike(pattern),
                    ExtensionAgent.employee_id.ilike(pattern),
                    ExtensionAgent.organization.ilike(pattern),
                )
            )

        if region:
            agents = agents.filter(ExtensionAgent.region.ilike(f"%{region}%"))

        if woreda:
            agents = agents.filter(ExtensionAgent.woreda.ilike(f"%{woreda}%"))

        if account_status:
            agents = agents.filter(
                ExtensionAgent.account_status == account_status
            )

        if professional_info_verified is not None:
            agents = agents.filter(
                ExtensionAgent.professional_info_verified
                == professional_info_verified
            )

        agents = agents.order_by(User.created_at.desc()).all()
        result = []
        for agent in agents:
            row = ExtensionAgentService.agent_to_dict(agent)
            row["id"] = agent.user_id
            result.append(row)
        return result

        agents = agents.order_by(User.created_at.desc()).all()
        result = []
        for agent in agents:
            row = ExtensionAgentService.agent_to_dict(agent)
            row["id"] = agent.user_id
            result.append(row)
        return result

    @classmethod
    def set_extension_agent_status(
        cls,
        user_id: int,
        account_status: str,
    ) -> dict[str, Any]:
        if account_status not in {"active", "suspended"}:
            raise InvalidUserStatusError(
                "Extension-agent status must be active or suspended."
            )
        agent = (
            ExtensionAgent.query
            .filter_by(user_id=user_id)
            .with_for_update()
            .first()
        )
        if agent is None or agent.user is None:
            raise AdminUserNotFoundError("Extension agent not found.")
        if account_status == "active":
            if (
                agent.account_status != "suspended"
                or not agent.region_id
                or not agent.zone_id
                or not agent.woreda_id
            ):
                raise InvalidUserStatusError(
                    "Only assigned suspended agents can be reactivated."
                )
            agent.user.is_active = True
        else:
            if agent.account_status == "pending_activation":
                raise InvalidUserStatusError(
                    "Pending agents cannot be suspended or reactivated before activation."
                )
            agent.user.is_active = False
        agent.account_status = account_status
        try:
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            raise AdminServiceError(
                "Failed to update extension-agent status."
            ) from error
        return ExtensionAgentService.agent_to_dict(agent)

    @classmethod
    def transfer_extension_agent(
        cls,
        *,
        user_id: int,
        region_id: str,
        zone_id: str,
        woreda_id: str,
        admin_id: int,
    ) -> dict[str, Any]:
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (region_id, zone_id, woreda_id)
        ):
            raise ValueError("Region, zone, and woreda are required.")
        if not isinstance(admin_id, int) or admin_id < 1:
            raise ValueError("The transferring administrator is invalid.")

        region_id = region_id.strip()
        zone_id = zone_id.strip()
        woreda_id = woreda_id.strip()

        agent = (
            ExtensionAgent.query
            .filter_by(user_id=user_id)
            .with_for_update()
            .first()
        )
        if agent is None:
            raise AdminUserNotFoundError("Extension agent not found.")
        region = db.session.get(GeographyRegion, region_id)
        zone = db.session.get(GeographyZone, zone_id)
        woreda = db.session.get(GeographyWoreda, woreda_id)
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
        if agent.woreda_id == woreda.id:
            raise ValueError("The agent is already assigned to this woreda.")

        try:
            db.session.add(
                ExtensionAgentAssignmentHistory(
                    user_id=agent.user_id,
                    previous_woreda_id=agent.woreda_id,
                    new_woreda_id=woreda.id,
                    changed_by_admin_id=admin_id,
                )
            )
            agent.region_id = region.id
            agent.zone_id = zone.id
            agent.woreda_id = woreda.id
            agent.region = region.name_en
            agent.zone = zone.name_en
            agent.woreda = woreda.name_en
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return ExtensionAgentService.agent_to_dict(agent)

    @staticmethod
    def get_extension_agent_assignment_history(
        user_id: int,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": item.id,
                "previous_woreda": (
                    item.previous_woreda.name_en
                    if item.previous_woreda
                    else None
                ),
                "previous_woreda_id": item.previous_woreda_id,
                "new_woreda": item.new_woreda.name_en,
                "new_woreda_id": item.new_woreda_id,
                "changed_by_admin_id": item.changed_by_admin_id,
                "changed_by_admin": (
                    item.changed_by_admin.full_name
                    if item.changed_by_admin
                    else None
                ),
                "changed_at": item.changed_at.isoformat(),
            }
            for item in (
                ExtensionAgentAssignmentHistory.query
                .filter_by(user_id=user_id)
                .order_by(ExtensionAgentAssignmentHistory.changed_at.asc())
                .all()
            )
        ]

    # =====================================================
    # UPDATE ACCOUNT STATUS
    # =====================================================

    @classmethod
    def set_user_status(
        cls,
        user_id: int,
        is_active: bool,
    ) -> dict[str, Any]:
        """
        Activate or deactivate a user account.
        """

        if not isinstance(is_active, bool):
            raise InvalidUserStatusError(
                "Account status must be true or false."
            )

        user = cls.get_user_by_id(user_id)

        user.is_active = is_active

        try:
            db.session.commit()
        except Exception as error:
            db.session.rollback()

            raise AdminServiceError(
                "Failed to update account status."
            ) from error

        return cls.user_to_dict(user)

    # =====================================================
    # DIAGNOSIS SERIALIZATION
    # =====================================================

    @staticmethod
    def diagnosis_to_dict(
        diagnosis: DiagnosisRecord,
    ) -> dict[str, Any]:
        """
        Serialize a diagnosis record for the admin API.
        """

        return {
            "id": diagnosis.id,
            "user_id": diagnosis.user_id,
            "farmer_name": (
                diagnosis.user.full_name
                if diagnosis.user and diagnosis.user.role == "farmer"
                else None
            ),
            "region": (
                diagnosis.user.farmer_profile.region
                if diagnosis.user and diagnosis.user.farmer_profile
                else None
            ),
            "woreda": (
                diagnosis.user.farmer_profile.woreda
                if diagnosis.user and diagnosis.user.farmer_profile
                else None
            ),
            "image_filename": diagnosis.image_filename,
            "image_path": diagnosis.image_path,
            "disease_class": diagnosis.disease_class,
            "confidence": (
                float(diagnosis.confidence)
                if diagnosis.confidence is not None
                else None
            ),
            "model_name": diagnosis.model_name,
            "model_version": diagnosis.model_version,
            "prediction_time": diagnosis.prediction_time,
            "explainability_requested": bool(
                diagnosis.explainability_requested
            ),
            "heatmap_path": diagnosis.heatmap_path,
            "created_at": (
                diagnosis.created_at.isoformat()
                if diagnosis.created_at
                else None
            ),
        }

    # =====================================================
    # LIST DIAGNOSES
    # =====================================================

    @classmethod
    def get_all_diagnoses(
        cls,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all AI diagnosis records.
        """

        diagnoses = (
            DiagnosisRecord.query
            .options(
                joinedload(DiagnosisRecord.user)
                .joinedload(User.farmer_profile)
            )
            .order_by(
                DiagnosisRecord.created_at.desc()
            )
            .all()
        )

        return [
            cls.diagnosis_to_dict(diagnosis)
            for diagnosis in diagnoses
        ]

    # =====================================================
    # EXTENSION COMMENTS
    # =====================================================

    @staticmethod
    def comment_to_dict(
        comment: ExtensionComment,
    ) -> dict[str, Any]:
        """
        Serialize an extension-agent comment.
        """

        agent = comment.extension_agent

        return {
            "id": comment.id,
            "kind": "diagnosis_comment",
            "source_label": "Diagnosis review",
            "diagnosis_id": comment.diagnosis_id,
            "extension_agent_id": (
                comment.extension_agent_id
            ),
            "extension_agent_name": (
                agent.full_name
                if agent
                else None
            ),
            "comment": comment.comment,
            "created_at": (
                comment.created_at.isoformat()
                if comment.created_at
                else None
            ),
            "updated_at": (
                comment.updated_at.isoformat()
                if comment.updated_at
                else None
            ),
        }

    @staticmethod
    def discussion_reply_to_dict(reply: DiscussionReply) -> dict[str, Any]:
        """Serialize an extension-agent reply to an agricultural discussion."""

        agent = reply.extension_agent
        post = reply.post

        return {
            "id": f"discussion-reply-{reply.id}",
            "kind": "discussion_reply",
            "source_label": "Discussion reply",
            "post_id": reply.post_id,
            "post_title": post.title if post else None,
            "diagnosis_id": post.diagnosis_id if post else None,
            "extension_agent_id": reply.extension_agent_id,
            "extension_agent_name": agent.full_name if agent else None,
            "comment": reply.content,
            "created_at": reply.created_at.isoformat() if reply.created_at else None,
            "updated_at": reply.updated_at.isoformat() if reply.updated_at else None,
        }

    @classmethod
    def get_all_extension_comments(cls) -> list[dict[str, Any]]:
        """Return diagnosis comments and discussion replies written by agents."""

        diagnosis_comments = [
            cls.comment_to_dict(comment)
            for comment in ExtensionComment.query.order_by(
                ExtensionComment.created_at.desc()
            ).all()
        ]
        discussion_replies = [
            cls.discussion_reply_to_dict(reply)
            for reply in DiscussionReply.query.options(
                joinedload(DiscussionReply.extension_agent),
                joinedload(DiscussionReply.post),
            )
            .filter(DiscussionReply.extension_agent_id.isnot(None))
            .order_by(DiscussionReply.created_at.desc())
            .all()
        ]

        def created_at_utc(item: dict[str, Any]) -> datetime:
            value = item.get("created_at")
            if not value:
                return datetime.min.replace(tzinfo=timezone.utc)
            timestamp = datetime.fromisoformat(value)
            if timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=timezone.utc)
            return timestamp.astimezone(timezone.utc)

        return sorted(
            diagnosis_comments + discussion_replies,
            key=created_at_utc,
            reverse=True,
        )

    # =====================================================
    # DATE FILTER VALIDATION
    # =====================================================

    @staticmethod
    def parse_date_filter(
        value: str | None,
        field_name: str,
    ) -> datetime | None:
        """
        Convert a YYYY-MM-DD date string into a UTC
        datetime suitable for diagnosis filtering.

        Returns None when no value is supplied.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise InvalidDateFilterError(
                f"{field_name} must be a date in YYYY-MM-DD format."
            )

        value = value.strip()

        if not value:
            return None

        try:
            parsed_date = datetime.strptime(
                value,
                "%Y-%m-%d",
            )
        except ValueError as error:
            raise InvalidDateFilterError(
                f"{field_name} must use YYYY-MM-DD format."
            ) from error

        return parsed_date.replace(
            tzinfo=timezone.utc
        )

    # =====================================================
    # DIAGNOSIS QUERY FILTERING
    # =====================================================

    @classmethod
    def _apply_diagnosis_filters(
        cls,
        query,
        disease_class: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        """
        Apply common diagnosis filters.

        This helper is shared by regional statistics
        and geo-disease queries so that filtering logic
        is not duplicated.
        """

        start_datetime = cls.parse_date_filter(
            start_date,
            "start_date",
        )

        end_datetime = cls.parse_date_filter(
            end_date,
            "end_date",
        )

        # -------------------------------------------------
        # END DATE IS INCLUSIVE
        # -------------------------------------------------

        if end_datetime is not None:
            end_datetime = end_datetime.replace(
                hour=23,
                minute=59,
                second=59,
                microsecond=999999,
            )

        # -------------------------------------------------
        # VALIDATE DATE RANGE
        # -------------------------------------------------

        if (
            start_datetime is not None
            and end_datetime is not None
            and start_datetime > end_datetime
        ):
            raise InvalidDateFilterError(
                "start_date cannot be later than end_date."
            )

        # -------------------------------------------------
        # DISEASE FILTER
        # -------------------------------------------------

        normalized_disease_class = None

        if disease_class is not None:

            if not isinstance(
                disease_class,
                str,
            ):
                raise AdminServiceError(
                    "disease_class must be a string."
                )

            normalized_disease_class = (
                disease_class.strip()
            )

            if normalized_disease_class:
                query = query.filter(
                    DiagnosisRecord.disease_class
                    == normalized_disease_class
                )

        # -------------------------------------------------
        # START DATE
        # -------------------------------------------------

        if start_datetime is not None:
            query = query.filter(
                DiagnosisRecord.created_at
                >= start_datetime
            )

        # -------------------------------------------------
        # END DATE
        # -------------------------------------------------

        if end_datetime is not None:
            query = query.filter(
                DiagnosisRecord.created_at
                <= end_datetime
            )

        return (
            query,
            normalized_disease_class,
        )

    # =====================================================
    # REGIONAL STATISTICS
    # =====================================================

    @classmethod
    def get_regional_statistics(
        cls,
        disease_class: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate geographic and disease statistics
        for the administrator.

        Optional filters:
            disease_class
            start_date
            end_date
        """

        query, normalized_disease_class = (
            cls._apply_diagnosis_filters(
                DiagnosisRecord.query,
                disease_class=disease_class,
                start_date=start_date,
                end_date=end_date,
            )
        )

        diagnoses = query.all()

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        total_diagnoses = len(diagnoses)

        healthy_cases = 0
        diseased_cases = 0

        # -------------------------------------------------
        # DISEASE COUNTS
        # -------------------------------------------------

        disease_counts: dict[str, int] = {}

        # -------------------------------------------------
        # REGIONAL COUNTS
        # -------------------------------------------------

        region_counts: dict[str, int] = {}

        # -------------------------------------------------
        # WOREDA COUNTS
        # -------------------------------------------------

        woreda_counts: dict[
            tuple[str, str],
            int,
        ] = {}

        # -------------------------------------------------
        # KEBELE COUNTS
        # -------------------------------------------------

        kebele_counts: dict[
            tuple[str, str, str],
            int,
        ] = {}

        # -------------------------------------------------
        # DAILY TREND
        # -------------------------------------------------

        daily_counts: dict[str, int] = {}

        # -------------------------------------------------
        # PROCESS DIAGNOSES
        # -------------------------------------------------

        for diagnosis in diagnoses:

            disease = (
                diagnosis.disease_class
                or "Unknown"
            )

            disease_counts[disease] = (
                disease_counts.get(
                    disease,
                    0,
                )
                + 1
            )

            normalized_disease = (
                disease.strip().lower()
            )

            if normalized_disease == "healthy":
                healthy_cases += 1
            else:
                diseased_cases += 1

            # -------------------------------------------------
            # DAILY TREND
            # -------------------------------------------------

            created_at = diagnosis.created_at

            if created_at:

                date_key = (
                    created_at
                    .date()
                    .isoformat()
                )

                daily_counts[date_key] = (
                    daily_counts.get(
                        date_key,
                        0,
                    )
                    + 1
                )

            # -------------------------------------------------
            # FARMER LOCATION
            # -------------------------------------------------

            if diagnosis.user_id is None:
                continue

            profile = (
                FarmerProfile.query
                .filter_by(
                    user_id=diagnosis.user_id
                )
                .first()
            )

            if profile is None:
                continue

            # -------------------------------------------------
            # REGION
            # -------------------------------------------------

            if profile.region:

                region = profile.region.strip()

                region_counts[region] = (
                    region_counts.get(
                        region,
                        0,
                    )
                    + 1
                )

            # -------------------------------------------------
            # WOREDA
            # -------------------------------------------------

            if (
                profile.region
                and profile.woreda
            ):

                region = profile.region.strip()
                woreda = profile.woreda.strip()

                key = (
                    region,
                    woreda,
                )

                woreda_counts[key] = (
                    woreda_counts.get(
                        key,
                        0,
                    )
                    + 1
                )

            # -------------------------------------------------
            # KEBELE
            # -------------------------------------------------

            if (
                profile.region
                and profile.woreda
                and profile.kebele
            ):

                region = profile.region.strip()
                woreda = profile.woreda.strip()
                kebele = profile.kebele.strip()

                key = (
                    region,
                    woreda,
                    kebele,
                )

                kebele_counts[key] = (
                    kebele_counts.get(
                        key,
                        0,
                    )
                    + 1
                )

        # -------------------------------------------------
        # FORMAT REGION RESULTS
        # -------------------------------------------------

        by_region = [
            {
                "region": region,
                "count": count,
            }
            for region, count
            in sorted(
                region_counts.items()
            )
        ]

        # -------------------------------------------------
        # FORMAT WOREDA RESULTS
        # -------------------------------------------------

        by_woreda = [
            {
                "region": region,
                "woreda": woreda,
                "count": count,
            }
            for (
                region,
                woreda,
            ), count
            in sorted(
                woreda_counts.items()
            )
        ]

        # -------------------------------------------------
        # FORMAT KEBELE RESULTS
        # -------------------------------------------------

        by_kebele = [
            {
                "region": region,
                "woreda": woreda,
                "kebele": kebele,
                "count": count,
            }
            for (
                region,
                woreda,
                kebele,
            ), count
            in sorted(
                kebele_counts.items()
            )
        ]

        # -------------------------------------------------
        # FORMAT DISEASE RESULTS
        # -------------------------------------------------

        by_disease = [
            {
                "disease_class": disease,
                "count": count,
            }
            for disease, count
            in sorted(
                disease_counts.items()
            )
        ]

        # -------------------------------------------------
        # FORMAT DAILY TRENDS
        # -------------------------------------------------

        trends = [
            {
                "date": date,
                "count": count,
            }
            for date, count
            in sorted(
                daily_counts.items()
            )
        ]

        return {
            "filters": {
                "disease_class": (
                    normalized_disease_class
                    if normalized_disease_class
                    else None
                ),
                "start_date": start_date,
                "end_date": end_date,
            },
            "summary": {
                "total_diagnoses": total_diagnoses,
                "diseased_cases": diseased_cases,
                "healthy_cases": healthy_cases,
            },
            "by_region": by_region,
            "by_woreda": by_woreda,
            "by_kebele": by_kebele,
            "by_disease": by_disease,
            "trends": trends,
        }

    # =====================================================
    # GLOBAL GEO-DISEASE CASES
    # =====================================================

    @classmethod
    def get_geo_disease_cases(
        cls,
        disease_class: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        include_coverage: bool = False,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """
        Retrieve geographically located diagnosis cases
        across all farmer regions.

        Only diagnosis records belonging to farmers with
        both latitude and longitude are returned.
        """

        query, _ = cls._apply_diagnosis_filters(
            DiagnosisRecord.query,
            disease_class=disease_class,
            start_date=start_date,
            end_date=end_date,
        )

        diagnoses = (
            query
            .order_by(
                DiagnosisRecord.created_at.desc()
            )
            .all()
        )

        cases: list[dict[str, Any]] = []
        total_farmer_diagnoses = 0
        unlocated_diagnoses = 0
        region_coverage: dict[str, dict[str, int]] = {}

        # -------------------------------------------------
        # BUILD GEO CASES
        # -------------------------------------------------

        for diagnosis in diagnoses:

            if diagnosis.user_id is None:
                continue

            user = db.session.get(
                User,
                diagnosis.user_id,
            )

            if user is None:
                continue

            # Only farmers can appear on farmer disease map.
            if user.role != "farmer":
                continue

            total_farmer_diagnoses += 1

            profile = (
                FarmerProfile.query
                .filter_by(
                    user_id=user.id
                )
                .first()
            )

            region_name = (
                profile.region.strip()
                if profile and profile.region
                else "Unknown region"
            )
            coverage = region_coverage.setdefault(
                region_name,
                {"total_diagnoses": 0, "mapped_cases": 0, "missing_coordinates": 0},
            )
            coverage["total_diagnoses"] += 1

            # Both coordinates are required.
            if profile is None or (
                profile.latitude is None
                or profile.longitude is None
            ):
                unlocated_diagnoses += 1
                coverage["missing_coordinates"] += 1
                continue

            coverage["mapped_cases"] += 1

            cases.append(
                {
                    "diagnosis_id": diagnosis.id,
                    "farmer_id": user.id,
                    "farmer_name": user.full_name,
                    "disease_class": (
                        diagnosis.disease_class
                    ),
                    "confidence": (
                        float(diagnosis.confidence)
                        if diagnosis.confidence is not None
                        else None
                    ),
                    "latitude": float(
                        profile.latitude
                    ),
                    "longitude": float(
                        profile.longitude
                    ),
                    "region": profile.region,
                    "woreda": profile.woreda,
                    "kebele": profile.kebele,
                    "created_at": (
                        diagnosis.created_at.isoformat()
                        if diagnosis.created_at
                        else None
                    ),
                }
            )

        if not include_coverage:
            return cases

        return {
            "cases": cases,
            "summary": {
                "total_farmer_diagnoses": total_farmer_diagnoses,
                "mapped_cases": len(cases),
                "missing_coordinates": unlocated_diagnoses,
                "by_region": [
                    {"region": region, **counts}
                    for region, counts in sorted(region_coverage.items())
                ],
            },
        }

    # =====================================================
    # ADMIN DASHBOARD
    # =====================================================

    @classmethod
    def get_dashboard_statistics(
        cls,
    ) -> dict[str, Any]:
        """
        Generate the complete administrator dashboard.

        This method intentionally reuses the existing
        regional-statistics and geo-disease functionality
        instead of duplicating those calculations.
        """

        # -------------------------------------------------
        # USER COUNTS
        # -------------------------------------------------

        total_users = User.query.count()

        total_farmers = (
            User.query
            .filter_by(role="farmer")
            .count()
        )

        total_extension_agents = (
            User.query
            .filter_by(role="extension_agent")
            .count()
        )

        total_admins = (
            User.query
            .filter_by(role="admin")
            .count()
        )

        active_users = (
            User.query
            .filter_by(is_active=True)
            .count()
        )

        inactive_users = (
            User.query
            .filter_by(is_active=False)
            .count()
        )

        # -------------------------------------------------
        # DIAGNOSIS COUNTS
        # -------------------------------------------------

        total_diagnoses = (
            DiagnosisRecord.query.count()
        )

        # -------------------------------------------------
        # DISEASE DISTRIBUTION
        # -------------------------------------------------

        disease_rows = (
            db.session.query(
                DiagnosisRecord.disease_class,
                db.func.count(
                    DiagnosisRecord.id
                ),
            )
            .group_by(
                DiagnosisRecord.disease_class
            )
            .all()
        )

        disease_counts: dict[str, int] = {}

        for disease_class, count in disease_rows:

            disease_counts[
                disease_class
            ] = count

        # -------------------------------------------------
        # HEALTHY / DISEASED SUMMARY
        # -------------------------------------------------

        healthy_cases = 0
        diseased_cases = 0

        for disease_class, count in disease_rows:

            if (
                disease_class
                and disease_class.strip().lower()
                == "healthy"
            ):
                healthy_cases += count
            else:
                diseased_cases += count

        # -------------------------------------------------
        # OTHER SYSTEM COUNTS
        # -------------------------------------------------

        total_advisories = (
            AdvisoryRecord.query.count()
        )

        total_comments = (
            ExtensionComment.query.count()
        )

        # -------------------------------------------------
        # RECENT DIAGNOSES
        # -------------------------------------------------

        recent_diagnoses = (
            DiagnosisRecord.query
            .order_by(
                DiagnosisRecord.created_at.desc()
            )
            .limit(10)
            .all()
        )

        recent_diagnoses_data = [
            cls.diagnosis_to_dict(
                diagnosis
            )
            for diagnosis in recent_diagnoses
        ]

        # -------------------------------------------------
        # RECENT USERS
        # -------------------------------------------------

        recent_users = (
            User.query
            .order_by(
                User.created_at.desc()
            )
            .limit(10)
            .all()
        )

        recent_users_data = [
            cls.user_to_dict(user)
            for user in recent_users
        ]

        # -------------------------------------------------
        # REUSE COMPONENT 8 REGIONAL STATISTICS
        # -------------------------------------------------

        regional_statistics = (
            cls.get_regional_statistics()
        )

        # -------------------------------------------------
        # REUSE COMPONENT 8 GEO-DISEASE DATA
        # -------------------------------------------------

        geo_disease_cases = (
            cls.get_geo_disease_cases()
        )

        # -------------------------------------------------
        # FINAL DASHBOARD RESPONSE
        # -------------------------------------------------

        return {
            "users": {
                "total": total_users,
                "farmers": total_farmers,
                "extension_agents": (
                    total_extension_agents
                ),
                "admins": total_admins,
                "active": active_users,
                "inactive": inactive_users,
            },

            "diagnoses": {
                "total": total_diagnoses,
                "healthy": healthy_cases,
                "diseased": diseased_cases,
                "by_disease": disease_counts,
            },

            "advisories": {
                "total": total_advisories,
            },

            "extension_comments": {
                "total": total_comments,
            },

            "regional_statistics": (
                regional_statistics
            ),

            "geo_disease_cases": {
                "total_mapped_cases": len(
                    geo_disease_cases
                ),
                "cases": geo_disease_cases,
            },

            "recent_diagnoses": (
                recent_diagnoses_data
            ),

            "recent_users": (
                recent_users_data
            ),
        }
