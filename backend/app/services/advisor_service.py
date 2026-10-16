"""
=========================================================
Backend Advisor Integration Service
=========================================================

Connects the Flask backend with the already-tested
AI Maize Disease Advisor system.

The backend does not implement advisory logic itself.
It delegates advisory generation to:

    ml_model.advisor.response_service.AdvisoryResponseService

Responsibilities:
    - Initialize AdvisoryResponseService
    - Check service readiness
    - Validate disease/class input
    - Generate farmer advisory
    - Support English and Amharic
    - Preserve confidence from diagnosis
    - Optionally persist advisory results to PostgreSQL
    - Return structured advisory data

=========================================================
"""

from __future__ import annotations

from typing import Any

from backend.app.extensions import db
from backend.app.models.advisory_record import AdvisoryRecord


# =========================================================
# EXCEPTION
# =========================================================

class BackendAdvisorError(Exception):
    """
    Base exception for backend advisor errors.
    """


# =========================================================
# SERVICE
# =========================================================

class AdvisorIntegrationService:
    """
    Integration layer between Flask and the existing
    AI Maize Disease Advisory system.

    The service delegates all advisory knowledge and
    generation to AdvisoryResponseService.

    Database persistence is optional and controlled
    through the 'persist' parameter.
    """

    def __init__(self) -> None:

        self._response_service = None

        self._initialize()

    # =====================================================
    # INITIALIZATION
    # =====================================================

    def _initialize(self) -> None:
        """
        Initialize the existing AdvisoryResponseService.
        """

        try:

            from ml_model.advisor.response_service import (
                AdvisoryResponseService,
            )

            self._response_service = (
                AdvisoryResponseService()
            )

        except Exception as error:

            raise BackendAdvisorError(
                "Unable to initialize "
                "AdvisoryResponseService: "
                f"{error}"
            ) from error

    # =====================================================
    # READINESS
    # =====================================================

    def is_ready(self) -> bool:
        """
        Check whether the advisory response service
        is ready.
        """

        if self._response_service is None:

            return False

        try:

            return bool(
                self._response_service.is_ready()
            )

        except Exception:

            return False

    # =====================================================
    # SUPPORTED LANGUAGES
    # =====================================================

    def get_supported_languages(self) -> list[str]:
        """
        Return the languages supported by the
        advisory service.
        """

        if not self.is_ready():

            raise BackendAdvisorError(
                "Advisory service is not ready."
            )

        try:

            return list(
                self._response_service
                .get_supported_languages()
            )

        except Exception as error:

            raise BackendAdvisorError(
                "Unable to retrieve supported languages: "
                f"{error}"
            ) from error

    # =====================================================
    # DATABASE PERSISTENCE
    # =====================================================

    def _save_advisory_record(
        self,
        advisory: dict[str, Any],
        language: str,
        diagnosis_id: int | None = None,
        user_id: int | None = None,
    ) -> AdvisoryRecord:
        """
        Save a generated advisory to PostgreSQL.

        The AdvisoryResponseService returns a structured
        response where the main farmer-facing advisory
        description is stored in the 'description' field.

        The PostgreSQL AdvisoryRecord model stores this
        value in the 'advisory_text' column.
        """

        # -------------------------------------------------
        # VALIDATE ADVISORY
        # -------------------------------------------------

        if not isinstance(
            advisory,
            dict,
        ):

            raise BackendAdvisorError(
                "Advisory result must be a dictionary."
            )

        # -------------------------------------------------
        # EXTRACT ADVISORY TEXT
        # -------------------------------------------------

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

        if not advisory_text:

            raise BackendAdvisorError(
                "Advisory response does not contain "
                "advisory description text."
            )

        # -------------------------------------------------
        # SOURCE
        # -------------------------------------------------

        source = advisory.get(
            "source"
        )

        if not source:

            source = (
                "structured_knowledge_base"
            )

        # -------------------------------------------------
        # LANGUAGE
        # -------------------------------------------------

        normalized_language = (
            str(language)
            .lower()
            .strip()
        )

        # -------------------------------------------------
        # CREATE DATABASE RECORD
        # -------------------------------------------------

        record = AdvisoryRecord(

            user_id=user_id,

            diagnosis_id=diagnosis_id,

            language=normalized_language,

            advisory_text=str(
                advisory_text
            ),

            source=str(
                source
            ),
        )

        # -------------------------------------------------
        # DATABASE TRANSACTION
        # -------------------------------------------------

        try:

            db.session.add(
                record
            )

            db.session.commit()

            return record

        except Exception as error:

            db.session.rollback()

            raise BackendAdvisorError(
                "Failed to save advisory to database: "
                f"{error}"
            ) from error

    # =====================================================
    # ADVISORY
    # =====================================================

    def get_advisory(
        self,
        class_name: str,
        language: str = "en",
        confidence: float | None = None,
        diagnosis_id: int | None = None,
        user_id: int | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a structured farmer advisory.

        Parameters
        ----------
        class_name:
            ML disease class name.

        language:
            Advisory language.

        confidence:
            AI prediction confidence.

        diagnosis_id:
            Related diagnosis database ID.

        user_id:
            Related user database ID.

        persist:
            If True, save the advisory to PostgreSQL.
            Default is False.

        Returns
        -------
        dict[str, Any]
            Structured advisory response.
        """

        # -------------------------------------------------
        # SERVICE READY
        # -------------------------------------------------

        if not self.is_ready():

            raise BackendAdvisorError(
                "Advisory service is not ready."
            )

        # -------------------------------------------------
        # VALIDATE CLASS
        # -------------------------------------------------

        if not class_name:

            raise BackendAdvisorError(
                "Disease class name is required."
            )

        # -------------------------------------------------
        # LANGUAGE
        # -------------------------------------------------

        language = (
            str(language)
            .lower()
            .strip()
        )

        supported_languages = (
            self.get_supported_languages()
        )

        if language not in supported_languages:

            raise BackendAdvisorError(
                f"Unsupported language: {language}. "
                f"Supported languages: "
                f"{supported_languages}"
            )

        # -------------------------------------------------
        # CONFIDENCE
        # -------------------------------------------------

        if confidence is not None:

            try:

                confidence = float(
                    confidence
                )

            except (
                TypeError,
                ValueError,
            ) as error:

                raise BackendAdvisorError(
                    "Confidence must be a numeric value."
                ) from error

            if not 0 <= confidence <= 100:

                raise BackendAdvisorError(
                    "Confidence must be between 0 and 100."
                )

        # -------------------------------------------------
        # GENERATE ADVISORY
        # -------------------------------------------------

        try:

            response = (
                self._response_service.get_advisory(
                    class_name=class_name,
                    language=language,
                    confidence=confidence,
                )
            )

        except Exception as error:

            raise BackendAdvisorError(
                "Unable to generate farmer advisory: "
                f"{error}"
            ) from error

        # -------------------------------------------------
        # VALIDATE RESPONSE
        # -------------------------------------------------

        if response is None:

            raise BackendAdvisorError(
                "Advisory service returned no response."
            )

        # -------------------------------------------------
        # SERIALIZE
        # -------------------------------------------------

        try:

            if hasattr(
                response,
                "to_dict",
            ):

                result = response.to_dict()

            elif isinstance(
                response,
                dict,
            ):

                result = response

            else:

                raise BackendAdvisorError(
                    "Unexpected advisory response type: "
                    f"{type(response).__name__}"
                )

        except BackendAdvisorError:

            raise

        except Exception as error:

            raise BackendAdvisorError(
                "Unable to serialize advisory response: "
                f"{error}"
            ) from error

        # -------------------------------------------------
        # OPTIONAL DATABASE PERSISTENCE
        # -------------------------------------------------

        if persist:

            self._save_advisory_record(
                advisory=result,
                language=language,
                diagnosis_id=diagnosis_id,
                user_id=user_id,
            )

        # -------------------------------------------------
        # RETURN RESULT
        # -------------------------------------------------

        return result

    # =====================================================
    # DIAGNOSIS → ADVISORY
    # =====================================================

    def get_advisory_from_diagnosis(
        self,
        diagnosis: dict[str, Any],
        language: str = "en",
        diagnosis_id: int | None = None,
        user_id: int | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        """
        Generate an advisory directly from an AI
        diagnosis result.

        Expected diagnosis structure:

        {
            "prediction": {
                "class_name": "Blight",
                "confidence": 89.47
            }
        }

        Persistence is disabled by default so that the
        complete diagnosis workflow can generate the
        advisory first and save it exactly once after
        obtaining the diagnosis database ID.
        """

        # -------------------------------------------------
        # VALIDATE DIAGNOSIS
        # -------------------------------------------------

        if not isinstance(
            diagnosis,
            dict,
        ):

            raise BackendAdvisorError(
                "Diagnosis result must be a dictionary."
            )

        # -------------------------------------------------
        # GET PREDICTION
        # -------------------------------------------------

        prediction = diagnosis.get(
            "prediction"
        )

        if not isinstance(
            prediction,
            dict,
        ):

            raise BackendAdvisorError(
                "Diagnosis result does not contain "
                "a valid prediction object."
            )

        # -------------------------------------------------
        # EXTRACT PREDICTION
        # -------------------------------------------------

        class_name = prediction.get(
            "class_name"
        )

        confidence = prediction.get(
            "confidence"
        )

        if not class_name:

            raise BackendAdvisorError(
                "Diagnosis prediction does not contain "
                "class_name."
            )

        # -------------------------------------------------
        # GENERATE ADVISORY
        # -------------------------------------------------

        return self.get_advisory(

            class_name=str(
                class_name
            ),

            language=language,

            confidence=confidence,

            diagnosis_id=diagnosis_id,

            user_id=user_id,

            persist=persist,
        )

    # =====================================================
    # SERVICE ACCESS
    # =====================================================

    @property
    def response_service(self):
        """
        Return the underlying AdvisoryResponseService.

        This is provided for future integration layers.
        """

        return self._response_service