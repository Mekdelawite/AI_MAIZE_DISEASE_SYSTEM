"""
=========================================================
Explainability Adapter Test
=========================================================
"""

from pathlib import Path

from explainability_adapter import (
    ExplainabilityAdapter,
)


def main():

    print()
    print("=" * 70)
    print("EXPLAINABILITY ADAPTER TEST")
    print("=" * 70)
    print()

    # -----------------------------------------------------
    # Project root
    # -----------------------------------------------------

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
        f"Image:\n{image_path}"
    )

    print()

    # -----------------------------------------------------
    # Create adapter
    # -----------------------------------------------------

    adapter = (
        ExplainabilityAdapter()
    )

    print(
        "Explainability adapter initialized."
    )

    print()

    # -----------------------------------------------------
    # Generate explanation
    # -----------------------------------------------------

    result = adapter.explain(
        image_path
    )

    # -----------------------------------------------------
    # Display result
    # -----------------------------------------------------

    print("=" * 70)
    print("EXPLANATION RESULT")
    print("=" * 70)
    print()

    print(
        f"Method       : "
        f"{result['method']}"
    )

    print(
        f"Target layer : "
        f"{result['target_layer']}"
    )

    print(
        f"Class ID     : "
        f"{result['class_id']}"
    )

    print(
        f"Class        : "
        f"{result['class_name']}"
    )

    print(
        f"Confidence   : "
        f"{result['confidence']}%"
    )

    print(
        f"Heatmap      : "
        f"{result['heatmap']}"
    )

    print(
        f"Overlay      : "
        f"{result['overlay']}"
    )

    print(
        f"Heatmap size : "
        f"{result['heatmap_shape']}"
    )

    print()

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    assert result["method"] == "Grad-CAM"

    assert (
        result["target_layer"]
        == "Conv_1"
    )

    assert result["class_id"] in (
        0,
        1,
        2,
        3,
    )

    assert 0.0 <= result[
        "confidence"
    ] <= 100.0

    assert Path(
        result["heatmap"]
    ).exists()

    assert Path(
        result["overlay"]
    ).exists()

    print(
        "All adapter checks passed."
    )

    print()
    print("=" * 70)
    print(
        "EXPLAINABILITY ADAPTER TEST PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()