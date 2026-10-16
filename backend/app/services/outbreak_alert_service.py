"""
=========================================================
Outbreak Alert Service
=========================================================

Coordinates disease outbreak detection, alert creation,
farmer targeting, SMS notification, and alert statistics.

Responsibilities:
    - Analyze outbreak risk using OutbreakDetectionService
    - Create OutbreakAlert records
    - Target eligible farmers by geographic location
    - Respect farmer SMS opt-in settings
    - Respect farmer preferred language
    - Send outbreak SMS notifications
    - Link SMSRecord records to OutbreakAlert
    - Track SMS statistics
    - Support automatic and manual alerts
    - Prevent duplicate automatic alerts

Architecture:

    OutbreakDetectionService
              |
              v
        OutbreakAlertService
              |
        +-----+-----+
        |     |     |
        v     v     v
      Alert  Farmer  SMS
      Model  Target  Service
              |
              v
          SMSRecord

=========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from backend.app.extensions import db
from backend.app.models.outbreak_alert import OutbreakAlert
from backend.app.services.farmer_targeting_service import (
    FarmerTargetingService,
)
from backend.app.services.outbreak_detection_service import (
    OutbreakDetectionService,
)
from backend.app.services.sms_service import SMSService


class OutbreakAlertError(Exception):
    """
    Base exception for outbreak alert service errors.
    """


class OutbreakAlertService:
    """
    Coordinate outbreak detection and farmer notification.

    This service is responsible for orchestration only.

    It does NOT calculate outbreak risk itself.

    Outbreak risk calculation is delegated to:
        OutbreakDetectionService

    Farmer targeting is delegated to:
        FarmerTargetingService

    SMS delivery is delegated to:
        SMSService
    """

    # =====================================================
    # CONFIGURATION
    # =====================================================

    DEFAULT_COOLDOWN_HOURS = 24

    # =====================================================
    # INITIALIZATION
    # =====================================================

    def __init__(
        self,
        detection_service: OutbreakDetectionService | None = None,
        targeting_service: FarmerTargetingService | None = None,
        sms_service: type[SMSService] = SMSService,
    ) -> None:
        """
        Initialize the outbreak alert service.

        Dependencies can be injected for testing.
        """

        self.detection_service = (
            detection_service
            or OutbreakDetectionService()
        )

        self.targeting_service = (
            targeting_service
            or FarmerTargetingService()
        )

        self.sms_service = sms_service

    # =====================================================
    # LOCATION
    # =====================================================

    @staticmethod
    def build_location(
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
    ) -> str:
        """
        Build a human-readable geographic location.

        Examples:

            Amhara

            Amhara, Bahir Dar Zuria

            Amhara, Bahir Dar Zuria, Kebele 03
        """

        parts = [str(region).strip()]

        if woreda:
            parts.append(str(woreda).strip())

        if kebele:
            parts.append(
                f"Kebele {str(kebele).strip()}"
            )

        return ", ".join(parts)

    # =====================================================
    # TARGET FARMERS
    # =====================================================

    def get_target_farmers(
        self,
        *,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return farmers eligible to receive an outbreak SMS.

        FarmerTargetingService handles:

            - farmer role
            - active account
            - phone number
            - SMS opt-in
            - geographic filtering
        """

        return self.targeting_service.find_farmers(
            region=region,
            woreda=woreda,
            kebele=kebele,
        )

    # =====================================================
    # DUPLICATE PROTECTION
    # =====================================================

    @staticmethod
    def has_recent_alert(
        *,
        disease_class: str,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        cooldown_hours: int = DEFAULT_COOLDOWN_HOURS,
    ) -> bool:
        """
        Check whether a recent alert already exists for
        the same disease and geographic scope.

        This prevents automatic detection from sending
        the same outbreak notification repeatedly.
        """

        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(hours=cooldown_hours)
        )

        query = OutbreakAlert.query.filter(
            OutbreakAlert.disease_class
            == disease_class,
            OutbreakAlert.region == region,
            OutbreakAlert.created_at >= cutoff,
            OutbreakAlert.trigger_type == "automatic",
        )

        if woreda is None:
            query = query.filter(
                OutbreakAlert.woreda.is_(None)
            )
        else:
            query = query.filter(
                OutbreakAlert.woreda == woreda
            )

        if kebele is None:
            query = query.filter(
                OutbreakAlert.kebele.is_(None)
            )
        else:
            query = query.filter(
                OutbreakAlert.kebele == kebele
            )

        return query.first() is not None

    # =====================================================
    # CREATE ALERT
    # =====================================================

    def create_alert(
        self,
        *,
        disease_class: str,
        risk_level: str,
        risk_score: float,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        registered_farmers: int = 0,
        affected_farmers: int = 0,
        total_diagnoses: int = 0,
        recent_diagnoses: int = 0,
        total_kebeles: int = 0,
        affected_kebeles: int = 0,
        trigger_type: str = "automatic",
        created_by: int | None = None,
    ) -> OutbreakAlert:
        """
        Create and persist an OutbreakAlert.
        """

        valid_trigger_types = {
            "automatic",
            "manual",
        }

        if trigger_type not in valid_trigger_types:
            raise OutbreakAlertError(
                "Invalid outbreak alert trigger type. "
                "Expected 'automatic' or 'manual'."
            )

        if not disease_class:
            raise OutbreakAlertError(
                "Disease class is required."
            )

        if not region:
            raise OutbreakAlertError(
                "Region is required."
            )

        alert = OutbreakAlert(
            disease_class=str(
                disease_class
            ).strip(),
            risk_level=str(
                risk_level
            ).strip().lower(),
            risk_score=float(risk_score),
            region=str(region).strip(),
            woreda=(
                str(woreda).strip()
                if woreda
                else None
            ),
            kebele=(
                str(kebele).strip()
                if kebele
                else None
            ),
            registered_farmers=int(
                registered_farmers
            ),
            affected_farmers=int(
                affected_farmers
            ),
            total_diagnoses=int(
                total_diagnoses
            ),
            recent_diagnoses=int(
                recent_diagnoses
            ),
            total_kebeles=int(
                total_kebeles
            ),
            affected_kebeles=int(
                affected_kebeles
            ),
            trigger_type=trigger_type,
            status="pending",
            created_by=created_by,
        )

        db.session.add(alert)
        db.session.commit()

        return alert

    # =====================================================
    # SEND ALERT SMS
    # =====================================================

    def send_alert_sms(
        self,
        alert: OutbreakAlert,
    ) -> dict[str, Any]:
        """
        Send an outbreak SMS to all eligible farmers.

        One SMSRecord is created for each farmer.

        Each SMSRecord is linked to the OutbreakAlert using:

            sms_records.outbreak_alert_id
        """

        farmers = self.get_target_farmers(
            region=alert.region,
            woreda=alert.woreda,
            kebele=alert.kebele,
        )

        alert.status = "processing"

        db.session.commit()

        total_recipients = len(farmers)

        sms_sent = 0
        sms_failed = 0
        sms_pending = 0

        location = self.build_location(
            alert.region,
            alert.woreda,
            alert.kebele,
        )

        results: list[dict[str, Any]] = []

        for farmer in farmers:
            try:
                result = (
                    self.sms_service.send_outbreak_alert(
                        recipient_phone=farmer[
                            "phone_number"
                        ],
                        disease_name=alert.disease_class,
                        location=location,
                        language=farmer.get(
                            "preferred_language",
                            "en",
                        ),
                        user_id=farmer.get(
                            "user_id"
                        ),
                        region=alert.region,
                        woreda=alert.woreda,
                        kebele=alert.kebele,
                        outbreak_alert_id=alert.id,
                    )
                )

                results.append(result)

                status = result.get(
                    "status"
                )

                if status in {
                    "sent",
                    "submitted",
                }:
                    sms_sent += 1

                elif status == "failed":
                    sms_failed += 1

                else:
                    sms_pending += 1

            except Exception as exc:
                sms_failed += 1

                results.append(
                    {
                        "success": False,
                        "status": "failed",
                        "phone": farmer.get(
                            "phone_number"
                        ),
                        "error": str(exc),
                    }
                )

        # =================================================
        # UPDATE ALERT STATISTICS
        # =================================================

        alert.total_recipients = (
            total_recipients
        )

        alert.sms_sent = sms_sent
        alert.sms_failed = sms_failed
        alert.sms_pending = sms_pending

        if total_recipients == 0:
            alert.status = "no_recipients"

        elif sms_sent == total_recipients:
            alert.status = "sent"

        elif sms_sent > 0:
            alert.status = "partially_sent"

        elif sms_failed == total_recipients:
            alert.status = "failed"

        else:
            alert.status = "pending"

        if sms_sent > 0:
            alert.sent_at = (
                datetime.now(timezone.utc)
            )

        alert.updated_at = (
            datetime.now(timezone.utc)
        )

        db.session.commit()

        return {
            "success": sms_sent > 0,
            "alert_id": alert.id,
            "status": alert.status,
            "total_recipients": total_recipients,
            "sms_sent": sms_sent,
            "sms_failed": sms_failed,
            "sms_pending": sms_pending,
            "results": results,
        }

    # =====================================================
    # AUTOMATIC ALERT
    # =====================================================

    def process_automatic_alert(
        self,
        *,
        disease_class: str,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        analysis_period_days: int = 7,
        recent_period_days: int = 2,
        cooldown_hours: int = DEFAULT_COOLDOWN_HOURS,
    ) -> dict[str, Any]:
        """
        Analyze an area and automatically send an outbreak
        alert when the detection service determines that
        an alert is required.
        """

        # =================================================
        # ANALYZE OUTBREAK
        # =================================================

        analysis = (
    self.detection_service.analyze_area(
        disease_class=disease_class,
        region=region,
        woreda=woreda,
        kebele=kebele,
        days=analysis_period_days,
        recent_days=recent_period_days,
    )
)

        # =================================================
        # NO ALERT REQUIRED
        # =================================================

        if not analysis.get(
            "alert_required",
            False,
        ):
            return {
                "success": True,
                "alert_created": False,
                "alert_required": False,
                "analysis": analysis,
            }

        # =================================================
        # DUPLICATE PROTECTION
        # =================================================

        if self.has_recent_alert(
            disease_class=disease_class,
            region=region,
            woreda=woreda,
            kebele=kebele,
            cooldown_hours=cooldown_hours,
        ):
            return {
                "success": True,
                "alert_created": False,
                "duplicate": True,
                "analysis": analysis,
            }

        # =================================================
        # CREATE ALERT
        # =================================================

        alert = self.create_alert(
            disease_class=disease_class,
            risk_level=analysis[
                "risk_level"
            ],
            risk_score=analysis[
                "outbreak_risk_score"
            ],
            region=region,
            woreda=woreda,
            kebele=kebele,
            registered_farmers=analysis[
                "registered_farmers"
            ],
            affected_farmers=analysis[
                "affected_farmers"
            ],
            total_diagnoses=analysis[
                "total_diagnoses"
            ],
            recent_diagnoses=analysis[
                "recent_diagnoses"
            ],
            total_kebeles=analysis[
                "total_kebeles"
            ],
            affected_kebeles=analysis[
                "affected_kebeles"
            ],
            trigger_type="automatic",
        )

        # =================================================
        # SEND SMS
        # =================================================

        notification = self.send_alert_sms(
            alert
        )

        return {
            "success": notification[
                "success"
            ],
            "alert_created": True,
            "duplicate": False,
            "analysis": analysis,
            "alert_id": alert.id,
            "notification": notification,
        }

    # =====================================================
    # MANUAL ADMIN ALERT
    # =====================================================

    def process_manual_alert(
        self,
        *,
        disease_class: str,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        risk_level: str = "high",
        risk_score: float = 0.0,
        created_by: int | None = None,
    ) -> dict[str, Any]:
        """
        Create and send an outbreak alert manually.

        Manual alerts do NOT require the automatic outbreak
        threshold to be reached.

        This allows an administrator to notify farmers when
        an outbreak is confirmed through field reports,
        extension agents, or other trusted information.
        """

        alert = self.create_alert(
            disease_class=disease_class,
            risk_level=risk_level,
            risk_score=risk_score,
            region=region,
            woreda=woreda,
            kebele=kebele,
            trigger_type="manual",
            created_by=created_by,
        )

        notification = self.send_alert_sms(
            alert
        )

        return {
            "success": notification[
                "success"
            ],
            "alert_created": True,
            "alert_id": alert.id,
            "notification": notification,
        }

    # =====================================================
    # GET ALERT
    # =====================================================

    @staticmethod
    def get_alert(
        alert_id: int,
    ) -> OutbreakAlert | None:
        """
        Retrieve an outbreak alert by ID.
        """

        return db.session.get(
            OutbreakAlert,
            alert_id,
        )

    # =====================================================
    # ALERT SUMMARY
    # =====================================================

    @staticmethod
    def serialize_alert(
        alert: OutbreakAlert,
    ) -> dict[str, Any]:
        """
        Convert an OutbreakAlert model into a JSON-friendly
        dictionary.
        """

        return {
            "id": alert.id,
            "disease_class": (
                alert.disease_class
            ),
            "risk_level": alert.risk_level,
            "risk_score": alert.risk_score,
            "region": alert.region,
            "woreda": alert.woreda,
            "kebele": alert.kebele,
            "registered_farmers": (
                alert.registered_farmers
            ),
            "affected_farmers": (
                alert.affected_farmers
            ),
            "total_diagnoses": (
                alert.total_diagnoses
            ),
            "recent_diagnoses": (
                alert.recent_diagnoses
            ),
            "total_kebeles": (
                alert.total_kebeles
            ),
            "affected_kebeles": (
                alert.affected_kebeles
            ),
            "trigger_type": (
                alert.trigger_type
            ),
            "status": alert.status,
            "total_recipients": (
                alert.total_recipients
            ),
            "sms_sent": alert.sms_sent,
            "sms_failed": alert.sms_failed,
            "sms_pending": alert.sms_pending,
            "created_by": alert.created_by,
            "created_at": (
                alert.created_at.isoformat()
                if alert.created_at
                else None
            ),
            "sent_at": (
                alert.sent_at.isoformat()
                if alert.sent_at
                else None
            ),
            "updated_at": (
                alert.updated_at.isoformat()
                if alert.updated_at
                else None
            ),
        }