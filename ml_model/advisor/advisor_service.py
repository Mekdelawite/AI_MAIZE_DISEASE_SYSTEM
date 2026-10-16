"""
=========================================================
Maize Disease Advisor Service
=========================================================

Provides structured agricultural advisory information
based on the disease identified by the AI diagnosis system.

The Advisor does NOT invent disease information.

It retrieves validated structured information from the
bilingual Knowledge Base.

Supported languages:
    en = English
    am = Amharic

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# =========================================================
# KNOWLEDGE BASE IMPORT
# =========================================================
#
# Import using the complete package path.
# This avoids the problem where Python imports
# ml_model/knowledge_base/__init__.py instead of
# ml_model/knowledge_base/knowledge_base.py.
#

try:

    from ml_model.knowledge_base.knowledge_base import (
        KnowledgeBase,
        DiseaseNotFoundError,
        UnsupportedLanguageError,
    )

except ImportError as error:

    raise ImportError(
        "Unable to import KnowledgeBase.\n"
        "Run this service from the project root:\n\n"
        "    python -m ml_model.advisor.test_advisor_service\n\n"
        f"Original error: {error}"
    ) from error


# =========================================================
# ADVISOR EXCEPTIONS
# =========================================================

class AdvisorError(Exception):
    """
    Base exception for Advisor errors.
    """


class AdvisorNotReadyError(AdvisorError):
    """
    Raised when the Advisor is not ready for use.
    """


class InvalidDiagnosisError(AdvisorError):
    """
    Raised when an invalid diagnosis result is supplied.
    """


class UnsupportedAdvisorLanguageError(AdvisorError):
    """
    Raised when an unsupported language is requested.
    """


# =========================================================
# ADVISOR SERVICE
# =========================================================

class AdvisorService:
    """
    Agricultural advisory service.

    The service receives a disease diagnosis and retrieves
    corresponding agricultural information from the
    Knowledge Base.

    It supports:
        - English
        - Amharic
        - disease information
        - symptoms
        - causes
        - favorable conditions
        - prevention
        - management
        - severity
        - source information
        - validation metadata

    The Advisor does not generate unsupported medical or
    agricultural claims.
    """

    SUPPORTED_LANGUAGES = (
        "en",
        "am",
    )

    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
    ) -> None:

        # -------------------------------------------------
        # Initialize Knowledge Base
        # -------------------------------------------------

        if knowledge_base is not None:

            self._knowledge_base = knowledge_base

        else:

            try:

                self._knowledge_base = (
                    KnowledgeBase()
                )

            except Exception as error:

                raise AdvisorError(
                    "Unable to initialize KnowledgeBase.\n"
                    f"{error}"
                ) from error

        # -------------------------------------------------
        # Readiness check
        # -------------------------------------------------

        if not self._knowledge_base.is_ready():

            raise AdvisorNotReadyError(
                "Knowledge Base is not ready."
            )

    # =====================================================
    # LANGUAGE
    # =====================================================

    def _validate_language(
        self,
        language: str,
    ) -> str:
        """
        Validate and normalize language code.
        """

        if not isinstance(
            language,
            str,
        ):

            raise UnsupportedAdvisorLanguageError(
                "Language must be a string."
            )

        language = (
            language.strip().lower()
        )

        if language not in self.SUPPORTED_LANGUAGES:

            raise UnsupportedAdvisorLanguageError(
                "Unsupported language: "
                f"{language}. "
                "Supported languages: "
                f"{', '.join(self.SUPPORTED_LANGUAGES)}"
            )

        return language

    # =====================================================
    # READINESS
    # =====================================================

    def is_ready(self) -> bool:
        """
        Check whether the Advisor is ready.
        """

        try:

            return (
                self._knowledge_base.is_ready()
            )

        except Exception:

            return False

    # =====================================================
    # BASIC DISEASE ADVICE
    # =====================================================

    def get_advice(
        self,
        class_name: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Retrieve complete advisory information.

        Example:

            advisor.get_advice(
                "Blight",
                "en"
            )
        """

        language = (
            self._validate_language(
                language
            )
        )

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        try:

            advice = (
                self._knowledge_base.get_advice(
                    class_name,
                    language,
                )
            )

        except (
            DiseaseNotFoundError,
            UnsupportedLanguageError,
        ) as error:

            raise AdvisorError(
                str(error)
            ) from error

        return advice

    # =====================================================
    # DISEASE INFORMATION
    # =====================================================

    def get_disease_information(
        self,
        class_name: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Retrieve localized disease information.
        """

        language = (
            self._validate_language(
                language
            )
        )

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        try:

            return (
                self._knowledge_base
                .get_disease_information(
                    class_name,
                    language,
                )
            )

        except (
            DiseaseNotFoundError,
            UnsupportedLanguageError,
        ) as error:

            raise AdvisorError(
                str(error)
            ) from error

    # =====================================================
    # DISEASE INFORMATION BY CLASS ID
    # =====================================================

    def get_disease_information_by_id(
        self,
        class_id: int,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Retrieve disease information using the
        ML model class ID.
        """

        language = (
            self._validate_language(
                language
            )
        )

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        try:

            return (
                self._knowledge_base
                .get_disease_information_by_id(
                    class_id,
                    language,
                )
            )

        except (
            DiseaseNotFoundError,
            UnsupportedLanguageError,
        ) as error:

            raise AdvisorError(
                str(error)
            ) from error

    # =====================================================
    # ADVICE FROM DIAGNOSIS RESULT
    # =====================================================

    def advise_from_diagnosis(
        self,
        diagnosis: dict[str, Any],
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Generate structured advisory information from
        an AI diagnosis result.

        Expected diagnosis format:

            {
                "prediction": {
                    "class_id": 0,
                    "class_name": "Blight",
                    "confidence": 89.47
                }
            }

        The Advisor uses the predicted class_name to
        retrieve information from the Knowledge Base.
        """

        language = (
            self._validate_language(
                language
            )
        )

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        if not isinstance(
            diagnosis,
            dict,
        ):

            raise InvalidDiagnosisError(
                "Diagnosis must be a dictionary."
            )

        # -------------------------------------------------
        # Extract prediction
        # -------------------------------------------------

        prediction = diagnosis.get(
            "prediction"
        )

        if not isinstance(
            prediction,
            dict,
        ):

            raise InvalidDiagnosisError(
                "Diagnosis does not contain a valid "
                "'prediction' object."
            )

        class_name = prediction.get(
            "class_name"
        )

        class_id = prediction.get(
            "class_id"
        )

        confidence = prediction.get(
            "confidence"
        )

        if class_name is None:

            if class_id is None:

                raise InvalidDiagnosisError(
                    "Diagnosis must contain either "
                    "'class_name' or 'class_id'."
                )

            try:

                information = (
                    self.get_disease_information_by_id(
                        class_id,
                        language,
                    )
                )

            except AdvisorError:

                raise

        else:

            information = (
                self.get_disease_information(
                    class_name,
                    language,
                )
            )

        # -------------------------------------------------
        # Build advisory response
        # -------------------------------------------------

        result = {

            "language": language,

            "diagnosis": {

                "class_id": class_id,

                "class_name": class_name,

                "confidence": confidence,
            },

            "advice": information,
        }

        return result

    # =====================================================
    # SOURCE INFORMATION
    # =====================================================

    def get_sources(
        self,
        class_name: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve source information for a disease.
        """

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        try:

            return (
                self._knowledge_base
                .get_sources(
                    class_name
                )
            )

        except DiseaseNotFoundError as error:

            raise AdvisorError(
                str(error)
            ) from error

    # =====================================================
    # VALIDATION INFORMATION
    # =====================================================

    def get_validation_status(
        self,
        class_name: str,
    ) -> dict[str, Any]:
        """
        Retrieve validation metadata for a disease.
        """

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        try:

            return (
                self._knowledge_base
                .get_validation_status(
                    class_name
                )
            )

        except DiseaseNotFoundError as error:

            raise AdvisorError(
                str(error)
            ) from error

    # =====================================================
    # SUPPORTED LANGUAGES
    # =====================================================

    def get_supported_languages(
        self,
    ) -> list[str]:
        """
        Return supported Advisor languages.
        """

        return list(
            self.SUPPORTED_LANGUAGES
        )

    # =====================================================
    # KNOWLEDGE BASE METADATA
    # =====================================================

    def get_knowledge_base_metadata(
        self,
    ) -> dict[str, Any]:
        """
        Return Knowledge Base metadata.
        """

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        return (
            self._knowledge_base
            .get_metadata()
        )

    # =====================================================
    # KNOWLEDGE BASE COUNT
    # =====================================================

    def get_disease_count(
        self,
    ) -> int:
        """
        Return number of diseases in the
        Knowledge Base.
        """

        if not self.is_ready():

            raise AdvisorNotReadyError(
                "Advisor is not ready."
            )

        return (
            self._knowledge_base.count()
        )

    # =====================================================
    # HEALTH CHECK
    # =====================================================

    def health_check(
        self,
    ) -> dict[str, Any]:
        """
        Return Advisor health information.
        """

        ready = self.is_ready()

        return {

            "service": "AdvisorService",

            "ready": ready,

            "supported_languages": (
                self.get_supported_languages()
            ),

            "disease_count": (
                self.get_disease_count()
                if ready
                else 0
            ),
        }


# =========================================================
# END OF FILE
# =========================================================