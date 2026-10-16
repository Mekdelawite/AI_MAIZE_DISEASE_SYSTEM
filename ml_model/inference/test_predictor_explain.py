"""
=========================================================
Predictor + Explainability Integration Test
=========================================================

Tests the complete pipeline:

Image
  ↓
DiseasePredictor
  ↓
Prediction
  ↓
Grad-CAM
  ↓
Heatmap
  ↓
Overlay

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

import json
from pathlib import Path

from predictor import DiseasePredictor


# =========================================================
# TEST IMAGE
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

IMAGE_PATH = (
    BASE_DIR
    / "test_images"
    / "sample.jpg"
)


# =========================================================
# MAIN TEST
# =========================================================

def main():

    print()
    print("=" * 70)
    print("PREDICTOR + GRAD-CAM INTEGRATION TEST")
    print("=" * 70)

    print()
    print("Test image:")
    print(IMAGE_PATH)

    # -----------------------------------------------------
    # Verify image exists
    # -----------------------------------------------------

    if not IMAGE_PATH.exists():

        raise FileNotFoundError(
            f"Test image not found:\n{IMAGE_PATH}"
        )

    # -----------------------------------------------------
    # Create predictor
    # -----------------------------------------------------

    print()
    print("Initializing disease predictor...")

    predictor = DiseasePredictor()

    print()
    print("Running prediction with explain=True...")

    # -----------------------------------------------------
    # Run prediction + explanation
    # -----------------------------------------------------

    result = predictor.predict(
        str(IMAGE_PATH),
        explain=True,
    )

    # -----------------------------------------------------
    # Print result
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("INTEGRATION RESULT")
    print("=" * 70)

    print()

    print(
        json.dumps(
            result,
            indent=4,
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    assert "prediction" in result

    assert "top_predictions" in result

    assert "explainability" in result

    prediction = result[
        "prediction"
    ]

    explanation = result[
        "explainability"
    ]

    # -----------------------------------------------------
    # Validate prediction
    # -----------------------------------------------------

    assert "class_id" in prediction

    assert "class_name" in prediction

    assert "confidence" in prediction

    # -----------------------------------------------------
    # Validate explainability
    # -----------------------------------------------------

    assert (
        explanation["method"]
        == "Grad-CAM"
    )

    assert (
        explanation["target_layer"]
        == "Conv_1"
    )

    assert (
        "class_id"
        in explanation
    )

    assert (
        "class_name"
        in explanation
    )

    assert (
        "confidence"
        in explanation
    )

    assert (
        "heatmap"
        in explanation
    )

    assert (
        "overlay"
        in explanation
    )

    assert (
        "heatmap_shape"
        in explanation
    )

    # -----------------------------------------------------
    # Verify prediction consistency
    # -----------------------------------------------------

    assert (
        prediction["class_id"]
        == explanation["class_id"]
    )

    # -----------------------------------------------------
    # Verify generated files
    # -----------------------------------------------------

    heatmap_path = Path(
        explanation["heatmap"]
    )

    overlay_path = Path(
        explanation["overlay"]
    )

    assert heatmap_path.exists(), (
        "Grad-CAM heatmap file was not created."
    )

    assert overlay_path.exists(), (
        "Grad-CAM overlay file was not created."
    )

    # =====================================================
    # SUCCESS
    # =====================================================

    print()
    print("=" * 70)
    print("INTEGRATION CHECKS")
    print("=" * 70)

    print()
    print("✓ Prediction generated")
    print("✓ Top predictions generated")
    print("✓ Grad-CAM generated")
    print("✓ Target layer confirmed: Conv_1")
    print("✓ Prediction class matches explanation class")
    print("✓ Heatmap file exists")
    print("✓ Overlay file exists")

    print()
    print("=" * 70)
    print("PREDICTOR + GRAD-CAM INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":

    main()