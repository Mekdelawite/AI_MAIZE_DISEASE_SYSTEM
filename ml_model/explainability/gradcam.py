"""
=========================================================
Grad-CAM Explainability Engine
=========================================================

Generates Class Activation Maps (Grad-CAM) for the
AI Maize Disease Detection System.

Target layer:
    Conv_1

Target layer output:
    (None, 7, 7, 1280)

Model:
    MobileNetV2

TensorFlow:
    2.21+

=========================================================
"""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model


class GradCAM:
    """
    Grad-CAM implementation for the maize disease model.

    The class loads the trained model once and creates
    a Grad-CAM heatmap for a selected prediction class.
    """

    # -----------------------------------------------------
    # Configuration
    # -----------------------------------------------------

    TARGET_LAYER_NAME = "Conv_1"

    MODEL_PATH = (
        Path(__file__).resolve().parents[1]
        / "models"
        / "best_model.h5"
    )

    IMAGE_SIZE = (224, 224)

    # -----------------------------------------------------
    # Initialization
    # -----------------------------------------------------

    def __init__(
        self,
        model_path: Optional[Path] = None,
        target_layer_name: str = TARGET_LAYER_NAME,
    ):
        """
        Initialize the Grad-CAM engine.

        Parameters
        ----------
        model_path:
            Path to the trained Keras model.

        target_layer_name:
            Name of the convolutional layer used
            for Grad-CAM.
        """

        self.model_path = Path(
            model_path
            if model_path is not None
            else self.MODEL_PATH
        )

        self.target_layer_name = target_layer_name

        self.model = self._load_model()

        self.target_layer = self._get_target_layer()

        self.grad_model = self._build_grad_model()

    # -----------------------------------------------------
    # Model loading
    # -----------------------------------------------------

    def _load_model(self):
        """
        Load the trained Keras model.
        """

        if not self.model_path.exists():

            raise FileNotFoundError(
                f"Model not found: {self.model_path}"
            )

        print(
            f"Loading Grad-CAM model: "
            f"{self.model_path}"
        )

        model = load_model(
            self.model_path,
            compile=False,
        )

        print(
            "Grad-CAM model loaded successfully."
        )

        return model

    # -----------------------------------------------------
    # Target layer
    # -----------------------------------------------------

    def _get_target_layer(self):
        """
        Retrieve the target convolutional layer.
        """

        try:

            layer = self.model.get_layer(
                self.target_layer_name
            )

        except ValueError as exc:

            raise ValueError(
                f"Grad-CAM target layer "
                f"'{self.target_layer_name}' "
                f"was not found in the model."
            ) from exc

        if not isinstance(
            layer,
            tf.keras.layers.Conv2D
        ):

            raise TypeError(
                f"Layer '{self.target_layer_name}' "
                f"is not a Conv2D layer."
            )

        return layer

    # -----------------------------------------------------
    # Grad-CAM model
    # -----------------------------------------------------

    def _build_grad_model(self):
        """
        Create a model that returns:

        1. Target convolutional activations
        2. Final class predictions
        """

        return tf.keras.models.Model(
            inputs=self.model.inputs,
            outputs=[
                self.target_layer.output,
                self.model.output,
            ],
        )

    # -----------------------------------------------------
    # Input validation
    # -----------------------------------------------------

    def _validate_input(
        self,
        image: np.ndarray,
    ):
        """
        Validate the input image tensor.
        """

        if not isinstance(
            image,
            np.ndarray
        ):

            raise TypeError(
                "Image must be a NumPy array."
            )

        if image.ndim != 4:

            raise ValueError(
                "Image must have shape "
                "(batch, height, width, channels). "
                f"Received: {image.shape}"
            )

        if image.shape[1:] != (
            224,
            224,
            3,
        ):

            raise ValueError(
                "Expected image shape "
                "(batch, 224, 224, 3). "
                f"Received: {image.shape}"
            )

    # -----------------------------------------------------
    # Generate Grad-CAM
    # -----------------------------------------------------

    def generate(
        self,
        image: np.ndarray,
        class_index: Optional[int] = None,
    ) -> Tuple[np.ndarray, int, float]:
        """
        Generate a Grad-CAM heatmap.

        Parameters
        ----------
        image:
            Preprocessed image with shape:

                (1, 224, 224, 3)

        class_index:
            Class to explain.

            If None, the predicted class is used.

        Returns
        -------
        heatmap:
            Normalized heatmap with shape:

                (7, 7)

        predicted_class:
            Selected class index.

        confidence:
            Model confidence for that class.
        """

        self._validate_input(image)

        image_tensor = tf.convert_to_tensor(
            image,
            dtype=tf.float32,
        )

        # -------------------------------------------------
        # Forward pass + gradient recording
        # -------------------------------------------------

        with tf.GradientTape() as tape:

            conv_outputs, predictions = (
                self.grad_model(
                    image_tensor,
                    training=False,
                )
            )

            if class_index is None:

                class_index = tf.argmax(
                    predictions[0]
                )

            class_index = tf.cast(
                class_index,
                tf.int32,
            )

            class_score = predictions[
                0,
                class_index,
            ]

        # -------------------------------------------------
        # Calculate gradients
        # -------------------------------------------------

        gradients = tape.gradient(
            class_score,
            conv_outputs,
        )

        if gradients is None:

            raise RuntimeError(
                "Gradients could not be calculated "
                "for the target layer."
            )

        # -------------------------------------------------
        # Global average pooling of gradients
        # -------------------------------------------------

        pooled_gradients = tf.reduce_mean(
            gradients,
            axis=(0, 1, 2),
        )

        # -------------------------------------------------
        # Extract activation map
        # -------------------------------------------------

        conv_outputs = conv_outputs[0]

        # -------------------------------------------------
        # Weight activation channels
        # -------------------------------------------------

        weighted_activations = (
            conv_outputs
            * pooled_gradients
        )

        # -------------------------------------------------
        # Combine channels
        # -------------------------------------------------

        heatmap = tf.reduce_sum(
            weighted_activations,
            axis=-1,
        )

        # -------------------------------------------------
        # ReLU
        # -------------------------------------------------

        heatmap = tf.maximum(
            heatmap,
            0,
        )

        # -------------------------------------------------
        # Normalize
        # -------------------------------------------------

        max_value = tf.reduce_max(
            heatmap
        )

        heatmap = tf.where(
            max_value > 0,
            heatmap / max_value,
            tf.zeros_like(heatmap),
        )

        heatmap = heatmap.numpy()

        predicted_class = int(
            class_index.numpy()
        )

        confidence = float(
            predictions[
                0,
                predicted_class
            ].numpy()
        )

        return (
            heatmap,
            predicted_class,
            confidence,
        )