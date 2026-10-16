"""
=========================================================
Diagnosis Service Test
=========================================================

Tests the complete AI diagnosis application service.

Tests:
    1. Service initialization
    2. Service readiness
    3. Fast diagnosis
    4. Diagnosis with Grad-CAM explanation
    5. Prediction/explanation class consistency
    6. Generated heatmap
    7. Generated overlay

Author : Nigusu Tigabu,Rediet Tsega,Sanueal Admasu
Project: AI Maize Disease Detection System
=========================================================
"""

import json
from pathlib import Path

from diagnosis_service import DiagnosisService


# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

IMAGE_PATH = (
    BASE_DIR
    / "inference"
    / "test_images"
    / "sample.jpg"
)


# =========================================================
# DISPLAY HELPER
# =========================================================

def print_result(result):
    """
    Display the important parts of a diagnosis result.
    """

    print()
    print("=" * 70)
    print("DIAGNOSIS RESULT")
    print("=" * 70)

    print(
        json.dumps(
            result,
            indent=4
        )
    )


# =========================================================
# MAIN TEST
# =========================================================

def main():

    print()
    print("=" * 70)
    print("AI DIAGNOSIS SERVICE TEST")
    print("=" * 70)

    # -----------------------------------------------------
    # Verify test image
    # -----------------------------------------------------

    print()
    print("Test image:")
    print(IMAGE_PATH)

    if not IMAGE_PATH.exists():

        raise FileNotFoundError(
            f"Test image not found:\n{IMAGE_PATH}"
        )

    print()
    print("✓ Test image found")

    # -----------------------------------------------------
    # Initialize service
    # -----------------------------------------------------

    print()
    print("Initializing DiagnosisService...")

    service = DiagnosisService()

    print(
        "✓ Diagnosis service initialized"
    )

    # -----------------------------------------------------
    # Check readiness
    # -----------------------------------------------------

    print()
    print("Checking service readiness...")

    if not service.is_ready():

        raise RuntimeError(
            "Diagnosis service is not ready."
        )

    print(
        "✓ Diagnosis service is ready"
    )

    # =====================================================
    # TEST 1 — FAST DIAGNOSIS
    # =====================================================

    print()
    print("=" * 70)
    print("TEST 1 — FAST DIAGNOSIS")
    print("=" * 70)

    print()
    print("Running prediction without explanation...")

    fast_result = service.diagnose(
        str(IMAGE_PATH),
        explain=False
    )

    print()
    print("✓ Fast diagnosis completed")

    # -----------------------------------------------------
    # Validate prediction
    # -----------------------------------------------------

    assert "prediction" in fast_result

    print(
        "✓ Prediction generated"
    )

    assert "top_predictions" in fast_result

    print(
        "✓ Top predictions generated"
    )

    prediction = fast_result[
        "prediction"
    ]

    assert prediction["class_id"] is not None

    print(
        f"✓ Class ID: {prediction['class_id']}"
    )

    assert prediction["class_name"]

    print(
        f"✓ Class: {prediction['class_name']}"
    )

    assert prediction["confidence"] is not None

    print(
        f"✓ Confidence: "
        f"{prediction['confidence']}%"
    )

    assert prediction["model"] == "MobileNetV2"

    print(
        "✓ Model: MobileNetV2"
    )

    # -----------------------------------------------------
    # Confirm explanation was NOT requested
    # -----------------------------------------------------

    assert "explainability" not in fast_result

    print(
        "✓ Fast mode did not generate Grad-CAM"
    )

    # -----------------------------------------------------
    # Display fast result
    # -----------------------------------------------------

    print_result(
        fast_result
    )

    # =====================================================
    # TEST 2 — DIAGNOSIS + EXPLANATION
    # =====================================================

    print()
    print("=" * 70)
    print("TEST 2 — DIAGNOSIS + GRAD-CAM")
    print("=" * 70)

    print()
    print(
        "Running diagnosis with explain=True..."
    )

    explained_result = service.diagnose(
        str(IMAGE_PATH),
        explain=True
    )

    print()
    print(
        "✓ Diagnosis with explanation completed"
    )

    # -----------------------------------------------------
    # Validate prediction
    # -----------------------------------------------------

    assert "prediction" in explained_result

    print(
        "✓ Prediction generated"
    )

    assert "top_predictions" in explained_result

    print(
        "✓ Top predictions generated"
    )

    # -----------------------------------------------------
    # Validate explainability
    # -----------------------------------------------------

    assert (
        "explainability"
        in explained_result
    )

    print(
        "✓ Explainability generated"
    )

    explanation = explained_result[
        "explainability"
    ]

    assert explanation[
        "method"
    ] == "Grad-CAM"

    print(
        "✓ Method: Grad-CAM"
    )

    assert explanation[
        "target_layer"
    ] == "Conv_1"

    print(
        "✓ Target layer: Conv_1"
    )

    # -----------------------------------------------------
    # Prediction consistency
    # -----------------------------------------------------

    prediction_class = (
        explained_result[
            "prediction"
        ]["class_id"]
    )

    explanation_class = (
        explanation[
            "class_id"
        ]
    )

    assert (
        prediction_class
        == explanation_class
    )

    print(
        "✓ Prediction class matches "
        "explanation class"
    )

    # -----------------------------------------------------
    # Validate heatmap
    # -----------------------------------------------------

    heatmap = Path(
        explanation["heatmap"]
    )

    assert heatmap.exists()

    print(
        f"✓ Heatmap exists:\n  {heatmap}"
    )

    # -----------------------------------------------------
    # Validate overlay
    # -----------------------------------------------------

    overlay = Path(
        explanation["overlay"]
    )

    assert overlay.exists()

    print(
        f"✓ Overlay exists:\n  {overlay}"
    )

    # -----------------------------------------------------
    # Validate heatmap dimensions
    # -----------------------------------------------------

    assert (
        explanation[
            "heatmap_shape"
        ] == [7, 7]
    )

    print(
        "✓ Heatmap shape: [7, 7]"
    )

    # -----------------------------------------------------
    # Display complete result
    # -----------------------------------------------------

    print_result(
        explained_result
    )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    print()
    print("=" * 70)
    print("ALL DIAGNOSIS SERVICE TESTS PASSED")
    print("=" * 70)

    print()
    print(
        "✓ Fast prediction"
    )

    print(
        "✓ Top predictions"
    )

    print(
        "✓ Grad-CAM integration"
    )

    print(
        "✓ Prediction/explanation consistency"
    )

    print(
        "✓ Heatmap generation"
    )

    print(
        "✓ Overlay generation"
    )

    print()
    print(
        "AI diagnosis service is ready "
        "for backend integration."
    )

    print()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()