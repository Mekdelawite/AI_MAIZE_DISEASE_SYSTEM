"""
=========================================================
Farmer Advisory Response Service
=========================================================

Converts structured AdvisorService information into a
clean farmer-facing advisory response.

The service does NOT generate new agricultural advice.
All disease information comes from the Knowledge Base
through AdvisorService.

Supported languages:
    en = English
    am = Amharic

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from __future__ import annotations

from typing import Any

from ml_model.advisor.advisor_service import AdvisorService
from ml_model.advisor.response_models import AdvisoryResponse


class AdvisoryResponseError(Exception):
    """Base exception for advisory response errors."""


class AdvisoryResponseService:
    """
    Builds farmer-facing responses from AdvisorService.

    The underlying agricultural information remains
    knowledge-base grounded.
    """

    SUPPORTED_LANGUAGES = (
        "en",
        "am",
    )

    def __init__(
        self,
        advisor_service: AdvisorService | None = None,
    ) -> None:

        self._advisor = (
            advisor_service
            if advisor_service is not None
            else AdvisorService()
        )

    # =====================================================
    # LANGUAGE
    # =====================================================

    def _validate_language(
        self,
        language: str,
    ) -> str:
        """
        Validate and normalize language.
        """

        if not isinstance(language, str):

            raise AdvisoryResponseError(
                "Language must be a string."
            )

        language = language.strip().lower()

        if language not in self.SUPPORTED_LANGUAGES:

            raise AdvisoryResponseError(
                "Unsupported language: "
                f"{language}. "
                "Supported languages: "
                f"{', '.join(self.SUPPORTED_LANGUAGES)}"
            )

        return language

    def get_supported_languages(self) -> list[str]:
        """
        Return supported language codes.
        """

        return list(
            self.SUPPORTED_LANGUAGES
        )

    # =====================================================
    # DISCLAIMER
    # =====================================================

    @staticmethod
    def _get_disclaimer(
        language: str,
        validation: dict[str, Any],
    ) -> str:
        """
        Generate a transparent validation disclaimer.

        The disclaimer reflects the actual validation
        metadata and does not claim expert validation
        when it has not occurred.
        """

        expert_validated = bool(
            validation.get(
                "expert_validated",
                False,
            )
        )

        if expert_validated:
            return ""

        if language == "am":

            return (
                "ይህ መረጃ በስርዓቱ የእውቀት መሠረት "
                "ላይ የተመሠረተ ነው። የባለሙያ "
                "ማረጋገጫ ገና እየተጠበቀ ነው። "
                "ለተጨማሪ የሙያ ምክር የግብርና "
                "ባለሙያን ያማክሩ።"
            )

        return (
            "This information is based on the system's "
            "structured agricultural knowledge base. "
            "Expert validation is still pending. "
            "Consult an agricultural professional for "
            "additional professional advice."
        )

    # =====================================================
    # SAFE LIST CONVERSION
    # =====================================================

    @staticmethod
    def _list_value(
        value: Any,
    ) -> list[str]:
        """
        Safely convert an advisory field into a list
        of strings.
        """

        if value is None:

            return []

        if isinstance(value, list):

            return [
                str(item)
                for item in value
                if item is not None
            ]

        return [str(value)]

    # =====================================================
    # RESPONSE BUILDING
    # =====================================================

    def _build_response(
        self,
        advisory: dict[str, Any],
        language: str,
        confidence: float | None = None,
        class_name: str | None = None,
    ) -> AdvisoryResponse:
        """
        Convert AdvisorService output into an
        AdvisoryResponse object.

        Source information is retrieved separately from
        AdvisorService so that the response layer preserves
        the Knowledge Base source metadata.
        """

        validation: dict[str, Any] = {}

        if class_name:

            try:

                validation = dict(
                    self._advisor.get_validation_status(
                        class_name
                    )
                )

            except Exception:

                validation = {}

        sources: list[dict[str, Any]] = []

        if class_name:

            try:

                sources = list(
                    self._advisor.get_sources(
                        class_name
                    )
                )

            except Exception:

                sources = []

        return AdvisoryResponse(

            language=language,

            disease=str(
                advisory.get(
                    "disease",
                    "",
                )
            ),

            scientific_name=advisory.get(
                "scientific_name"
            ),

            confidence=confidence,

            severity=str(
                advisory.get(
                    "severity",
                    "",
                )
            ),

            description=str(
                advisory.get(
                    "description",
                    "",
                )
            ),

            symptoms=self._list_value(
                advisory.get(
                    "symptoms",
                    [],
                )
            ),

            causes=self._list_value(
                advisory.get(
                    "causes",
                    [],
                )
            ),

            favorable_conditions=self._list_value(
                advisory.get(
                    "favorable_conditions",
                    [],
                )
            ),

            prevention=self._list_value(
                advisory.get(
                    "prevention",
                    [],
                )
            ),

            management=self._list_value(
                advisory.get(
                    "management",
                    [],
                )
            ),

            sources=sources,

            validation=validation,

            disclaimer=self._get_disclaimer(
                language,
                validation,
            ),
        )

    # =====================================================
    # DISEASE ADVISORY
    # =====================================================

    def get_advisory(
        self,
        class_name: str,
        language: str = "en",
        confidence: float | None = None,
    ) -> AdvisoryResponse:
        """
        Generate a structured farmer advisory.

        Parameters
        ----------
        class_name:
            Model disease class name.

        language:
            'en' or 'am'.

        confidence:
            Optional prediction confidence from the
            DiseasePredictor.

        Returns
        -------
        AdvisoryResponse
        """

        language = self._validate_language(
            language
        )

        try:

            advisory = self._advisor.get_advice(
                class_name=class_name,
                language=language,
            )

        except Exception as error:

            raise AdvisoryResponseError(
                "Unable to retrieve advisory information: "
                f"{error}"
            ) from error

        if not isinstance(advisory, dict):

            raise AdvisoryResponseError(
                "AdvisorService returned an invalid "
                "advisory response."
            )

        return self._build_response(
            advisory=advisory,
            language=language,
            confidence=confidence,
            class_name=class_name,
        )

    # =====================================================
    # DIAGNOSIS-BASED ADVISORY
    # =====================================================

    def from_diagnosis(
        self,
        diagnosis: dict[str, Any],
        language: str = "en",
    ) -> AdvisoryResponse:
        """
        Build advisory information directly from a
        DiseasePredictor / DiagnosisService result.

        Expected structure:

            {
                "prediction": {
                    "class_name": "Blight",
                    "confidence": 89.47
                }
            }

        The disease class is taken from the prediction,
        while all advisory content comes from the
        Knowledge Base through AdvisorService.
        """

        language = self._validate_language(
            language
        )

        if not isinstance(diagnosis, dict):

            raise AdvisoryResponseError(
                "Diagnosis must be a dictionary."
            )

        prediction = diagnosis.get(
            "prediction"
        )

        if not isinstance(
            prediction,
            dict,
        ):

            raise AdvisoryResponseError(
                "Diagnosis does not contain a valid "
                "'prediction' object."
            )

        class_name = prediction.get(
            "class_name"
        )

        if not class_name:

            raise AdvisoryResponseError(
                "Prediction does not contain "
                "'class_name'."
            )

        confidence = prediction.get(
            "confidence"
        )

        if confidence is not None:

            try:

                confidence = float(
                    confidence
                )

            except (
                TypeError,
                ValueError,
            ):

                confidence = None

        return self.get_advisory(
            class_name=str(
                class_name
            ),
            language=language,
            confidence=confidence,
        )

    # =====================================================
    # SERIALIZATION
    # =====================================================

    def get_advisory_dict(
        self,
        class_name: str,
        language: str = "en",
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """
        Return advisory information as a dictionary.
        """

        response = self.get_advisory(
            class_name=class_name,
            language=language,
            confidence=confidence,
        )

        return response.to_dict()

    # =====================================================
    # HEALTH CHECK
    # =====================================================

    def is_ready(self) -> bool:
        """
        Check whether the underlying AdvisorService
        is ready.
        """

        try:

            return bool(
                self._advisor.is_ready()
            )

        except Exception:

            return False

    def health_check(self) -> dict[str, Any]:
        """
        Return service health information.
        """

        return {

            "service": (
                "AdvisoryResponseService"
            ),

            "ready": self.is_ready(),

            "supported_languages": (
                self.get_supported_languages()
            ),

        }