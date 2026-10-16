
"""
=========================================================
Image Validator Tests
=========================================================

Tests the ImageValidator used by the AI inference layer.

Project:
    AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path

import pytest

from ml_model.inference.validator import ImageValidator
from ml_model.inference.exceptions import (
    ImageNotFoundError,
    UnsupportedImageFormatError,
    InvalidImageError,
)


# =========================================================
# PROJECT PATH
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent


# =========================================================
# TEST IMAGE
# =========================================================

TEST_IMAGE = (
    PROJECT_ROOT
    / "ml_model"
    / "inference"
    / "test_images"
    / "blure.png"
)


# =========================================================
# TEST 1
# =========================================================

def test_sample_image_exists():
    """Verify that the test image exists."""

    assert TEST_IMAGE.exists()
    assert TEST_IMAGE.is_file()


# =========================================================
# TEST 2
# =========================================================

def test_valid_image_passes():
    """Verify that a valid image passes validation."""

    result = ImageValidator.validate(
        str(TEST_IMAGE)
    )

    assert result == TEST_IMAGE
    assert result.exists()


# =========================================================
# TEST 3
# =========================================================

def test_quality_metrics():
    """Verify that image-quality metrics are calculated."""

    metrics = ImageValidator.get_quality_metrics(
        str(TEST_IMAGE)
    )

    assert isinstance(metrics, dict)

    assert metrics["width"] > 0
    assert metrics["height"] > 0
    assert metrics["file_size_bytes"] > 0
    assert metrics["intensity_std"] >= 0
    assert metrics["blur_variance"] >= 0


# =========================================================
# TEST 4
# =========================================================

def test_missing_image():
    """Verify that a missing image is rejected."""

    missing_image = (
        PROJECT_ROOT
        / "ml_model"
        / "inference"
        / "test_images"
        / "does_not_exist.jpg"
    )

    with pytest.raises(ImageNotFoundError):

        ImageValidator.validate(
            str(missing_image)
        )


# =========================================================
# TEST 5
# =========================================================

def test_unsupported_extension():
    """Verify that unsupported file extensions are rejected."""

    test_file = (
        PROJECT_ROOT
        / "ml_model"
        / "inference"
        / "test_images"
        / "validator_test.txt"
    )

    test_file.write_text(
        "This is not an image.",
        encoding="utf-8",
    )

    try:

        with pytest.raises(
            UnsupportedImageFormatError
        ):

            ImageValidator.validate(
                str(test_file)
            )

    finally:

        if test_file.exists():
            test_file.unlink()


# =========================================================
# TEST 6
# =========================================================

def test_empty_image():
    """Verify that an empty image file is rejected."""

    test_file = (
        PROJECT_ROOT
        / "ml_model"
        / "inference"
        / "test_images"
        / "empty_test.jpg"
    )

    test_file.write_bytes(b"")

    try:

        with pytest.raises(
            InvalidImageError
        ):

            ImageValidator.validate(
                str(test_file)
            )

    finally:

        if test_file.exists():
            test_file.unlink()


# =========================================================
# TEST 7
# =========================================================

def test_validator_methods_exist():
    """Verify that required validator methods exist."""

    assert callable(
        ImageValidator.validate
    )

    assert callable(
        ImageValidator.get_quality_metrics
    )