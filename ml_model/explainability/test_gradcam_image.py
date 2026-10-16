"""
=========================================================
Grad-CAM Image Test
=========================================================

Tests the Grad-CAM engine using a real maize leaf image.

Input:
    ml_model/inference/test_images/sample.jpg

Output:
    Prints predicted class, confidence, and heatmap
    information.

=========================================================
"""

from pathlib import Path

import numpy as np
from tensorflow.keras.utils import load_img, img_to_array

from gradcam import GradCAM


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IMAGE_PATH = (
    PROJECT_ROOT
    / "ml_model"
    / "inference"
    / "test_images"
    / "sample.jpg"
)


# ---------------------------------------------------------
# Image preprocessing
# ---------------------------------------------------------

def preprocess_image(image_path: Path) -> np.ndarray:
    """
    Load and preprocess an image for MobileNetV2.
    """

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = load_img(
        image_path,
        target_size=(224, 224),
        color_mode="rgb",
    )

    image_array = img_to_array(image)

    image_array = image_array.astype(
        np.float32
    )

    # MobileNetV2 preprocessing
    image_array = (
        image_array / 127.5
    ) - 1.0

    image_array = np.expand_dims(
        image_array,
        axis=0,
    )

    return image_array


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print()
    print("=" * 60)
    print("GRAD-CAM IMAGE TEST")
    print("=" * 60)
    print()

    print(
        f"Image: {IMAGE_PATH}"
    )

    print()

    # -----------------------------------------------------
    # Prepare image
    # -----------------------------------------------------

    image = preprocess_image(
        IMAGE_PATH
    )

    print(
        "Image preprocessing successful."
    )

    print(
        f"Input shape: {image.shape}"
    )

    print()

    # -----------------------------------------------------
    # Initialize Grad-CAM
    # -----------------------------------------------------

    gradcam = GradCAM()

    print()

    # -----------------------------------------------------
    # Generate heatmap
    # -----------------------------------------------------

    heatmap, predicted_class, confidence = (
        gradcam.generate(image)
    )

    # -----------------------------------------------------
    # Results
    # -----------------------------------------------------

    print("=" * 60)
    print("GRAD-CAM RESULT")
    print("=" * 60)

    print()

    print(
        f"Predicted class ID : {predicted_class}"
    )

    print(
        f"Confidence         : {confidence * 100:.2f}%"
    )

    print(
        f"Heatmap shape      : {heatmap.shape}"
    )

    print(
        f"Heatmap minimum    : {heatmap.min():.6f}"
    )

    print(
        f"Heatmap maximum    : {heatmap.max():.6f}"
    )

    print(
        f"Heatmap mean       : {heatmap.mean():.6f}"
    )

    print()

    print(
        "Grad-CAM generated successfully."
    )


if __name__ == "__main__":
    main()