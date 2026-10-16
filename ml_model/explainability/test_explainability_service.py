"""
=========================================================
Explainability Service Test
=========================================================

Tests the application-level ExplainabilityService.

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path

from explainability_service import (
    ExplainabilityService
)


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

IMAGE_PATH = (
    BASE_DIR
    / "inference"
    / "test_images"
    / "sample.jpg"
)


# =========================================================
# MAIN TEST
# =========================================================

def main():

    print()
    print("=" * 70)
    print("EXPLAINABILITY SERVICE TEST")
    print("=" * 70)

    # -----------------------------------------------------
    # Check test image
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
    print("Initializing ExplainabilityService...")

    service = ExplainabilityService()

    print("✓ Explainability service initialized")

    # -----------------------------------------------------
    # Check service readiness
    # -----------------------------------------------------

    print()
    print("Checking service readiness...")

    if not service.is_ready():

        raise RuntimeError(
            "Explainability service is not ready."
        )

    print("✓ Service is ready")

    # -----------------------------------------------------
    # Generate explanation
    # -----------------------------------------------------

    print()
    print("Generating explanation...")

    result = service.explain(
        str(IMAGE_PATH)
    )

    # -----------------------------------------------------
    # Display result
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("EXPLANATION RESULT")
    print("=" * 70)

    print()
    print(
        f"Method       : {result['method']}"
    )

    print(
        f"Target layer : {result['target_layer']}"
    )

    print(
        f"Class ID     : {result['class_id']}"
    )

    print(
        f"Class        : {result['class_name']}"
    )

    print(
        f"Confidence   : {result['confidence']}%"
    )

    print(
        f"Heatmap      : {result['heatmap']}"
    )

    print(
        f"Overlay      : {result['overlay']}"
    )

    print(
        f"Heatmap size : {result['heatmap_shape']}"
    )

    # -----------------------------------------------------
    # Validate result
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("SERVICE CHECKS")
    print("=" * 70)

    assert result["method"] == "Grad-CAM"

    print("✓ Method confirmed: Grad-CAM")

    assert result["target_layer"] == "Conv_1"

    print("✓ Target layer confirmed: Conv_1")

    assert result["class_id"] is not None

    print("✓ Class ID generated")

    assert result["class_name"]

    print("✓ Class name generated")

    assert result["confidence"] is not None

    print("✓ Confidence generated")

    heatmap = Path(
        result["heatmap"]
    )

    assert heatmap.exists()

    print("✓ Heatmap file exists")

    overlay = Path(
        result["overlay"]
    )

    assert overlay.exists()

    print("✓ Overlay file exists")

    assert result["heatmap_shape"] == [
        7,
        7
    ]

    print("✓ Heatmap shape confirmed: [7, 7]")

    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("EXPLAINABILITY SERVICE TEST PASSED")
    print("=" * 70)
    print()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()