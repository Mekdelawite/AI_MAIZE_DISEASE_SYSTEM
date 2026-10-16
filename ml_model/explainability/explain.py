"""
=========================================================
Complete Grad-CAM Explainability Service
=========================================================

Pipeline:

    Image
      ↓
    Preprocessing
      ↓
    Model prediction
      ↓
    Grad-CAM
      ↓
    Heatmap
      ↓
    Overlay
      ↓
    Saved explanation

=========================================================
"""

from pathlib import Path
from typing import Dict, Optional

import numpy as np
from tensorflow.keras.utils import (
    load_img,
    img_to_array,
)

from gradcam import GradCAM
from heatmap import HeatmapGenerator
from overlay import GradCAMOverlay


class ExplainabilityService:
    """
    Complete explainability pipeline for the
    maize disease detection model.
    """

    # -----------------------------------------------------
    # Configuration
    # -----------------------------------------------------

    IMAGE_SIZE = (224, 224)

    CLASS_NAMES = {
        0: "Blight",
        1: "Common_Rust",
        2: "Gray_Leaf_Spot",
        3: "Healthy",
    }

    # -----------------------------------------------------
    # Initialization
    # -----------------------------------------------------

    def __init__(
        self,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize the explainability service.
        """

        if output_dir is None:

            output_dir = (
                Path(__file__).resolve().parent
                / "outputs"
            )

        self.output_dir = Path(
            output_dir
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Initialize Grad-CAM once
        self.gradcam = GradCAM()

        # Heatmap generator
        self.heatmap_generator = (
            HeatmapGenerator(
                output_size=self.IMAGE_SIZE
            )
        )

        # Overlay generator
        self.overlay_generator = (
            GradCAMOverlay(
                alpha=0.40
            )
        )

    # -----------------------------------------------------
    # Preprocess image
    # -----------------------------------------------------

    @staticmethod
    def preprocess_image(
        image_path: Path,
    ) -> np.ndarray:
        """
        Preprocess image for MobileNetV2.
        """

        image_path = Path(
            image_path
        )

        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: "
                f"{image_path}"
            )

        image = load_img(
            image_path,
            target_size=(
                224,
                224,
            ),
            color_mode="rgb",
        )

        image_array = img_to_array(
            image
        ).astype(
            np.float32
        )

        # MobileNetV2 preprocessing
        image_array = (
            image_array / 127.5
        ) - 1.0

        image_array = np.expand_dims(
            image_array,
            axis=0,
        )

        return image_array

    # -----------------------------------------------------
    # Explain image
    # -----------------------------------------------------

    def explain(
        self,
        image_path,
    ) -> Dict:
        """
        Generate a complete explanation.

        Returns
        -------
        dict
            Prediction and generated file paths.
        """

        image_path = Path(
            image_path
        )

        # -------------------------------------------------
        # Load original image
        # -------------------------------------------------

        original_image = (
            self.overlay_generator.load_image(
                image_path
            )
        )

        # -------------------------------------------------
        # Preprocess
        # -------------------------------------------------

        processed_image = (
            self.preprocess_image(
                image_path
            )
        )

        # -------------------------------------------------
        # Generate Grad-CAM
        # -------------------------------------------------

        (
            heatmap,
            predicted_class,
            confidence,
        ) = self.gradcam.generate(
            processed_image
        )

        # -------------------------------------------------
        # Class name
        # -------------------------------------------------

        class_name = self.CLASS_NAMES.get(
            predicted_class,
            "Unknown",
        )

        # -------------------------------------------------
        # Generate visual heatmap
        # -------------------------------------------------

        heatmap_image = (
            self.heatmap_generator.generate(
                heatmap
            )
        )

        # -------------------------------------------------
        # Create overlay
        # -------------------------------------------------

        overlay = (
            self.overlay_generator.create(
                original_image,
                heatmap_image,
            )
        )

        # -------------------------------------------------
        # Output filenames
        # -------------------------------------------------

        image_stem = image_path.stem

        heatmap_path = (
            self.output_dir
            / f"{image_stem}_heatmap.jpg"
        )

        overlay_path = (
            self.output_dir
            / f"{image_stem}_overlay.jpg"
        )

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        self.heatmap_generator.save(
            heatmap_image,
            heatmap_path,
        )

        self.overlay_generator.save(
            overlay,
            overlay_path,
        )

        # -------------------------------------------------
        # Return result
        # -------------------------------------------------

        return {
            "image": str(image_path),
            "class_id": predicted_class,
            "class_name": class_name,
            "confidence": round(
                confidence * 100,
                2,
            ),
            "heatmap": str(
                heatmap_path
            ),
            "overlay": str(
                overlay_path
            ),
            "heatmap_shape": list(
                heatmap.shape
            ),
        }