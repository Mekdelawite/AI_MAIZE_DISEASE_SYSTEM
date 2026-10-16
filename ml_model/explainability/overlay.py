"""
=========================================================
Grad-CAM Overlay Utilities
=========================================================

Combines the original maize leaf image with a Grad-CAM
heatmap.

=========================================================
"""

from pathlib import Path

import cv2
import numpy as np


class GradCAMOverlay:
    """
    Creates visual overlays between an original image
    and a Grad-CAM heatmap.
    """

    def __init__(
        self,
        alpha: float = 0.40,
    ):
        """
        Parameters
        ----------
        alpha:
            Strength of the heatmap.

            0.0 = original image only
            1.0 = heatmap only

            Recommended:
                0.35 - 0.45
        """

        if not 0.0 <= alpha <= 1.0:
            raise ValueError(
                "alpha must be between 0.0 and 1.0"
            )

        self.alpha = alpha

    # -----------------------------------------------------
    # Load image
    # -----------------------------------------------------

    @staticmethod
    def load_image(
        image_path
    ) -> np.ndarray:
        """
        Load an image using OpenCV.
        """

        image_path = Path(
            image_path
        )

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        image = cv2.imread(
            str(image_path)
        )

        if image is None:
            raise ValueError(
                f"Unable to read image: "
                f"{image_path}"
            )

        return image

    # -----------------------------------------------------
    # Resize heatmap
    # -----------------------------------------------------

    @staticmethod
    def resize_heatmap(
        heatmap: np.ndarray,
        target_shape,
    ) -> np.ndarray:
        """
        Resize heatmap to match the original image.
        """

        if heatmap.ndim != 3:
            raise ValueError(
                "Heatmap must be a color image "
                "with shape (height, width, 3)."
            )

        height, width = target_shape[:2]

        return cv2.resize(
            heatmap,
            (width, height),
            interpolation=cv2.INTER_LINEAR,
        )

    # -----------------------------------------------------
    # Create overlay
    # -----------------------------------------------------

    def create(
        self,
        original_image: np.ndarray,
        heatmap_image: np.ndarray,
    ) -> np.ndarray:
        """
        Combine the original image and heatmap.
        """

        if original_image is None:
            raise ValueError(
                "Original image cannot be None."
            )

        if heatmap_image is None:
            raise ValueError(
                "Heatmap image cannot be None."
            )

        # Make heatmap same size as original
        heatmap_image = self.resize_heatmap(
            heatmap_image,
            original_image.shape,
        )

        # Ensure both images have same channels
        if (
            len(original_image.shape) != 3
            or original_image.shape[2] != 3
        ):
            raise ValueError(
                "Original image must have "
                "3 color channels."
            )

        if (
            len(heatmap_image.shape) != 3
            or heatmap_image.shape[2] != 3
        ):
            raise ValueError(
                "Heatmap image must have "
                "3 color channels."
            )

        # Blend
        overlay = cv2.addWeighted(
            original_image,
            1.0 - self.alpha,
            heatmap_image,
            self.alpha,
            0,
        )

        return overlay

    # -----------------------------------------------------
    # Save overlay
    # -----------------------------------------------------

    @staticmethod
    def save(
        image: np.ndarray,
        output_path,
    ):
        """
        Save overlay image.
        """

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        success = cv2.imwrite(
            str(output_path),
            image,
        )

        if not success:
            raise IOError(
                f"Failed to save overlay: "
                f"{output_path}"
            )

        return output_path