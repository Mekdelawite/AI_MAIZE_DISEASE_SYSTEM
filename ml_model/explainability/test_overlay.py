"""
=========================================================
Grad-CAM Overlay Test
=========================================================
"""

from heatmap import HeatmapGenerator
from overlay import GradCAMOverlay


def main():

    print()
    print("=" * 60)
    print("GRAD-CAM OVERLAY TEST")
    print("=" * 60)
    print()

    # -----------------------------------------------------
    # Paths
    # -----------------------------------------------------

    original_path = (
        "outputs/original_test.jpg"
    )

    heatmap_path = (
        "outputs/test_heatmap.jpg"
    )

    overlay_path = (
        "outputs/test_overlay.jpg"
    )

    # -----------------------------------------------------
    # Load original image
    # -----------------------------------------------------

    overlay_generator = GradCAMOverlay(
        alpha=0.40
    )

    original = (
        overlay_generator.load_image(
            "../../ml_model/inference/test_images/sample.jpg"
        )
    )

    print(
        f"Original image shape: "
        f"{original.shape}"
    )

    # -----------------------------------------------------
    # Load heatmap
    # -----------------------------------------------------

    heatmap = (
        overlay_generator.load_image(
            heatmap_path
        )
    )

    print(
        f"Heatmap image shape: "
        f"{heatmap.shape}"
    )

    # -----------------------------------------------------
    # Create overlay
    # -----------------------------------------------------

    overlay = (
        overlay_generator.create(
            original,
            heatmap,
        )
    )

    print(
        f"Overlay shape: "
        f"{overlay.shape}"
    )

    # -----------------------------------------------------
    # Save original resized image
    # -----------------------------------------------------

    original_resized = (
        HeatmapGenerator(
            output_size=(
                original.shape[1],
                original.shape[0],
            )
        ).resize(
            heatmap[:, :, 0]
        )
    )

    # -----------------------------------------------------
    # Save overlay
    # -----------------------------------------------------

    overlay_generator.save(
        overlay,
        overlay_path,
    )

    print()
    print(
        f"Overlay saved to: "
        f"{overlay_path}"
    )

    print()
    print(
        "Grad-CAM overlay test passed successfully."
    )


if __name__ == "__main__":
    main()