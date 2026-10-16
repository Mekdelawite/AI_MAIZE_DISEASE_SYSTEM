"""
=========================================================
Diagnosis + Advisory Integration Service
=========================================================

Coordinates the complete farmer diagnosis workflow.

Responsibilities:

    1. Run AI maize disease diagnosis.
    2. Save diagnosis result to PostgreSQL.
    3. Extract predicted disease and confidence.
    4. Generate the corresponding farmer advisory.
    5. Save advisory linked to the diagnosis and user.
    6. Return the complete structured result.

This service does not implement ML inference or advisory
knowledge itself.

It delegates to:

    DiagnosisIntegrationService
    AdvisorIntegrationService

=========================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.extensions import db

from backend.app.models.advisory_record import (
    AdvisoryRecord,
)

from backend.app.services.advisor_service import (
    AdvisorIntegrationService,
    BackendAdvisorError,
)

from backend.app.services.diagnosis_service import (
    BackendDiagnosisError,
    DiagnosisIntegrationService,
)


# =========================================================
# EXCEPTION
# =========================================================

class DiagnosisAdvisoryError(Exception):
    """
    Base exception for diagnosis + advisory integration
    errors.
    """


_ADVISORY_PAYLOAD_MARKER = "\n\n__MAIZECARE_ADVISORY_PAYLOAD_V1__\n"


# =========================================================
# SERVICE
# =========================================================

class DiagnosisAdvisoryIntegrationService:
    """
    Coordinate AI diagnosis and farmer advisory generation.

    Workflow:

        Image
          ↓
        AI Diagnosis
          ↓
        PostgreSQL Diagnosis Record
          ↓
        Advisory Generation
          ↓
        PostgreSQL Advisory Record
          ↓
        Complete API Response
    """

    def __init__(self) -> None:

        self._diagnosis_service = (
            DiagnosisIntegrationService()
        )

        self._advisor_service = (
            AdvisorIntegrationService()
        )

    # =====================================================
    # READINESS
    # =====================================================

    def is_ready(self) -> bool:
        """
        Return True only when both services are ready.
        """

        try:

            return (
                self._diagnosis_service.is_ready()
                and self._advisor_service.is_ready()
            )

        except Exception:

            return False

    # =====================================================
    # ADVISORY DATABASE PERSISTENCE
    # =====================================================

    def _save_advisory_record(
        self,
        advisory: dict[str, Any],
        diagnosis_id: int,
        language: str,
        user_id: int | None = None,
    ) -> AdvisoryRecord:
        """
        Save the generated advisory to PostgreSQL.

        The advisory is linked to:

            - the diagnosis
            - the authenticated user
            - the selected language

        Parameters
        ----------
        advisory:
            Structured advisory result.

        diagnosis_id:
            ID of the related diagnosis record.

        language:
            Advisory language.

        user_id:
            Authenticated farmer/user ID.
        """

        # =================================================
        # VALIDATE ADVISORY
        # =================================================

        if not isinstance(
            advisory,
            dict,
        ):

            raise DiagnosisAdvisoryError(
                "Advisory result must be a dictionary."
            )

        # =================================================
        # EXTRACT ADVISORY TEXT
        # =================================================

        advisory_text = advisory.get(
            "description"
        )

        # -------------------------------------------------
        # BACKWARD COMPATIBILITY
        # -------------------------------------------------

        if not advisory_text:

            advisory_text = advisory.get(
                "advisory_text"
            )

        if not advisory_text:

            advisory_text = advisory.get(
                "text"
            )

        # =================================================
        # VALIDATE ADVISORY TEXT
        # =================================================

        if not advisory_text:

            raise DiagnosisAdvisoryError(
                "Advisory result does not contain "
                "description text."
            )

        # Keep the farmer-readable text first for compatibility, and persist
        # the full structured response after a marker so history can restore
        # every advisory field without requiring a schema migration.
        structured_fields = {
            "disease",
            "scientific_name",
            "severity",
            "symptoms",
            "causes",
            "favorable_conditions",
            "prevention",
            "management",
            "sources",
            "validation",
            "disclaimer",
        }
        if structured_fields.intersection(advisory):
            advisory_text = (
                f"{advisory_text}{_ADVISORY_PAYLOAD_MARKER}"
                f"{json.dumps(advisory, ensure_ascii=False, default=str)}"
            )

        # =================================================
        # SOURCE
        # =================================================

        source = advisory.get(
            "source"
        )

        if not source:

            source = (
                "structured_knowledge_base"
            )

        # =================================================
        # LANGUAGE
        # =================================================

        normalized_language = (
            str(language)
            .lower()
            .strip()
        )

        if not normalized_language:

            normalized_language = "en"

        # =================================================
        # USER ID VALIDATION
        # =================================================

        normalized_user_id: int | None = None

        if user_id is not None:

            try:

                normalized_user_id = int(
                    user_id
                )

            except (
                TypeError,
                ValueError,
            ) as error:

                raise DiagnosisAdvisoryError(
                    "Authenticated user ID is invalid."
                ) from error

        # =================================================
        # CREATE DATABASE RECORD
        # =================================================

        record = AdvisoryRecord(

            # -------------------------------------------------
            # USER OWNERSHIP
            # -------------------------------------------------

            user_id=normalized_user_id,

            # -------------------------------------------------
            # DIAGNOSIS RELATIONSHIP
            # -------------------------------------------------

            diagnosis_id=diagnosis_id,

            # -------------------------------------------------
            # ADVISORY DATA
            # -------------------------------------------------

            language=normalized_language,

            advisory_text=str(
                advisory_text
            ),

            source=str(
                source
            ),
        )

        # =================================================
        # DATABASE TRANSACTION
        # =================================================

        try:

            db.session.add(
                record
            )

            db.session.commit()

            return record

        except Exception as error:

            db.session.rollback()

            raise DiagnosisAdvisoryError(
                "Failed to save advisory to database: "
                f"{error}"
            ) from error

    # =====================================================
    # DIAGNOSIS + ADVISORY
    # =====================================================

    def diagnose_and_advise(
        self,
        image_path: str | Path,
        language: str = "en",
        explain: bool = False,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Run the complete diagnosis + advisory workflow.

        Parameters
        ----------
        image_path:
            Path to the maize leaf image.

        language:
            Advisory language.

        explain:
            Whether Grad-CAM explanation should be generated.

        user_id:
            Authenticated user ID.

        Returns
        -------
        dict[str, Any]
            Complete diagnosis, advisory, and database
            information.
        """

        # =================================================
        # READINESS
        # =================================================

        if not self.is_ready():

            raise DiagnosisAdvisoryError(
                "Diagnosis and advisory services "
                "are not ready."
            )

        # =================================================
        # VALIDATE IMAGE
        # =================================================

        path = Path(
            image_path
        )

        if not path.exists():

            raise DiagnosisAdvisoryError(
                "Image file not found: "
                f"{path}"
            )

        if not path.is_file():

            raise DiagnosisAdvisoryError(
                "Image path is not a file: "
                f"{path}"
            )

        # =================================================
        # RUN DIAGNOSIS
        # =================================================

        try:

            diagnosis = (
                self._diagnosis_service.diagnose(
                    image_path=path,
                    explain=explain,
                    user_id=user_id,
                )
            )

        except BackendDiagnosisError as error:

            raise DiagnosisAdvisoryError(
                "AI diagnosis failed: "
                f"{error}"
            ) from error

        # =================================================
        # VALIDATE DIAGNOSIS
        # =================================================

        if not isinstance(
            diagnosis,
            dict,
        ):

            raise DiagnosisAdvisoryError(
                "Diagnosis service returned "
                "an invalid result."
            )

        # =================================================
        # PREDICTION
        # =================================================

        prediction = diagnosis.get(
            "prediction"
        )

        if not isinstance(
            prediction,
            dict,
        ):

            raise DiagnosisAdvisoryError(
                "Diagnosis result does not contain "
                "a valid prediction object."
            )

        # =================================================
        # CLASS NAME
        # =================================================

        class_name = prediction.get(
            "class_name"
        )

        if not class_name:

            raise DiagnosisAdvisoryError(
                "Diagnosis result does not contain "
                "a disease class name."
            )

        # =================================================
        # DIAGNOSIS DATABASE ID
        # =================================================

        diagnosis_id = diagnosis.get(
            "database_id"
        )

        if diagnosis_id is None:

            raise DiagnosisAdvisoryError(
                "Diagnosis result does not contain "
                "a database diagnosis ID."
            )

        try:

            diagnosis_id = int(
                diagnosis_id
            )

        except (
            TypeError,
            ValueError,
        ) as error:

            raise DiagnosisAdvisoryError(
                "Diagnosis database ID is invalid."
            ) from error

        # =================================================
        # GENERATE ADVISORY
        # =================================================

        try:

            advisory = (
                self._advisor_service
                .get_advisory_from_diagnosis(
                    diagnosis=diagnosis,
                    language=language,
                    diagnosis_id=diagnosis_id,
                    user_id=user_id,
                )
            )

        except BackendAdvisorError as error:

            raise DiagnosisAdvisoryError(
                "Farmer advisory generation failed: "
                f"{error}"
            ) from error

        # =================================================
        # VALIDATE ADVISORY
        # =================================================

        if not isinstance(
            advisory,
            dict,
        ):

            raise DiagnosisAdvisoryError(
                "Advisory service returned "
                "an invalid result."
            )

        # =================================================
        # SAVE ADVISORY
        # =================================================

        try:

            advisory_record = (
                self._save_advisory_record(
                    advisory=advisory,
                    diagnosis_id=diagnosis_id,
                    language=language,
                    user_id=user_id,
                )
            )

        except DiagnosisAdvisoryError:

            raise

        except Exception as error:

            raise DiagnosisAdvisoryError(
                "Failed to save advisory record: "
                f"{error}"
            ) from error

        # =================================================
        # RETURN COMPLETE RESULT
        # =================================================

        return {

            "diagnosis": diagnosis,

            "advisory": advisory,

            "database": {

                "diagnosis_id": diagnosis_id,

                "advisory_id": (
                    advisory_record.id
                ),

            },

        }

    # =====================================================
    # SERVICE ACCESS
    # =====================================================

    @property
    def diagnosis_service(
        self,
    ) -> DiagnosisIntegrationService:
        """
        Return the underlying diagnosis service.
        """

        return self._diagnosis_service

    @property
    def advisor_service(
        self,
    ) -> AdvisorIntegrationService:
        """
        Return the underlying advisor service.
        """

        return self._advisor_service
