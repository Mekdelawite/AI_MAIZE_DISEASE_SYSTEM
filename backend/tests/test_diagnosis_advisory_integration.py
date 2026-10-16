"""
=========================================================
Diagnosis + Advisory Integration Test
=========================================================
"""

from pathlib import Path

from backend.app.services.diagnosis_advisory_service import (
    DiagnosisAdvisoryIntegrationService,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEST_IMAGE = (
    PROJECT_ROOT
    / "ml_model"
    / "inference"
    / "test_images"
    / "sample.jpg"
)


def main() -> None:

    print("=" * 70)
    print("DIAGNOSIS + ADVISORY INTEGRATION TEST")
    print("=" * 70)

    # =====================================================
    # TEST 1 — SERVICE INITIALIZATION
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 1 — SERVICE INITIALIZATION")
    print("=" * 70)

    print(
        "Initializing diagnosis + advisory service..."
    )

    service = (
        DiagnosisAdvisoryIntegrationService()
    )

    print(
        "✓ Diagnosis + advisory service initialized"
    )

    # =====================================================
    # TEST 2 — READINESS
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 2 — READINESS")
    print("=" * 70)

    assert service.is_ready()

    print(
        "✓ Diagnosis service ready"
    )

    print(
        "✓ Advisor service ready"
    )

    # =====================================================
    # TEST 3 — TEST IMAGE
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 3 — TEST IMAGE")
    print("=" * 70)

    print(f"Image: {TEST_IMAGE}")

    assert TEST_IMAGE.exists()
    assert TEST_IMAGE.is_file()

    print("✓ Test image found")

    # =====================================================
    # TEST 4 — COMBINED WORKFLOW
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 4 — DIAGNOSIS + ADVISORY")
    print("=" * 70)

    print(
        "Running complete farmer workflow..."
    )

    result = (
        service.diagnose_and_advise(
            image_path=TEST_IMAGE,
            language="en",
            explain=False,
        )
    )

    assert isinstance(result, dict)

    print(
        "✓ Combined result returned"
    )

    # =====================================================
    # TEST 5 — DIAGNOSIS RESULT
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 5 — DIAGNOSIS RESULT")
    print("=" * 70)

    diagnosis = result.get(
        "diagnosis"
    )

    assert isinstance(
        diagnosis,
        dict,
    )

    prediction = diagnosis.get(
        "prediction"
    )

    assert isinstance(
        prediction,
        dict,
    )

    print(
        f"Disease: "
        f"{prediction.get('display_name')}"
    )

    print(
        f"Class: "
        f"{prediction.get('class_name')}"
    )

    print(
        f"Confidence: "
        f"{prediction.get('confidence')}%"
    )

    assert prediction.get(
        "class_name"
    ) == "Blight"

    assert prediction.get(
        "confidence"
    ) is not None

    print(
        "✓ Diagnosis result validated"
    )

    # =====================================================
    # TEST 6 — ADVISORY RESULT
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 6 — ADVISORY RESULT")
    print("=" * 70)

    advisory = result.get(
        "advisory"
    )

    assert isinstance(
        advisory,
        dict,
    )

    print(
        f"Advisory disease: "
        f"{advisory.get('disease')}"
    )

    print(
        f"Language: "
        f"{advisory.get('language')}"
    )

    print(
        f"Confidence: "
        f"{advisory.get('confidence')}%"
    )

    assert advisory.get(
        "disease"
    ) == "Northern Leaf Blight"

    assert advisory.get(
        "language"
    ) == "en"

    print(
        "✓ Advisory result validated"
    )

    # =====================================================
    # TEST 7 — CONFIDENCE TRANSFER
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 7 — CONFIDENCE TRANSFER")
    print("=" * 70)

    diagnosis_confidence = (
        prediction.get(
            "confidence"
        )
    )

    advisory_confidence = (
        advisory.get(
            "confidence"
        )
    )

    print(
        f"Diagnosis confidence: "
        f"{diagnosis_confidence}%"
    )

    print(
        f"Advisory confidence: "
        f"{advisory_confidence}%"
    )

    assert (
        diagnosis_confidence
        == advisory_confidence
    )

    print(
        "✓ Confidence transferred correctly"
    )

    # =====================================================
    # TEST 8 — SOURCE INFORMATION
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 8 — SOURCE INFORMATION")
    print("=" * 70)

    sources = advisory.get(
        "sources",
        [],
    )

    assert len(sources) >= 1

    print(
        f"Number of sources: "
        f"{len(sources)}"
    )

    print(
        f"✓ Source: "
        f"{sources[0].get('title')}"
    )

    print(
        "✓ Source information preserved"
    )

    # =====================================================
    # TEST 9 — VALIDATION METADATA
    # =====================================================

    print("\n" + "=" * 70)
    print("TEST 9 — VALIDATION METADATA")
    print("=" * 70)

    validation = advisory.get(
        "validation",
        {},
    )

    assert isinstance(
        validation,
        dict,
    )

    print(
        f"Validation status: "
        f"{validation.get('status')}"
    )

    print(
        f"Expert validated: "
        f"{validation.get('expert_validated')}"
    )

    assert (
        validation.get(
            "expert_validated"
        )
        is False
    )

    print(
        "✓ Validation metadata preserved"
    )

    # =====================================================
    # TEST 10 — FINAL RESULT
    # =====================================================

    print("\n" + "=" * 70)
    print("FINAL COMBINED RESULT")
    print("=" * 70)

    print(result)

    print("\n" + "=" * 70)
    print(
        "ALL DIAGNOSIS + ADVISORY "
        "INTEGRATION TESTS PASSED"
    )
    print("=" * 70)

    print(
        "✓ Diagnosis executed"
    )

    print(
        "✓ Disease extracted"
    )

    print(
        "✓ Confidence transferred"
    )

    print(
        "✓ Advisory generated"
    )

    print(
        "✓ Source information preserved"
    )

    print(
        "✓ Validation metadata preserved"
    )

    print(
        "✓ Complete farmer workflow verified"
    )


if __name__ == "__main__":
    main()