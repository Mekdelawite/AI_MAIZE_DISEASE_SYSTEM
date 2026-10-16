"""
=========================================================
Image Preprocessing Module
=========================================================

This module prepares images for MobileNetV2 inference.

Responsibilities:
- Load image
- Convert to RGB
- Resize
- Convert to NumPy array
- Normalize
- Add batch dimension

Author : Nigusu Tgabu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path
from typing import Tuple

import numpy as np
import tensorflow as tf
from PIL import Image

from config import IMAGE_SIZE
from validator import ImageValidator


class ImagePreprocessor:
    """
    Handles image preprocessing for AI inference.
    """

    @staticmethod
    def load_image(image_path: str) -> Image.Image:
        """
        Load image after validation.
        """

        valid_path = ImageValidator.validate(image_path)

        image = Image.open(valid_path)

        image = image.convert("RGB")

        return image

    @staticmethod
    def resize(image: Image.Image) -> Image.Image:
        """
        Resize image to model input size.
        """

        return image.resize(IMAGE_SIZE)

    @staticmethod
    def image_to_array(image: Image.Image) -> np.ndarray:
        """
        Convert PIL image to NumPy array.
        """

        return np.asarray(image, dtype=np.float32)

    @staticmethod
    def normalize(image_array: np.ndarray) -> np.ndarray:
        """
        Apply MobileNetV2 preprocessing.
        """

        return tf.keras.applications.mobilenet_v2.preprocess_input(
            image_array
        )

    @staticmethod
    def add_batch_dimension(image_array: np.ndarray) -> np.ndarray:
        """
        Convert shape

        (224,224,3)

        into

        (1,224,224,3)
        """

        return np.expand_dims(image_array, axis=0)

    @classmethod
    def preprocess(cls, image_path: str) -> np.ndarray:
        """
        Complete preprocessing pipeline.
        """

        image = cls.load_image(image_path)

        image = cls.resize(image)

        image_array = cls.image_to_array(image)

        image_array = cls.normalize(image_array)

        image_array = cls.add_batch_dimension(image_array)

        return image_array