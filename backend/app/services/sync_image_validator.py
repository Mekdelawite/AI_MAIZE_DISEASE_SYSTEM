"""
=========================================================
Offline Sync Image Validator
=========================================================

Validates images received through offline synchronization
before they are passed to the diagnosis service.

This validator does NOT perform diagnosis and does NOT
duplicate the existing diagnosis logic.

Responsibilities:
    - Validate file existence
    - Validate file extension
    - Validate file size
    - Validate that the file is a readable image
=========================================================
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


class SyncImageValidationError(Exception):
    """Raised when a synchronization image is invalid."""


class SyncImageValidator:
    """
    Validates images submitted through offline synchronization.
    """

    # Backend safety limit.
    #
    # The project SRS requires frontend image compression
    # to a maximum of 500 KB before synchronization.
    MAX_IMAGE_SIZE_BYTES = 500 * 1024

    ALLOWED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    @classmethod
    def validate(cls, image_path: str | Path) -> Path:
        """
        Validate a synchronization image.

        Args:
            image_path: Path to the image file.

        Returns:
            Validated Path object.

        Raises:
            SyncImageValidationError:
                If the image fails validation.
        """

        if not image_path:
            raise SyncImageValidationError(
                "Synchronization image is required."
            )

        path = Path(image_path)

        # -------------------------------------------------
        # File existence
        # -------------------------------------------------
        if not path.exists():
            raise SyncImageValidationError(
                "Synchronization image was not found."
            )

        if not path.is_file():
            raise SyncImageValidationError(
                "Synchronization image is not a valid file."
            )

        # -------------------------------------------------
        # Extension
        # -------------------------------------------------
        extension = path.suffix.lower()

        if extension not in cls.ALLOWED_EXTENSIONS:
            raise SyncImageValidationError(
                "Unsupported image format. "
                "Allowed formats: JPG, JPEG, PNG, WEBP."
            )

        # -------------------------------------------------
        # File size
        # -------------------------------------------------
        file_size = path.stat().st_size

        if file_size <= 0:
            raise SyncImageValidationError(
                "Synchronization image is empty."
            )

        if file_size > cls.MAX_IMAGE_SIZE_BYTES:
            size_kb = file_size / 1024

            raise SyncImageValidationError(
                f"Synchronization image is too large "
                f"({size_kb:.1f} KB). Maximum allowed size is 500 KB."
            )

        # -------------------------------------------------
        # Actual image validation
        # -------------------------------------------------
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception as exc:
            raise SyncImageValidationError(
                "Synchronization file is not a valid readable image."
            ) from exc

        return path