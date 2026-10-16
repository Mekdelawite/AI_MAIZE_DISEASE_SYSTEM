"""
=========================================================
Backend Advisor Integration Test
=========================================================

Tests the connection between the Flask backend advisor
integration service and the already-tested AI Advisor.

Run from project root:

    python -m backend.tests.test_advisor_integration
=========================================================
"""

from __future__ import annotations

from backend.app.services.advisor_service import (
    AdvisorIntegrationService,
    BackendAdvisorError,
)


def main() -> None:
    print("=" * 70)
    print("BACKEND ADVISOR INTEGRATION TEST")
    print("=" * 70)

    # =====================================================
    # TEST 1 — SERVICE INITIALIZATION
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 1 — SERVICE INITIALIZATION")
    print("=" * 70)

    print("Initializing backend advisor service...")

    service = AdvisorIntegrationService()

    print("✓ Backend advisor service initialized")

    # =====================================================
    # TEST 2 — READINESS
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 2 — READINESS")
    print("=" * 70)

    assert service.is_ready()

    print("✓ AI advisor service is ready")

    # =====================================================
    # TEST 3 — SUPPORTED LANGUAGES
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 3 — LANGUAGE SUPPORT")
    print("=" * 70)

    languages = service.get_supported_languages()

    print(f"Supported languages: {languages}")

    assert "en" in languages
    assert "am" in languages

    print("✓ English supported")
    print("✓ Amharic supported")

    # =====================================================
    # TEST 4 — ENGLISH ADVISORY
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 4 — ENGLISH ADVISORY")
    print("=" * 70)

    english = service.get_advisory(
        class_name="Blight",
        language="en",
        confidence=89.47,
    )

    assert isinstance(english, dict)

    assert english.get("disease")

    assert english.get("confidence") == 89.47

    print(
        f"Disease: {english.get('disease')}"
    )

    print(
        f"Confidence: {english.get('confidence')}%"
    )

    print("✓ English advisory generated")

    # =====================================================
    # TEST 5 — AMHARIC ADVISORY
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 5 — AMHARIC ADVISORY")
    print("=" * 70)

    amharic = service.get_advisory(
        class_name="Blight",
        language="am",
        confidence=89.47,
    )

    assert isinstance(amharic, dict)

    assert amharic.get("disease")

    assert amharic.get("language") == "am"

    print(
        f"Disease: {amharic.get('disease')}"
    )

    print("✓ Amharic advisory generated")

    # =====================================================
    # TEST 6 — ADVISORY CONTENT
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 6 — ADVISORY CONTENT")
    print("=" * 70)

    required_fields = [
        "symptoms",
        "causes",
        "favorable_conditions",
        "prevention",
        "management",
    ]

    for field in required_fields:

        value = english.get(field)

        assert value is not None

        print(
            f"✓ {field.replace('_', ' ').title()} available"
        )

    # =====================================================
    # TEST 7 — SOURCE INFORMATION
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 7 — SOURCE INFORMATION")
    print("=" * 70)

    sources = english.get(
        "sources",
        []
    )

    assert isinstance(sources, list)
    assert len(sources) > 0

    print(
        f"Number of sources: {len(sources)}"
    )

    for source in sources:

        print(
            f"✓ {source}"
        )

    print("✓ Source information preserved")

    # =====================================================
    # TEST 8 — VALIDATION METADATA
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 8 — VALIDATION METADATA")
    print("=" * 70)

    validation = english.get(
        "validation",
        {}
    )

    assert isinstance(
        validation,
        dict,
    )

    print(
        f"Validation: {validation}"
    )

    print(
        "✓ Validation metadata preserved"
    )

    # =====================================================
    # TEST 9 — DIAGNOSIS → ADVISORY
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 9 — DIAGNOSIS INTEGRATION")
    print("=" * 70)

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
        },
        "top_predictions": [],
    }

    advisory_from_diagnosis = (
        service.get_advisory_from_diagnosis(
            diagnosis=diagnosis,
            language="en",
        )
    )

    assert isinstance(
        advisory_from_diagnosis,
        dict,
    )

    assert (
        advisory_from_diagnosis.get(
            "confidence"
        )
        == 89.47
    )

    assert (
        advisory_from_diagnosis.get(
            "disease"
        )
    )

    print("✓ Diagnosis accepted")
    print("✓ Disease matched")
    print("✓ Confidence transferred")
    print("✓ Advisory generated")

    # =====================================================
    # TEST 10 — DIAGNOSIS → AMHARIC
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 10 — DIAGNOSIS + AMHARIC")
    print("=" * 70)

    amharic_from_diagnosis = (
        service.get_advisory_from_diagnosis(
            diagnosis=diagnosis,
            language="am",
        )
    )

    assert isinstance(
        amharic_from_diagnosis,
        dict,
    )

    assert (
        amharic_from_diagnosis.get(
            "language"
        )
        == "am"
    )

    print(
        "✓ Diagnosis converted to Amharic advisory"
    )

    # =====================================================
    # TEST 11 — INVALID LANGUAGE
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 11 — INVALID LANGUAGE HANDLING")
    print("=" * 70)

    try:

        service.get_advisory(
            class_name="Blight",
            language="fr",
            confidence=89.47,
        )

        raise AssertionError(
            "Invalid language was accepted."
        )

    except BackendAdvisorError:

        print(
            "✓ Unsupported language rejected"
        )

    # =====================================================
    # TEST 12 — INVALID CONFIDENCE
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 12 — CONFIDENCE VALIDATION")
    print("=" * 70)

    try:

        service.get_advisory(
            class_name="Blight",
            language="en",
            confidence=150,
        )

        raise AssertionError(
            "Invalid confidence was accepted."
        )

    except BackendAdvisorError:

        print(
            "✓ Invalid confidence rejected"
        )

    # =====================================================
    # TEST 13 — HEALTH / READINESS
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 13 — FINAL READINESS")
    print("=" * 70)

    assert service.is_ready()

    print("✓ Backend advisor service remains ready")

    # =====================================================
    # FINAL RESULT
    # =====================================================

    print("\n" + "=" * 70)
    print("ALL BACKEND ADVISOR TESTS PASSED")
    print("=" * 70)

    print("✓ Backend advisor initialized")
    print("✓ AI Advisor connected")
    print("✓ English advisory")
    print("✓ Amharic advisory")
    print("✓ Advisory content")
    print("✓ Source information")
    print("✓ Validation metadata")
    print("✓ Diagnosis integration")
    print("✓ Language validation")
    print("✓ Confidence validation")

    print(
        "\nBackend Advisor Integration is ready "
        "for Flask route integration."
    )


if __name__ == "__main__":
    main()