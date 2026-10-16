"""
=========================================================
Farmer Advisory Response Models
=========================================================

Defines structured response models used by the
AI Maize Disease Advisor.

Supported languages:
    en = English
    am = Amharic

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdvisoryResponse:
    """
    Structured farmer-facing advisory response.
    """

    language: str

    disease: str

    scientific_name: str | None

    confidence: float | None

    severity: str

    description: str

    symptoms: list[str] = field(default_factory=list)

    causes: list[str] = field(default_factory=list)

    favorable_conditions: list[str] = field(
        default_factory=list
    )

    prevention: list[str] = field(
        default_factory=list
    )

    management: list[str] = field(
        default_factory=list
    )

    sources: list[dict[str, Any]] = field(
        default_factory=list
    )

    validation: dict[str, Any] = field(
        default_factory=dict
    )

    disclaimer: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the advisory response to a dictionary.
        """

        return {
            "language": self.language,

            "disease": self.disease,

            "scientific_name": (
                self.scientific_name
            ),

            "confidence": self.confidence,

            "severity": self.severity,

            "description": self.description,

            "symptoms": list(
                self.symptoms
            ),

            "causes": list(
                self.causes
            ),

            "favorable_conditions": list(
                self.favorable_conditions
            ),

            "prevention": list(
                self.prevention
            ),

            "management": list(
                self.management
            ),

            "sources": list(
                self.sources
            ),

            "validation": dict(
                self.validation
            ),

            "disclaimer": self.disclaimer,
        }