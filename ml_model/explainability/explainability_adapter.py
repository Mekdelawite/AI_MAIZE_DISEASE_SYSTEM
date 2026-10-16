"""
=========================================================
Explainability Adapter
=========================================================

Provides a simple interface between the inference system
and the Grad-CAM explainability pipeline.

The adapter keeps Grad-CAM implementation details out of
the main prediction code.

=========================================================
"""

from pathlib import Path
from typing import Dict, Optional

from explain import ExplainabilityService


class ExplainabilityAdapter:
    """
    Safe interface for generating Grad-CAM explanations.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize the explainability service.
        """

        self.service = ExplainabilityService(
            output_dir=output_dir
        )

    # -----------------------------------------------------
    # Generate explanation
    # -----------------------------------------------------

    def explain(
        self,
        image_path,
    ) -> Dict:
        """
        Generate a Grad-CAM explanation for an image.

        Parameters
        ----------
        image_path:
            Path to the original image.

        Returns
        -------
        dict
            Explanation information.
        """

        image_path = Path(
            image_path
        )

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        result = self.service.explain(
            image_path
        )

        return {
            "method": "Grad-CAM",
            "target_layer": "Conv_1",
            "class_id": result["class_id"],
            "class_name": result["class_name"],
            "confidence": result["confidence"],
            "heatmap": result["heatmap"],
            "overlay": result["overlay"],
            "heatmap_shape": result[
                "heatmap_shape"
            ],
        }


# ---------------------------------------------------------
# Simple factory function
# ---------------------------------------------------------

def create_explainability_adapter(
    output_dir: Optional[Path] = None,
) -> ExplainabilityAdapter:
    """
    Create and return an ExplainabilityAdapter.
    """

    return ExplainabilityAdapter(
        output_dir=output_dir
    )