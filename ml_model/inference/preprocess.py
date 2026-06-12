"""
=========================================================
Image Preprocessing Module
=========================================================

Prepares validated images for AI model inference.

Author : Nigusu Tigabu
Project: AI-Based Maize Disease Detection System
=========================================================
"""

import numpy as np
from PIL import Image

from tensorflow.keras.applications.mobilenet_v2 import preprocess_input


class ImagePreprocessor:
    """
    Handles image preprocessing for MobileNetV2 model.
    """

    def __init__(self, target_size=(224, 224)):
        self.target_size = target_size

    def load_image(self, image_path):
        """
        Load image and convert to RGB.
        """
        image = Image.open(image_path).convert("RGB")
        return image

    def resize_image(self, image):
        """
        Resize image to model input size.
        """
        return image.resize(self.target_size)

    def to_array(self, image):
        """
        Convert PIL image to numpy array.
        """
        return np.array(image)

    def preprocess(self, image_path):
        """
        Full preprocessing pipeline.

        Parameters
        ----------
        image_path : str

        Returns
        -------
        np.ndarray
            Preprocessed image ready for model prediction.
        """

        # 1. Load image
        image = self.load_image(image_path)

        # 2. Resize image
        image = self.resize_image(image)

        # 3. Convert to array
        image_array = self.to_array(image)

        # 4. Expand dimensions (1, 224, 224, 3)
        image_array = np.expand_dims(image_array, axis=0)

        # 5. Apply MobileNetV2 preprocessing
        image_array = preprocess_input(image_array)

        return image_array