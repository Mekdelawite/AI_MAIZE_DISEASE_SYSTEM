"""
=========================================================
Knowledge Base Models
=========================================================

Data models used by the bilingual agricultural
knowledge base.

Supported languages:
    en = English
    am = Amharic

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class LocalizedContent:
    """
    Farmer-facing disease information in one language.
    """

    description: str

    symptoms: List[str]

    causes: List[str]

    favorable_conditions: List[str]

    prevention: List[str]

    management: List[str]

    severity: str


@dataclass(frozen=True)
class Source:
    """
    Source used to support knowledge-base content.
    """

    title: str

    organization: str

    source_type: str

    url: str

    year: int | None = None

    notes: str = ""


@dataclass(frozen=True)
class Validation:
    """
    Validation metadata for a knowledge-base record.
    """

    status: str

    method: str

    expert_validated: bool

    reviewer: str | None = None

    date: str | None = None

    notes: str = ""


@dataclass(frozen=True)
class DiseaseRecord:
    """
    Complete bilingual disease knowledge record.
    """

    class_id: int

    class_name: str

    display_name_en: str

    display_name_am: str

    scientific_name: str

    english: LocalizedContent

    amharic: LocalizedContent

    sources: List[Source]

    validation: Validation

    def get_language_content(
        self,
        language: str,
    ) -> LocalizedContent:
        """
        Return content for the requested language.

        Supported:
            en
            am
        """

        language = language.lower().strip()

        if language == "en":
            return self.english

        if language == "am":
            return self.amharic

        raise ValueError(
            f"Unsupported language: {language}. "
            "Use 'en' or 'am'."
        )

    def get_display_name(
        self,
        language: str,
    ) -> str:
        """
        Return localized disease display name.
        """

        language = language.lower().strip()

        if language == "en":
            return self.display_name_en

        if language == "am":
            return self.display_name_am

        raise ValueError(
            f"Unsupported language: {language}. "
            "Use 'en' or 'am'."
        )

    def to_dict(
        self,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Convert the disease record into a
        farmer-facing dictionary.
        """

        content = self.get_language_content(
            language
        )

        return {
            "class_id": self.class_id,

            "class_name": self.class_name,

            "display_name": self.get_display_name(
                language
            ),

            "scientific_name": (
                self.scientific_name
            ),

            "description": (
                content.description
            ),

            "symptoms": (
                content.symptoms
            ),

            "causes": (
                content.causes
            ),

            "favorable_conditions": (
                content.favorable_conditions
            ),

            "prevention": (
                content.prevention
            ),

            "management": (
                content.management
            ),

            "severity": (
                content.severity
            ),
        }