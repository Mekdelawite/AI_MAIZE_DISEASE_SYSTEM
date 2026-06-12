"""
=========================================================
Image Validator
=========================================================

Validates uploaded images before sending them
to the AI model.

Author : Nigusu Tgabu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path
from PIL import Image

from config import (
    SUPPORTED_EXTENSIONS,
    MAX_IMAGE_SIZE_BYTES,
)

from exceptions import (
    ImageNotFoundError,
    UnsupportedImageFormatError,
    ImageTooLargeError,
    InvalidImageError,
)


class ImageValidator:
    """
    Performs all image validation checks.
    """

    @staticmethod
    def validate(image_path: str) -> Path:
        """
        Validate an image.

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
        UnsupportedImageFormatError
        ImageTooLargeError
        InvalidImageError
        """

        image = Path(image_path)

        # -------------------------------
        # Check file exists
        # -------------------------------
        if not image.exists():
            raise ImageNotFoundError(
                f"Image not found:\n{image.resolve()}"
            )

        # -------------------------------
        # Check extension
        # -------------------------------
        extension = image.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedImageFormatError(
                f"Unsupported image format: {extension}\n"
                f"Supported formats: {SUPPORTED_EXTENSIONS}"
            )

        # -------------------------------
        # Check file size
        # -------------------------------
        file_size = image.stat().st_size

        if file_size > MAX_IMAGE_SIZE_BYTES:
            raise ImageTooLargeError(
                f"Image size exceeds "
                f"{MAX_IMAGE_SIZE_BYTES/(1024*1024):.1f} MB"
            )

        # -------------------------------
        # Verify image integrity
        # -------------------------------
        try:

            with Image.open(image) as img:

                img.verify()

        except Exception as error:

            raise InvalidImageError(
                f"Invalid image file.\n{error}"
            )

        return image