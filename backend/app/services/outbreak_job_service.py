"""
=========================================================
Outbreak Background Job Service
=========================================================

Runs outbreak evaluation outside the farmer-facing
diagnosis request.

Responsibilities:

    - Receive a saved diagnosis ID
    - Load the diagnosis record
    - Load the farmer's location
    - Run automatic outbreak evaluation
    - Keep outbreak failures isolated from diagnosis
    - Return a structured job result

Architecture:

    Diagnosis Request
           |
           v
    DiagnosisRecord
           |
           v
    Background Job
           |
           v
    OutbreakAlertService
           |
           v
    Outbreak Detection
           |
           v
    Alert / SMS

=========================================================
"""

from __future__ import annotations

from typing import Any

from backend.app.extensions import db
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.services.outbreak_alert_service import (
    OutbreakAlertError,
    OutbreakAlertService,
)


class OutbreakJobError(Exception):
    """Base exception for outbreak background job errors."""


class OutbreakJobService:
    """
    Executes outbreak evaluation for a completed diagnosis.

    This service is intentionally independent from the
    farmer-facing diagnosis response.
    """

    def __init__(self) -> None:
        self._outbreak_alert_service = OutbreakAlertService()

    def process_diagnosis(
        self,
        diagnosis_id: int,
    ) -> dict[str, Any]:
        """
        Process outbreak evaluation for one diagnosis.

        Parameters
        ----------
        diagnosis_id:
            ID of an already saved DiagnosisRecord.

        Returns
        -------
        dict
            Structured background-job result.
        """

        try:
            normalized_diagnosis_id = int(diagnosis_id)
        except (TypeError, ValueError) as error:
            raise OutbreakJobError(
                "Diagnosis ID must be a valid integer."
            ) from error

        diagnosis = (
            DiagnosisRecord.query
            .filter_by(id=normalized_diagnosis_id)
            .first()
        )

        if diagnosis is None:
            raise OutbreakJobError(
                f"Diagnosis record {normalized_diagnosis_id} "
                "was not found."
            )

        # -------------------------------------------------
        # Healthy diagnoses do not contribute to outbreaks
        # -------------------------------------------------

        disease_class = (
            str(diagnosis.disease_class).strip()
            if diagnosis.disease_class
            else ""
        )

        if not disease_class:
            return {
                "success": False,
                "evaluated": False,
                "alert_created": False,
                "diagnosis_id": diagnosis.id,
                "reason": "Diagnosis disease class is missing.",
            }

        if disease_class.lower() == "healthy":
            return {
                "success": True,
                "evaluated": False,
                "alert_created": False,
                "diagnosis_id": diagnosis.id,
                "reason": (
                    "Healthy diagnosis does not contribute "
                    "to outbreak detection."
                ),
            }

        # -------------------------------------------------
        # Diagnosis must belong to an authenticated farmer
        # -------------------------------------------------

        if diagnosis.user_id is None:
            return {
                "success": True,
                "evaluated": False,
                "alert_created": False,
                "diagnosis_id": diagnosis.id,
                "reason": (
                    "Diagnosis is not associated with a user."
                ),
            }

        # -------------------------------------------------
        # Load farmer location
        # -------------------------------------------------

        farmer_profile = (
            FarmerProfile.query
            .filter_by(user_id=diagnosis.user_id)
            .first()
        )

        if farmer_profile is None:
            return {
                "success": True,
                "evaluated": False,
                "alert_created": False,
                "diagnosis_id": diagnosis.id,
                "reason": (
                    "Farmer profile/location was not found."
                ),
            }

        if not farmer_profile.region:
            return {
                "success": True,
                "evaluated": False,
                "alert_created": False,
                "diagnosis_id": diagnosis.id,
                "reason": (
                    "Farmer region is not configured."
                ),
            }

        # -------------------------------------------------
        # Run outbreak evaluation
        # -------------------------------------------------

        try:
            result = (
                self._outbreak_alert_service
                .process_automatic_alert(
                    disease_class=disease_class,
                    region=farmer_profile.region,
                    woreda=farmer_profile.woreda,
                    kebele=farmer_profile.kebele,
                )
            )

        except OutbreakAlertError as error:
            db.session.rollback()

            return {
                "success": False,
                "evaluated": True,
                "alert_created": False,
                "diagnosis_id": diagnosis.id,
                "error": str(error),
            }

        except Exception as error:
            db.session.rollback()

            return {
                "success": False,
                "evaluated": True,
                "alert_created": False,
                "diagnosis_id": diagnosis.id,
                "error": (
                    "Outbreak background job failed: "
                    f"{error}"
                ),
            }

        return {
            "success": True,
            "evaluated": True,
            "diagnosis_id": diagnosis.id,
            **result,
        }

    @property
    def outbreak_alert_service(
        self,
    ) -> OutbreakAlertService:
        """Return the outbreak alert service."""

        return self._outbreak_alert_service