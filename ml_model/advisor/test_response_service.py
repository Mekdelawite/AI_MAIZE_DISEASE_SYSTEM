"""
=========================================================
Farmer Advisory Response Service Test
=========================================================

Tests the response layer that converts the structured
AdvisorService output into farmer-facing responses.

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from __future__ import annotations

import json
from pathlib import Path

from ml_model.advisor.response_service import (
    AdvisoryResponseError,
    AdvisoryResponseService,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEST_IMAGE = (
    PROJECT_ROOT
    / "inference"
    / "test_images"
    / "sample.jpg"
)


def print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:

    print("=" * 70)
    print("FARMER ADVISORY RESPONSE SERVICE TEST")
    print("=" * 70)

    # ==================================================
    # TEST 1 — INITIALIZATION
    # ==================================================

    print_section(
        "TEST 1 — RESPONSE SERVICE INITIALIZATION"
    )

    print("Initializing AdvisoryResponseService...")

    service = AdvisoryResponseService()

    print("✓ Response service initialized")

    # ==================================================
    # TEST 2 — READINESS
    # ==================================================

    print_section(
        "TEST 2 — READINESS CHECK"
    )

    assert service.is_ready(), (
        "Response service is not ready."
    )

    print("✓ Response service is ready")

    # ==================================================
    # TEST 3 — LANGUAGE SUPPORT
    # ==================================================

    print_section(
        "TEST 3 — LANGUAGE SUPPORT"
    )

    languages = (
        service.get_supported_languages()
    )

    print(
        f"Supported languages: {languages}"
    )

    assert "en" in languages
    assert "am" in languages

    print("✓ English supported")
    print("✓ Amharic supported")

    # ==================================================
    # TEST 4 — ENGLISH ADVISORY
    # ==================================================

    print_section(
        "TEST 4 — ENGLISH FARMER ADVISORY"
    )

    english = service.get_advisory(
        class_name="Blight",
        language="en",
        confidence=89.47,
    )

    english_data = english.to_dict()

    assert english_data["language"] == "en"
    assert english_data["disease"]
    assert english_data["description"]

    print(
        f"Disease: {english_data['disease']}"
    )

    print(
        f"Confidence: "
        f"{english_data['confidence']}%"
    )

    print("✓ English advisory generated")

    # ==================================================
    # TEST 5 — AMHARIC ADVISORY
    # ==================================================

    print_section(
        "TEST 5 — AMHARIC FARMER ADVISORY"
    )

    amharic = service.get_advisory(
        class_name="Blight",
        language="am",
        confidence=89.47,
    )

    amharic_data = amharic.to_dict()

    assert amharic_data["language"] == "am"
    assert amharic_data["disease"]
    assert amharic_data["description"]

    print(
        f"Disease: {amharic_data['disease']}"
    )

    print("✓ Amharic advisory generated")

    # ==================================================
    # TEST 6 — ADVISORY CONTENT
    # ==================================================

    print_section(
        "TEST 6 — ADVISORY CONTENT"
    )

    assert isinstance(
        english_data["symptoms"],
        list,
    )

    assert isinstance(
        english_data["causes"],
        list,
    )

    assert isinstance(
        english_data["favorable_conditions"],
        list,
    )

    assert isinstance(
        english_data["prevention"],
        list,
    )

    assert isinstance(
        english_data["management"],
        list,
    )

    print("✓ Symptoms available")
    print("✓ Causes available")
    print("✓ Favorable conditions available")
    print("✓ Prevention available")
    print("✓ Management available")

    # ==================================================
    # TEST 7 — SOURCE INFORMATION
    # ==================================================

    print_section(
        "TEST 7 — SOURCE INFORMATION"
    )

    sources = english_data["sources"]

    assert isinstance(
        sources,
        list,
    )

    assert len(sources) > 0

    print(
        f"Number of sources: {len(sources)}"
    )

    for source in sources:

        print(
            f"✓ {source.get('organization', '')}"
        )

        print(
            f"  {source.get('title', '')}"
        )

    print("✓ Source information preserved")

    # ==================================================
    # TEST 8 — VALIDATION METADATA
    # ==================================================

    print_section(
        "TEST 8 — VALIDATION METADATA"
    )

    validation = english_data[
        "validation"
    ]

    assert isinstance(
        validation,
        dict,
    )

    print(
        "Status:",
        validation.get("status"),
    )

    print(
        "Method:",
        validation.get("method"),
    )

    print(
        "Expert validated:",
        validation.get(
            "expert_validated"
        ),
    )

    print("✓ Validation metadata preserved")

    # ==================================================
    # TEST 9 — DISCLAIMER
    # ==================================================

    print_section(
        "TEST 9 — VALIDATION DISCLAIMER"
    )

    if validation.get(
        "expert_validated",
        False,
    ):

        assert (
            english_data["disclaimer"]
            == ""
        )

        print(
            "✓ No disclaimer required "
            "for expert-validated record"
        )

    else:

        assert english_data[
            "disclaimer"
        ]

        print(
            "✓ Disclaimer generated because "
            "expert validation is pending"
        )

    # ==================================================
    # TEST 10 — DIAGNOSIS INTEGRATION
    # ==================================================

    print_section(
        "TEST 10 — DIAGNOSIS INTEGRATION"
    )

    diagnosis = {

        "prediction": {

            "class_id": 0,

            "class_name": "Blight",

            "display_name": (
                "Northern Leaf Blight"
            ),

            "scientific_name": (
                "Exserohilum turcicum"
            ),

            "confidence": 89.47,
        }
    }

    response = service.from_diagnosis(
        diagnosis,
        language="en",
    )

    response_data = response.to_dict()

    assert (
        response_data["disease"]
        == "Northern Leaf Blight"
    )

    assert (
        response_data["confidence"]
        == 89.47
    )

    print("✓ Diagnosis accepted")
    print("✓ Disease matched")
    print("✓ Confidence transferred")
    print("✓ Advisory generated")

    # ==================================================
    # TEST 11 — DIAGNOSIS + AMHARIC
    # ==================================================

    print_section(
        "TEST 11 — DIAGNOSIS + AMHARIC"
    )

    amharic_response = (
        service.from_diagnosis(
            diagnosis,
            language="am",
        )
    )

    amharic_response_data = (
        amharic_response.to_dict()
    )

    assert (
        amharic_response_data[
            "language"
        ]
        == "am"
    )

    assert amharic_response_data[
        "disease"
    ]

    print(
        "✓ Diagnosis converted to Amharic advisory"
    )

    # ==================================================
    # TEST 12 — DICTIONARY OUTPUT
    # ==================================================

    print_section(
        "TEST 12 — DICTIONARY OUTPUT"
    )

    advisory_dict = (
        service.get_advisory_dict(
            class_name="Blight",
            language="en",
            confidence=89.47,
        )
    )

    assert isinstance(
        advisory_dict,
        dict,
    )

    json.dumps(
        advisory_dict,
        ensure_ascii=False,
    )

    print(
        "✓ Advisory can be serialized to JSON"
    )

    # ==================================================
    # TEST 13 — HEALTH CHECK
    # ==================================================

    print_section(
        "TEST 13 — HEALTH CHECK"
    )

    health = service.health_check()

    print(
        json.dumps(
            health,
            indent=4,
            ensure_ascii=False,
        )
    )

    assert health["ready"] is True

    print("✓ Health check passed")

    # ==================================================
    # FINAL RESULT
    # ==================================================

    print_section(
        "ALL RESPONSE SERVICE TESTS PASSED"
    )

    print("✓ Response service initialized")
    print("✓ English advisory")
    print("✓ Amharic advisory")
    print("✓ Advisory content")
    print("✓ Source information")
    print("✓ Validation metadata")
    print("✓ Validation disclaimer")
    print("✓ Diagnosis integration")
    print("✓ JSON serialization")
    print("✓ Health check")

    print()
    print(
        "Farmer Advisory Response Service "
        "is ready for the next integration layer."
    )


if __name__ == "__main__":
    main()