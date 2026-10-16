"""
=========================================================
Maize Disease Knowledge Base Validators
=========================================================

Validates the structure and quality of the disease
knowledge base before it is used by the AI Advisor.

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """
    Raised when knowledge-base validation fails.
    """


class KnowledgeBaseValidator:
    """
    Performs structural and content validation on the
    maize disease knowledge base.

    The validator checks:

        - Disease count
        - Unique class IDs
        - Unique class names
        - Required languages
        - Required localized content
        - Required disease metadata
        - Source information
        - Validation metadata
    """

    REQUIRED_LANGUAGES = {
        "en",
        "am",
    }

    REQUIRED_CONTENT_FIELDS = {
        "description",
        "symptoms",
        "causes",
        "favorable_conditions",
        "prevention",
        "management",
        "severity",
    }

    REQUIRED_DISEASE_FIELDS = {
        "class_id",
        "class_name",
        "display_name_en",
        "display_name_am",
        "scientific_name",
        "english",
        "amharic",
        "sources",
        "validation",
    }

    REQUIRED_SOURCE_FIELDS = {
        "title",
        "organization",
        "source_type",
    }

    REQUIRED_VALIDATION_FIELDS = {
        "status",
        "method",
        "expert_validated",
    }

    def __init__(
        self,
        knowledge_base: Any,
    ) -> None:

        self.knowledge_base = knowledge_base

        self.errors: list[str] = []

        self.warnings: list[str] = []

    # =====================================================
    # MAIN VALIDATION
    # =====================================================

    def validate(
        self,
        raise_on_error: bool = True,
    ) -> bool:
        """
        Run all validation checks.

        Returns:
            True when validation succeeds.

        Raises:
            ValidationError when validation fails and
            raise_on_error=True.
        """

        self.errors.clear()
        self.warnings.clear()

        self._validate_disease_count()

        self._validate_languages()

        self._validate_diseases()

        if self.errors and raise_on_error:

            raise ValidationError(
                self.format_errors()
            )

        return not bool(
            self.errors
        )

    # =====================================================
    # DISEASE COUNT
    # =====================================================

    def _validate_disease_count(
        self,
    ) -> None:

        try:

            count = self.knowledge_base.count()

        except Exception as error:

            self.errors.append(
                "Unable to determine disease count: "
                f"{error}"
            )

            return

        if count == 0:

            self.errors.append(
                "Knowledge base contains no diseases."
            )

    # =====================================================
    # LANGUAGE VALIDATION
    # =====================================================

    def _validate_languages(
        self,
    ) -> None:

        try:

            languages = set(
                self.knowledge_base
                .get_supported_languages()
            )

        except Exception as error:

            self.errors.append(
                "Unable to determine supported "
                f"languages: {error}"
            )

            return

        missing = (
            self.REQUIRED_LANGUAGES
            - languages
        )

        if missing:

            self.errors.append(
                "Missing required languages: "
                f"{', '.join(sorted(missing))}"
            )

    # =====================================================
    # DISEASE VALIDATION
    # =====================================================

    def _validate_diseases(
        self,
    ) -> None:

        try:

            diseases = (
                self.knowledge_base
                .get_all_diseases()
            )

        except Exception as error:

            self.errors.append(
                "Unable to retrieve diseases: "
                f"{error}"
            )

            return

        if not diseases:

            return

        class_ids: set[int] = set()

        class_names: set[str] = set()

        for index, disease in enumerate(
            diseases,
            start=1,
        ):

            self._validate_single_disease(
                disease,
                index,
                class_ids,
                class_names,
            )

    # =====================================================
    # SINGLE DISEASE
    # =====================================================

    def _validate_single_disease(
        self,
        disease: Any,
        index: int,
        class_ids: set[int],
        class_names: set[str],
    ) -> None:

        prefix = (
            f"Disease #{index}"
        )

        # -------------------------------------------------
        # Class ID
        # -------------------------------------------------

        class_id = getattr(
            disease,
            "class_id",
            None,
        )

        if class_id is None:

            self.errors.append(
                f"{prefix}: missing class_id."
            )

        else:

            if class_id in class_ids:

                self.errors.append(
                    f"{prefix}: duplicate "
                    f"class_id {class_id}."
                )

            class_ids.add(
                class_id
            )

        # -------------------------------------------------
        # Class name
        # -------------------------------------------------

        class_name = getattr(
            disease,
            "class_name",
            None,
        )

        if not class_name:

            self.errors.append(
                f"{prefix}: missing class_name."
            )

        else:

            normalized = (
                str(class_name)
                .strip()
                .lower()
            )

            if normalized in class_names:

                self.errors.append(
                    f"{prefix}: duplicate "
                    f"class_name '{class_name}'."
                )

            class_names.add(
                normalized
            )

        # -------------------------------------------------
        # Display names
        # -------------------------------------------------

        self._require_value(
            disease,
            "display_name_en",
            prefix,
        )

        self._require_value(
            disease,
            "display_name_am",
            prefix,
        )

        # -------------------------------------------------
        # Scientific name
        # -------------------------------------------------

        scientific_name = getattr(
            disease,
            "scientific_name",
            None,
        )

        if not scientific_name:

            self.warnings.append(
                f"{prefix}: scientific_name "
                "is missing."
            )

        # -------------------------------------------------
        # Localized content
        # -------------------------------------------------

        english = getattr(
            disease,
            "english",
            None,
        )

        amharic = getattr(
            disease,
            "amharic",
            None,
        )

        self._validate_localized_content(
            english,
            "English",
            prefix,
        )

        self._validate_localized_content(
            amharic,
            "Amharic",
            prefix,
        )

        # -------------------------------------------------
        # Sources
        # -------------------------------------------------

        sources = getattr(
            disease,
            "sources",
            None,
        )

        self._validate_sources(
            sources,
            prefix,
        )

        # -------------------------------------------------
        # Validation metadata
        # -------------------------------------------------

        validation = getattr(
            disease,
            "validation",
            None,
        )

        self._validate_validation_metadata(
            validation,
            prefix,
        )

    # =====================================================
    # REQUIRED VALUE
    # =====================================================

    def _require_value(
        self,
        object_value: Any,
        attribute: str,
        prefix: str,
    ) -> None:

        value = getattr(
            object_value,
            attribute,
            None,
        )

        if value is None:

            self.errors.append(
                f"{prefix}: missing "
                f"{attribute}."
            )

            return

        if isinstance(
            value,
            str,
        ):

            if not value.strip():

                self.errors.append(
                    f"{prefix}: empty "
                    f"{attribute}."
                )

    # =====================================================
    # LOCALIZED CONTENT
    # =====================================================

    def _validate_localized_content(
        self,
        content: Any,
        language_name: str,
        prefix: str,
    ) -> None:

        if content is None:

            self.errors.append(
                f"{prefix}: missing "
                f"{language_name} content."
            )

            return

        for field in (
            self.REQUIRED_CONTENT_FIELDS
        ):

            value = getattr(
                content,
                field,
                None,
            )

            if value is None:

                self.errors.append(
                    f"{prefix}: {language_name} "
                    f"content missing '{field}'."
                )

                continue

            if isinstance(
                value,
                str,
            ):

                if not value.strip():

                    self.errors.append(
                        f"{prefix}: {language_name} "
                        f"'{field}' is empty."
                    )

            elif isinstance(
                value,
                list,
            ):

                if len(value) == 0:

                    self.warnings.append(
                        f"{prefix}: {language_name} "
                        f"'{field}' is empty."
                    )

    # =====================================================
    # SOURCES
    # =====================================================

    def _validate_sources(
        self,
        sources: Any,
        prefix: str,
    ) -> None:

        if sources is None:

            self.errors.append(
                f"{prefix}: sources are missing."
            )

            return

        if not isinstance(
            sources,
            list,
        ):

            self.errors.append(
                f"{prefix}: sources must "
                "be a list."
            )

            return

        if len(sources) == 0:

            self.warnings.append(
                f"{prefix}: no sources "
                "are registered."
            )

            return

        for source_index, source in enumerate(
            sources,
            start=1,
        ):

            source_prefix = (
                f"{prefix}, source #{source_index}"
            )

            for field in (
                self.REQUIRED_SOURCE_FIELDS
            ):

                value = getattr(
                    source,
                    field,
                    None,
                )

                if value is None:

                    self.errors.append(
                        f"{source_prefix}: "
                        f"missing {field}."
                    )

                elif isinstance(
                    value,
                    str,
                ):

                    if not value.strip():

                        self.errors.append(
                            f"{source_prefix}: "
                            f"empty {field}."
                        )

    # =====================================================
    # VALIDATION METADATA
    # =====================================================

    def _validate_validation_metadata(
        self,
        validation: Any,
        prefix: str,
    ) -> None:

        if validation is None:

            self.errors.append(
                f"{prefix}: validation metadata "
                "is missing."
            )

            return

        for field in (
            self.REQUIRED_VALIDATION_FIELDS
        ):

            value = getattr(
                validation,
                field,
                None,
            )

            if value is None:

                self.errors.append(
                    f"{prefix}: validation "
                    f"metadata missing '{field}'."
                )

        expert_validated = getattr(
            validation,
            "expert_validated",
            False,
        )

        if expert_validated is not True:

            self.warnings.append(
                f"{prefix}: record is not marked "
                "as expert validated."
            )

    # =====================================================
    # REPORTING
    # =====================================================

    def format_errors(
        self,
    ) -> str:
        """
        Format validation errors.
        """

        if not self.errors:

            return "No validation errors."

        lines = [
            "Knowledge base validation failed:",
            "",
        ]

        for index, error in enumerate(
            self.errors,
            start=1,
        ):

            lines.append(
                f"{index}. {error}"
            )

        return "\n".join(
            lines
        )

    def format_warnings(
        self,
    ) -> str:
        """
        Format validation warnings.
        """

        if not self.warnings:

            return "No validation warnings."

        lines = [
            "Knowledge base validation warnings:",
            "",
        ]

        for index, warning in enumerate(
            self.warnings,
            start=1,
        ):

            lines.append(
                f"{index}. {warning}"
            )

        return "\n".join(
            lines
        )

    def get_report(
        self,
    ) -> dict[str, Any]:
        """
        Return a structured validation report.
        """

        return {

            "valid": not bool(
                self.errors
            ),

            "disease_count": (
                self.knowledge_base.count()
            ),

            "supported_languages": (
                self.knowledge_base
                .get_supported_languages()
            ),

            "errors": list(
                self.errors
            ),

            "warnings": list(
                self.warnings
            ),
        }