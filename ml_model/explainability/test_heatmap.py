"""
=========================================================
Heatmap Utility Test
=========================================================
"""

import numpy as np

from heatmap import HeatmapGenerator


def main():

    print()
    print("=" * 60)
    print("HEATMAP GENERATOR TEST")
    print("=" * 60)
    print()

    # Simulate the actual Grad-CAM output
    test_heatmap = np.random.random(
        (7, 7)
    ).astype(np.float32)

    print(
        f"Input heatmap shape: "
        f"{test_heatmap.shape}"
    )

    generator = HeatmapGenerator()

    # Generate visual heatmap
    result = generator.generate(
        test_heatmap
    )

    print(
        f"Output heatmap shape: "
        f"{result.shape}"
    )

    print(
        f"Output data type: "
        f"{result.dtype}"
    )

    print(
        f"Minimum value: "
        f"{result.min()}"
    )

    print(
        f"Maximum value: "
        f"{result.max()}"
    )

    print()

    # Save test result
    output_path = (
        "outputs/test_heatmap.jpg"
    )

    generator.save(
        result,
        output_path,
    )

    print(
        f"Heatmap saved to: "
        f"{output_path}"
    )

    print()
    print(
        "Heatmap utility test passed successfully."
    )


if __name__ == "__main__":
    main()