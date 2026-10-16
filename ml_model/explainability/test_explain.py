"""
=========================================================
Complete Explainability Pipeline Test
=========================================================
"""

from pathlib import Path

from explain import ExplainabilityService


def main():

    print()
    print("=" * 70)
    print("COMPLETE GRAD-CAM EXPLAINABILITY TEST")
    print("=" * 70)
    print()

    project_root = (
        Path(__file__).resolve().parents[2]
    )

    image_path = (
        project_root
        / "ml_model"
        / "inference"
        / "test_images"
        / "sample.jpg"
    )

    print(
        f"Input image:\n{image_path}"
    )

    print()

    # -----------------------------------------------------
    # Initialize service
    # -----------------------------------------------------

    service = ExplainabilityService()

    print()

    # -----------------------------------------------------
    # Explain image
    # -----------------------------------------------------

    result = service.explain(
        image_path
    )

    # -----------------------------------------------------
    # Results
    # -----------------------------------------------------

    print("=" * 70)
    print("EXPLANATION RESULT")
    print("=" * 70)
    print()

    print(
        f"Class ID       : "
        f"{result['class_id']}"
    )

    print(
        f"Class          : "
        f"{result['class_name']}"
    )

    print(
        f"Confidence     : "
        f"{result['confidence']}%"
    )

    print(
        f"Heatmap shape  : "
        f"{result['heatmap_shape']}"
    )

    print()

    print(
        f"Heatmap saved  : "
        f"{result['heatmap']}"
    )

    print(
        f"Overlay saved  : "
        f"{result['overlay']}"
    )

    print()

    print("=" * 70)
    print(
        "COMPLETE EXPLAINABILITY PIPELINE PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()