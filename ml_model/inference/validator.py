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
import json
import threading

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
    VALIDITY_ARTIFACTS_DIR = (
        Path(__file__).resolve().parents[1]
        / "validity_classifier"
        / "artifacts"
    )
    VALIDITY_CONFIG_PATH = VALIDITY_ARTIFACTS_DIR / "class_mapping.json"
    VALIDITY_MODEL_PATH = VALIDITY_ARTIFACTS_DIR / "maize_validity_best.keras"
    _validity_model = None
    _validity_config: dict | None = None
    _validity_model_lock = threading.Lock()

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
        ImageValidator._validate_maize_leaf(image)

        return image

    @classmethod
    def _load_validity_model(cls):
        if cls._validity_model is not None and cls._validity_config is not None:
            return cls._validity_model, cls._validity_config

        with cls._validity_model_lock:
            if cls._validity_model is not None and cls._validity_config is not None:
                return cls._validity_model, cls._validity_config

            if not cls.VALIDITY_CONFIG_PATH.is_file():
                raise InvalidImageError(
                    "The maize-image validity configuration is unavailable."
                )
            if not cls.VALIDITY_MODEL_PATH.is_file():
                raise InvalidImageError(
                    "The maize-image validity model is unavailable."
                )

            try:
                with cls.VALIDITY_CONFIG_PATH.open(
                    "r",
                    encoding="utf-8",
                ) as config_file:
                    config = json.load(config_file)

                class_indices = config["class_indices"]
                image_size = config["input_size"]
                threshold = float(config["valid_probability_threshold"])
                preprocessing = config["preprocessing"]
                valid_index = class_indices["valid_maize_leaf"]

                if (
                    not isinstance(image_size, list)
                    or len(image_size) != 2
                    or any(not isinstance(size, int) or size <= 0 for size in image_size)
                    or not isinstance(valid_index, int)
                    or not 0 <= threshold <= 1
                    or preprocessing
                    != "tensorflow.keras.applications.mobilenet_v2.preprocess_input"
                ):
                    raise ValueError("Invalid maize-image validity configuration.")

                import tensorflow as tf

                model = tf.keras.models.load_model(
                    cls.VALIDITY_MODEL_PATH,
                    compile=False,
                )
                output_shape = model.output_shape
                output_width = output_shape[-1] if isinstance(output_shape, tuple) else None
                if output_width not in (1, len(class_indices)):
                    raise ValueError(
                        "The maize-image validity model has an unexpected output shape."
                    )

                cls._validity_model = model
                cls._validity_config = config
                return model, config
            except InvalidImageError:
                raise
            except Exception as error:
                raise InvalidImageError(
                    f"Unable to load the maize-image validity model: {error}"
                ) from error

    @classmethod
    def _validate_maize_leaf(cls, image_path: Path) -> None:
        try:
            model, config = cls._load_validity_model()
            image_size = tuple(config["input_size"])
            with Image.open(image_path) as source:
                image = source.convert("RGB").resize(
                    image_size,
                    Image.Resampling.NEAREST,
                )

            import tensorflow as tf

            pixels = np.asarray(image, dtype=np.float32)
            input_tensor = tf.keras.applications.mobilenet_v2.preprocess_input(
                np.expand_dims(pixels, axis=0)
            )
            prediction = np.asarray(model.predict(input_tensor, verbose=0))
            if prediction.ndim != 2 or prediction.shape[0] != 1:
                raise ValueError(
                    "The maize-image validity model returned an unexpected prediction shape."
                )

            if prediction.shape[1] == 1:
                valid_probability = float(prediction[0, 0])
            else:
                valid_index = config["class_indices"]["valid_maize_leaf"]
                if valid_index >= prediction.shape[1]:
                    raise ValueError(
                        "The maize-image validity model output does not match its class mapping."
                    )
                valid_probability = float(prediction[0, valid_index])

            if not np.isfinite(valid_probability) or not 0 <= valid_probability <= 1:
                raise ValueError(
                    "The maize-image validity model returned an invalid probability."
                )
            if valid_probability < float(config["valid_probability_threshold"]):
                raise InvalidImageError(
                    "The image does not appear to show a maize leaf. "
                    "Please select a clear photo of a maize leaf."
                )
        except InvalidImageError:
            raise
        except Exception as error:
            raise InvalidImageError(
                f"Unable to validate that the image shows a maize leaf: {error}"
            ) from error

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
