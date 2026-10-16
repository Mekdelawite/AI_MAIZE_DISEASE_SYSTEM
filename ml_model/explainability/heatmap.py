"""
=========================================================
Grad-CAM Heatmap Utilities
=========================================================

Converts a normalized Grad-CAM heatmap into a visual
heatmap that can later be overlaid on the original image.

=========================================================
"""

from pathlib import Path

import cv2
import numpy as np


class HeatmapGenerator:
    """
    Generates and saves visual Grad-CAM heatmaps.
    """

    def __init__(self, output_size=(224, 224)):
        """
        Parameters
        ----------
        output_size:
            Final heatmap size as (width, height).
        """

        self.output_size = output_size

    # -----------------------------------------------------
    # Validate heatmap
    # -----------------------------------------------------

    @staticmethod
    def validate_heatmap(heatmap: np.ndarray):
        """
        Validate a Grad-CAM heatmap.
        """

        if not isinstance(
            heatmap,
            np.ndarray
        ):
            raise TypeError(
                "Heatmap must be a NumPy array."
            )

        if heatmap.ndim != 2:
            raise ValueError(
                "Heatmap must be a 2D array. "
                f"Received shape: {heatmap.shape}"
            )

        if heatmap.size == 0:
            raise ValueError(
                "Heatmap is empty."
            )

    # -----------------------------------------------------
    # Normalize
    # -----------------------------------------------------

    @staticmethod
    def normalize(
        heatmap: np.ndarray
    ) -> np.ndarray:
        """
        Normalize heatmap values to [0, 1].
        """

        HeatmapGenerator.validate_heatmap(
            heatmap
        )

        heatmap = heatmap.astype(
            np.float32
        )

        minimum = np.min(heatmap)
        maximum = np.max(heatmap)

        if maximum - minimum < 1e-8:
            return np.zeros_like(
                heatmap,
                dtype=np.float32
            )

        normalized = (
            heatmap - minimum
        ) / (
            maximum - minimum
        )

        return normalized

    # -----------------------------------------------------
    # Resize
    # -----------------------------------------------------

    def resize(
        self,
        heatmap: np.ndarray
    ) -> np.ndarray:
        """
        Resize the heatmap to the model image size.
        """

        self.validate_heatmap(
            heatmap
        )

        width, height = self.output_size

        resized = cv2.resize(
            heatmap,
            (width, height),
            interpolation=cv2.INTER_CUBIC,
        )

        return resized

    # -----------------------------------------------------
    # Convert to color
    # -----------------------------------------------------

    def colorize(
        self,
        heatmap: np.ndarray
    ) -> np.ndarray:
        """
        Convert a normalized grayscale heatmap into
        a BGR color heatmap using OpenCV.
        """

        heatmap = self.normalize(
            heatmap
        )

        heatmap_uint8 = np.uint8(
            heatmap * 255
        )

        colored = cv2.applyColorMap(
            heatmap_uint8,
            cv2.COLORMAP_JET,
        )

        return colored

    # -----------------------------------------------------
    # Complete heatmap generation
    # -----------------------------------------------------

    def generate(
        self,
        heatmap: np.ndarray
    ) -> np.ndarray:
        """
        Generate a resized color heatmap.

        Returns
        -------
        np.ndarray
            BGR heatmap with shape:

                (224, 224, 3)
        """

        normalized = self.normalize(
            heatmap
        )

        resized = self.resize(
            normalized
        )

        colored = self.colorize(
            resized
        )

        return colored

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    def save(
        self,
        heatmap_image: np.ndarray,
        output_path
    ):
        """
        Save a generated heatmap image.
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
            heatmap_image,
        )

        if not success:
            raise IOError(
                f"Failed to save heatmap: "
                f"{output_path}"
            )

        return output_path