import cv2
import numpy as np
import pytest
from PIL import Image

from ml_model.inference.exceptions import InvalidImageError
from ml_model.inference.validator import ImageValidator


def test_image_validator_minimum_dimensions():
    assert ImageValidator.MIN_IMAGE_WIDTH == 200
    assert ImageValidator.MIN_IMAGE_HEIGHT == 200


def test_image_validator_rejects_image_below_minimum(tmp_path):
    image_path = tmp_path / "too_small.jpg"
    Image.new("RGB", (199, 200), (120, 150, 80)).save(image_path)

    with pytest.raises(InvalidImageError, match="Minimum required resolution is 200x200"):
        ImageValidator.validate(str(image_path))


def test_image_validator_accepts_minimum_dimensions(tmp_path):
    image_path = tmp_path / "minimum.jpg"

    rng = np.random.default_rng(42)
    array = rng.integers(0, 256, size=(200, 200, 3), dtype=np.uint8)
    Image.fromarray(array, "RGB").save(image_path, quality=95)

    result = ImageValidator.validate(str(image_path))

    assert result == image_path
