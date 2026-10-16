"""
=========================================================
Image Validator
=========================================================

Validates uploaded images before sending them
to the AI model.

Validation includes:
    - File existence
    - Regular file check
    - Supported format
    - File size
    - Empty file detection
    - Image integrity
    - Minimum resolution
    - Blank / near-uniform image detection
    - Excessive blur detection

Author : Nigusu Tgabu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ml_model.inference.config import (
    SUPPORTED_EXTENSIONS,
    MAX_IMAGE_SIZE_BYTES,
)

from ml_model.inference.exceptions import (
    ImageNotFoundError,
    UnsupportedImageFormatError,
    ImageTooLargeError,
    InvalidImageError,
)


class ImageValidator:
    """
    Performs image validation and basic image-quality checks.

    The validator is intentionally kept in the inference layer
    because ImagePreprocessor already uses it before the image
    reaches the CNN.
    """

    # ---------------------------------------------------------
    # Image quality thresholds
    # ---------------------------------------------------------

    # Minimum image dimensions.
    MIN_IMAGE_WIDTH = 200
    MIN_IMAGE_HEIGHT = 200

    # Minimum grayscale standard deviation.
    # Very small values indicate an almost completely uniform
    # or blank image.
    MIN_INTENSITY_STD = 8.0

    # Minimum Laplacian variance.
    # Very small values indicate an excessively blurry image.
    MIN_BLUR_VARIANCE = 25.0

    # ---------------------------------------------------------
    # Basic validation
    # ---------------------------------------------------------

    @staticmethod
    def validate(image_path: str) -> Path:
        """
        Validate an image and its visual quality.

        Parameters
        ----------
        image_path : str
            Path to the image.

        Returns
        -------
        Path
            Valid image path.

        Raises
        ------
        ImageNotFoundError
            If the image does not exist.

        UnsupportedImageFormatError
            If the extension is unsupported.

        ImageTooLargeError
            If the file exceeds the configured size limit.

        InvalidImageError
            If the image is corrupted or fails quality checks.
        """

        image = Path(image_path)

        # -----------------------------------------------------
        # Check file exists
        # -----------------------------------------------------

        if not image.exists():
            raise ImageNotFoundError(
                f"Image not found:\n{image.resolve()}"
            )

        # -----------------------------------------------------
        # Check that path points to a regular file
        # -----------------------------------------------------

        if not image.is_file():
            raise InvalidImageError(
                "The selected image is not a valid file."
            )

        # -----------------------------------------------------
        # Check extension
        # -----------------------------------------------------

        extension = image.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedImageFormatError(
                f"Unsupported image format: {extension}\n"
                f"Supported formats: {SUPPORTED_EXTENSIONS}"
            )

        # -----------------------------------------------------
        # Check file size
        # -----------------------------------------------------

        try:
            file_size = image.stat().st_size

        except OSError as error:
            raise InvalidImageError(
                f"Unable to read image file information.\n{error}"
            )

        # Empty file
        if file_size <= 0:
            raise InvalidImageError(
                "The image file is empty."
            )

        # Maximum file size
        if file_size > MAX_IMAGE_SIZE_BYTES:
            raise ImageTooLargeError(
                f"Image size exceeds "
                f"{MAX_IMAGE_SIZE_BYTES / (1024 * 1024):.1f} MB"
            )

        # -----------------------------------------------------
        # Verify image integrity and obtain dimensions
        # -----------------------------------------------------

        try:
            # First verify the image structure.
            with Image.open(image) as img:
                img.verify()

            # Re-open after verify().
            with Image.open(image) as img:
                width, height = img.size

                if width <= 0 or height <= 0:
                    raise InvalidImageError(
                        "Image has invalid dimensions."
                    )

        except InvalidImageError:
            raise

        except Exception as error:
            raise InvalidImageError(
                f"Invalid or corrupted image file.\n{error}"
            )

        # -----------------------------------------------------
        # Minimum resolution
        # -----------------------------------------------------

        if (
            width < ImageValidator.MIN_IMAGE_WIDTH
            or height < ImageValidator.MIN_IMAGE_HEIGHT
        ):
            raise InvalidImageError(
                "Image resolution is too low for reliable diagnosis. "
                f"Minimum required resolution is "
                f"{ImageValidator.MIN_IMAGE_WIDTH}x"
                f"{ImageValidator.MIN_IMAGE_HEIGHT} pixels. "
                f"Received {width}x{height}."
            )

        # -----------------------------------------------------
        # Visual quality validation
        # -----------------------------------------------------

        ImageValidator._validate_visual_quality(image)

        return image

    # ---------------------------------------------------------
    # Visual quality validation
    # ---------------------------------------------------------

    @staticmethod
    def _validate_visual_quality(image_path: Path) -> None:
        """
        Perform basic visual-quality checks.

        Checks:
            1. Blank / nearly uniform image
            2. Excessive blur
        """

        try:
            image = cv2.imread(
                str(image_path),
                cv2.IMREAD_COLOR,
            )

        except Exception as error:
            raise InvalidImageError(
                f"Unable to analyze image quality.\n{error}"
            )

        # OpenCV could not decode the image.
        if image is None:
            raise InvalidImageError(
                "The image could not be decoded for quality analysis."
            )

        # -----------------------------------------------------
        # Convert to grayscale
        # -----------------------------------------------------

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        # -----------------------------------------------------
        # Blank / near-uniform image detection
        # -----------------------------------------------------

        intensity_std = float(np.std(gray))

        if intensity_std < ImageValidator.MIN_INTENSITY_STD:
            raise InvalidImageError(
                "Image appears blank or nearly uniform. "
                "Please capture a clear photograph of the maize leaf."
            )

        # -----------------------------------------------------
        # Excessive blur detection
        # -----------------------------------------------------

        blur_variance = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F,
            ).var()
        )

        if blur_variance < ImageValidator.MIN_BLUR_VARIANCE:
            raise InvalidImageError(
                "Image is too blurry for reliable diagnosis. "
                "Hold the camera steady and capture a sharper image "
                "of the maize leaf."
            )

    # ---------------------------------------------------------
    # Diagnostic metrics
    # ---------------------------------------------------------

    @staticmethod
    def get_quality_metrics(image_path: str) -> dict:
        """
        Return image-quality metrics for debugging and testing.

        This method does not determine whether the image should
        be accepted. Validation remains centralized in validate().
        """

        image = Path(image_path)

        if not image.exists() or not image.is_file():
            raise ImageNotFoundError(
                f"Image not found:\n{image.resolve()}"
            )

        try:
            data = cv2.imread(
                str(image),
                cv2.IMREAD_COLOR,
            )

            if data is None:
                raise InvalidImageError(
                    "Unable to decode image."
                )

            gray = cv2.cvtColor(
                data,
                cv2.COLOR_BGR2GRAY,
            )

            height, width = gray.shape

            intensity_std = float(np.std(gray))

            blur_variance = float(
                cv2.Laplacian(
                    gray,
                    cv2.CV_64F,
                ).var()
            )

            return {
                "width": int(width),
                "height": int(height),
                "file_size_bytes": int(image.stat().st_size),
                "intensity_std": round(
                    intensity_std,
                    2,
                ),
                "blur_variance": round(
                    blur_variance,
                    2,
                ),
            }

        except InvalidImageError:
            raise

        except Exception as error:
            raise InvalidImageError(
                f"Unable to calculate image quality metrics.\n{error}"
            )
