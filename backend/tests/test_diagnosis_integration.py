"""
=========================================================
Backend Diagnosis Integration Test
=========================================================
"""

from pathlib import Path

from backend.app.services.diagnosis_service import (
    BackendDiagnosisError,
    DiagnosisIntegrationService,
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
    print("BACKEND DIAGNOSIS INTEGRATION TEST")
    print("=" * 70)

    # -----------------------------------------------------
    # TEST 1
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("TEST 1 — SERVICE INITIALIZATION")
    print("=" * 70)

    print("Initializing backend diagnosis service...")

    service = DiagnosisIntegrationService()

    print("✓ Backend diagnosis service initialized")

    # -----------------------------------------------------
    # TEST 2
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("TEST 2 — READINESS")
    print("=" * 70)

    assert service.is_ready()

    print("✓ AI diagnosis service is ready")

    # -----------------------------------------------------
    # TEST 3
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("TEST 3 — TEST IMAGE")
    print("=" * 70)

    print(f"Image: {TEST_IMAGE}")

    assert TEST_IMAGE.exists()

    print("✓ Test image found")

    # -----------------------------------------------------
    # TEST 4
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("TEST 4 — DIAGNOSIS")
    print("=" * 70)

    print("Running AI diagnosis...")

    result = service.diagnose(
        image_path=TEST_IMAGE,
        explain=False,
    )

    assert isinstance(result, dict)

    print("✓ Diagnosis completed")
    print("✓ Diagnosis result returned")

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("DIAGNOSIS RESULT")
    print("=" * 70)

    print(result)

    print("\n" + "=" * 70)
    print("ALL BACKEND DIAGNOSIS TESTS PASSED")
    print("=" * 70)

    print("✓ Backend initialized")
    print("✓ AI service connected")
    print("✓ Test image accepted")
    print("✓ Diagnosis executed")
    print("✓ Result returned")


if __name__ == "__main__":

    main()