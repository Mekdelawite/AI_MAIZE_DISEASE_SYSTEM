"""
=========================================================
Maize Disease Knowledge Base
=========================================================

Provides structured access to the bilingual agricultural
knowledge stored in diseases.json.

Supported languages:
    en = English
    am = Amharic

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    DiseaseRecord,
    LocalizedContent,
    Source,
    Validation,
)


class KnowledgeBaseError(Exception):
    """
    Base exception for knowledge-base errors.
    """


class DiseaseNotFoundError(KnowledgeBaseError):
    """
    Raised when a requested disease cannot be found.
    """


class UnsupportedLanguageError(KnowledgeBaseError):
    """
    Raised when an unsupported language is requested.
    """


class KnowledgeBase:
    """
    Loads and provides access to the maize disease
    knowledge base.

    The JSON file is loaded once when the service is
    initialized.

    Example:

        kb = KnowledgeBase()

        disease = kb.get_disease("Blight")

        print(
            disease.get_display_name("en")
        )
    """

    SUPPORTED_LANGUAGES = (
        "en",
        "am",
    )

    def __init__(
        self,
        data_path: str | Path | None = None,
    ) -> None:

        if data_path is None:

            data_path = (
                Path(__file__).resolve().parent
                / "diseases.json"
            )
   
        self.data_path = Path(data_path)

        self._metadata: dict[str, Any] = {}

        self._diseases: list[DiseaseRecord] = []

        self._by_class_id: dict[
            int,
            DiseaseRecord
        ] = {}

        self._by_class_name: dict[
            str,
            DiseaseRecord
        ] = {}

        self._load()
    # =====================================================
    # LOADING
    # =====================================================

    def _load(self) -> None:
        """
        Load and validate the JSON knowledge base.
        """

        if not self.data_path.exists():

            raise KnowledgeBaseError(
                "Knowledge base file not found: "
                f"{self.data_path}"
            )

        try:

            with self.data_path.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

        except json.JSONDecodeError as error:

            raise KnowledgeBaseError(
                "Invalid JSON in knowledge base: "
                f"{error}"
            ) from error

        except OSError as error:

            raise KnowledgeBaseError(
                "Unable to read knowledge base: "
                f"{error}"
            ) from error

        self._metadata = data.get(
            "metadata",
            {},
        )

        diseases = data.get(
            "diseases",
            [],
        )

        if not isinstance(
            diseases,
            list,
        ):

            raise KnowledgeBaseError(
                "'diseases' must be a list."
            )

        for disease_data in diseases:

            disease = self._create_disease_record(
                disease_data
            )

            self._register_disease(
                disease
            )

    # =====================================================
    # DISEASE CONVERSION
    # =====================================================

    @staticmethod
    def _create_localized_content(
        data: dict[str, Any],
    ) -> LocalizedContent:
        """
        Convert localized JSON content into a
        LocalizedContent object.
        """

        return LocalizedContent(

            description=data.get(
                "description",
                "",
            ),

            symptoms=data.get(
                "symptoms",
                [],
            ),

            causes=data.get(
                "causes",
                [],
            ),

            favorable_conditions=data.get(
                "favorable_conditions",
                [],
            ),

            prevention=data.get(
                "prevention",
                [],
            ),

            management=data.get(
                "management",
                [],
            ),

            severity=data.get(
                "severity",
                "",
            ),
        )

    @staticmethod
    def _create_source(
        data: dict[str, Any],
    ) -> Source:
        """
        Convert source JSON data into a Source object.
        """

        return Source(

            title=data.get(
                "title",
                "",
            ),

            organization=data.get(
                "organization",
                "",
            ),

            source_type=data.get(
                "source_type",
                "",
            ),

            url=data.get(
                "url",
                "",
            ),

            year=data.get(
                "year"
            ),

            notes=data.get(
                "notes",
                "",
            ),
        )

    @staticmethod
    def _create_validation(
        data: dict[str, Any],
    ) -> Validation:
        """
        Convert validation JSON data into a
        Validation object.
        """

        return Validation(

            status=data.get(
                "status",
                "",
            ),

            method=data.get(
                "method",
                "",
            ),

            expert_validated=data.get(
                "expert_validated",
                False,
            ),

            reviewer=data.get(
                "reviewer"
            ),

            date=data.get(
                "date"
            ),

            notes=data.get(
                "notes",
                "",
            ),
        )

    def _create_disease_record(
        self,
        data: dict[str, Any],
    ) -> DiseaseRecord:
        """
        Convert one JSON disease object into a
        DiseaseRecord.
        """

        try:

            english = (
                self._create_localized_content(
                    data["english"]
                )
            )

            amharic = (
                self._create_localized_content(
                    data["amharic"]
                )
            )

            sources = [

                self._create_source(
                    source
                )

                for source in data.get(
                    "sources",
                    [],
                )
            ]

            validation = (
                self._create_validation(
                    data.get(
                        "validation",
                        {},
                    )
                )
            )

            return DiseaseRecord(

                class_id=int(
                    data["class_id"]
                ),

                class_name=str(
                    data["class_name"]
                ),

                display_name_en=str(
                    data["display_name_en"]
                ),

                display_name_am=str(
                    data["display_name_am"]
                ),

                scientific_name=data.get(
                    "scientific_name"
                ),

                english=english,

                amharic=amharic,

                sources=sources,

                validation=validation,
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as error:

            raise KnowledgeBaseError(
                "Invalid disease record: "
                f"{error}"
            ) from error

    # =====================================================
    # REGISTRATION
    # =====================================================

    def _register_disease(
        self,
        disease: DiseaseRecord,
    ) -> None:
        """
        Register a disease in the internal indexes.
        """

        class_id = disease.class_id

        class_name = (
            disease.class_name.strip().lower()
        )

        if class_id in self._by_class_id:

            raise KnowledgeBaseError(
                "Duplicate class_id detected: "
                f"{class_id}"
            )

        if class_name in self._by_class_name:

            raise KnowledgeBaseError(
                "Duplicate class_name detected: "
                f"{disease.class_name}"
            )

        self._diseases.append(
            disease
        )

        self._by_class_id[
            class_id
        ] = disease

        self._by_class_name[
            class_name
        ] = disease

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

            raise UnsupportedLanguageError(
                "Language must be a string."
            )

        language = (
            language.strip().lower()
        )

        if language not in (
            self.SUPPORTED_LANGUAGES
        ):

            raise UnsupportedLanguageError(
                "Unsupported language: "
                f"{language}. "
                "Supported languages: "
                f"{', '.join(self.SUPPORTED_LANGUAGES)}"
            )

        return language

    def get_supported_languages(
        self,
    ) -> list[str]:
        """
        Return supported language codes.
        """

        return list(
            self.SUPPORTED_LANGUAGES
        )

    # =====================================================
    # LOOKUP
    # =====================================================

    def get_disease(
        self,
        class_name: str,
    ) -> DiseaseRecord:
        """
        Get disease by model class name.

        Example:

            kb.get_disease("Blight")
        """

        if not isinstance(
            class_name,
            str,
        ):

            raise DiseaseNotFoundError(
                "Disease class name must be a string."
            )

        key = (
            class_name.strip().lower()
        )

        disease = (
            self._by_class_name.get(key)
        )

        if disease is None:

            raise DiseaseNotFoundError(
                "Disease not found: "
                f"{class_name}"
            )

        return disease

    def get_disease_by_class_id(
        self,
        class_id: int,
    ) -> DiseaseRecord:
        """
        Get disease by model class ID.

        Example:

            kb.get_disease_by_class_id(0)
        """

        try:

            class_id = int(
                class_id
            )

        except (
            TypeError,
            ValueError,
        ) as error:

            raise DiseaseNotFoundError(
                "Invalid class ID: "
                f"{class_id}"
            ) from error

        disease = (
            self._by_class_id.get(
                class_id
            )
        )

        if disease is None:

            raise DiseaseNotFoundError(
                "Disease class ID not found: "
                f"{class_id}"
            )

        return disease

    def get_all_diseases(
        self,
    ) -> list[DiseaseRecord]:
        """
        Return all disease records.
        """

        return list(
            self._diseases
        )

    # =====================================================
    # USER-FACING INFORMATION
    # =====================================================

    def get_disease_information(
        self,
        class_name: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Return localized disease information.

        Example:

            kb.get_disease_information(
                "Blight",
                "am"
            )
        """

        language = (
            self._validate_language(
                language
            )
        )

        disease = self.get_disease(
            class_name
        )

        return disease.to_dict(
            language
        )

    def get_disease_information_by_id(
        self,
        class_id: int,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Return localized disease information
        using the ML model class ID.
        """

        language = (
            self._validate_language(
                language
            )
        )

        disease = (
            self.get_disease_by_class_id(
                class_id
            )
        )

        return disease.to_dict(
            language
        )

    # =====================================================
    # ADVISORY CONTENT
    # =====================================================

    def get_advice(
        self,
        class_name: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Return the advisory sections for a disease.

        This method does not generate new advice.

        It retrieves structured advice already stored
        in the validated knowledge base.
        """

        information = (
            self.get_disease_information(
                class_name,
                language,
            )
        )

        return {

            "disease": information[
                "display_name"
            ],

            "scientific_name": information[
                "scientific_name"
            ],

            "description": information[
                "description"
            ],

            "symptoms": information[
                "symptoms"
            ],

            "causes": information[
                "causes"
            ],

            "favorable_conditions": information[
                "favorable_conditions"
            ],

            "prevention": information[
                "prevention"
            ],

            "management": information[
                "management"
            ],

            "severity": information[
                "severity"
            ],
        }

    # =====================================================
    # SOURCE INFORMATION
    # =====================================================

    def get_sources(
        self,
        class_name: str,
    ) -> list[dict[str, Any]]:
        """
        Return source metadata for a disease.
        """

        disease = self.get_disease(
            class_name
        )

        return [

            {
                "title": source.title,

                "organization": (
                    source.organization
                ),

                "source_type": (
                    source.source_type
                ),

                "url": source.url,

                "year": source.year,

                "notes": source.notes,
            }

            for source in disease.sources
        ]

    # =====================================================
    # VALIDATION INFORMATION
    # =====================================================

    def get_validation_status(
        self,
        class_name: str,
    ) -> dict[str, Any]:
        """
        Return validation metadata.
        """

        disease = self.get_disease(
            class_name
        )

        validation = (
            disease.validation
        )

        return {

            "status": (
                validation.status
            ),

            "method": (
                validation.method
            ),

            "expert_validated": (
                validation.expert_validated
            ),

            "reviewer": (
                validation.reviewer
            ),

            "date": (
                validation.date
            ),

            "notes": (
                validation.notes
            ),
        }

    # =====================================================
    # METADATA
    # =====================================================

    def get_metadata(
        self,
    ) -> dict[str, Any]:
        """
        Return knowledge-base metadata.
        """

        return dict(
            self._metadata
        )

    def count(
        self,
    ) -> int:
        """
        Return the number of knowledge records.
        """

        return len(
            self._diseases
        )

    def is_ready(
        self,
    ) -> bool:
        """
        Check whether the knowledge base is ready
        for application use.

        This checks structural readiness only.

        It does NOT claim that expert validation
        has been completed.
        """

        return (

            self.data_path.exists()

            and len(
                self._diseases
            ) > 0

            and all(

                language in
                self.SUPPORTED_LANGUAGES

                for language in (
                    self.SUPPORTED_LANGUAGES
                )
            )
        )
