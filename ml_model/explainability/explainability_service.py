"""
=========================================================
Explainability Service
=========================================================

Provides a clean application-level interface for
AI disease prediction explainability.

Responsibilities:
    - Validate image input
    - Call ExplainabilityAdapter
    - Return a standardized explanation result
    - Keep Grad-CAM implementation details out of
      the API/frontend layers

Pipeline:

    Image
      ↓
    ExplainabilityService
      ↓
    ExplainabilityAdapter
      ↓
    Grad-CAM
      ↓
    Heatmap + Overlay

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path
from typing import Any, Dict


class ExplainabilityService:
    """
    Application-level service for Grad-CAM explanations.

    The service intentionally does not implement Grad-CAM
    itself. That responsibility belongs to the adapter.

    This keeps the architecture modular and makes it easier
    to replace or extend the explainability method later.
    """

    def __init__(self, adapter=None):
        """
        Initialize the explainability service.

        Parameters
        ----------
        adapter:
            Optional ExplainabilityAdapter instance.

            If an adapter is not supplied, the service
            creates one automatically.
        """

        self._adapter = (
            adapter
            if adapter is not None
            else self._create_adapter()
        )

    # =====================================================
    # ADAPTER INITIALIZATION
    # =====================================================

    @staticmethod
    def _create_adapter():
        """
        Create the ExplainabilityAdapter.

        The import is performed here rather than at module
        import time so the service remains lightweight.
        """

        try:

            from explainability_adapter import (
                ExplainabilityAdapter
            )

            return ExplainabilityAdapter()

        except Exception as error:

            raise RuntimeError(
                "Unable to initialize "
                "ExplainabilityAdapter."
            ) from error

    # =====================================================
    # INPUT VALIDATION
    # =====================================================

    @staticmethod
    def _validate_image_path(
        image_path: str
    ) -> Path:
        """
        Validate the supplied image path.

        Returns
        -------
        Path
            Validated image path.

        Raises
        ------
        ValueError
            If the path is empty or invalid.

        FileNotFoundError
            If the image does not exist.
        """

        if not image_path:

            raise ValueError(
                "Image path cannot be empty."
            )

        path = Path(image_path)

        if not path.exists():

            raise FileNotFoundError(
                f"Image not found: {path}"
            )

        if not path.is_file():

            raise ValueError(
                f"Image path is not a file: {path}"
            )

        return path

    # =====================================================
    # EXPLANATION
    # =====================================================

    def explain(
        self,
        image_path: str
    ) -> Dict[str, Any]:
        """
        Generate an explanation for a maize leaf image.

        Parameters
        ----------
        image_path:
            Path to the maize leaf image.

        Returns
        -------
        dict
            Standardized explainability result.

        Example
        -------
        result = service.explain(
            "test_images/sample.jpg"
        )
        """

        # -------------------------------------------------
        # Validate input
        # -------------------------------------------------

        path = self._validate_image_path(
            image_path
        )

        # -------------------------------------------------
        # Generate explanation
        # -------------------------------------------------

        try:

            explanation = self._adapter.explain(
                str(path)
            )

        except Exception as error:

            raise RuntimeError(
                "Explainability generation failed."
            ) from error

        # -------------------------------------------------
        # Validate adapter result
        # -------------------------------------------------

        self._validate_result(
            explanation
        )

        # -------------------------------------------------
        # Return standardized result
        # -------------------------------------------------

        return {
            "method": explanation[
                "method"
            ],

            "target_layer": explanation[
                "target_layer"
            ],

            "class_id": explanation[
                "class_id"
            ],

            "class_name": explanation[
                "class_name"
            ],

            "confidence": explanation[
                "confidence"
            ],

            "heatmap": explanation[
                "heatmap"
            ],

            "overlay": explanation[
                "overlay"
            ],

            "heatmap_shape": explanation[
                "heatmap_shape"
            ],
        }

    # =====================================================
    # RESULT VALIDATION
    # =====================================================

    @staticmethod
    def _validate_result(
        result: Dict[str, Any]
    ) -> None:
        """
        Validate the structure returned by the adapter.

        This prevents incomplete explainability results
        from propagating into the API or frontend.
        """

        if not isinstance(
            result,
            dict
        ):

            raise ValueError(
                "Explainability result must be a dictionary."
            )

        required_fields = [
            "method",
            "target_layer",
            "class_id",
            "class_name",
            "confidence",
            "heatmap",
            "overlay",
            "heatmap_shape",
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in result
        ]

        if missing_fields:

            raise ValueError(
                "Explainability result is missing "
                f"required fields: {missing_fields}"
            )

        # -------------------------------------------------
        # Validate generated files
        # -------------------------------------------------

        heatmap = Path(
            result["heatmap"]
        )

        overlay = Path(
            result["overlay"]
        )

        if not heatmap.exists():

            raise FileNotFoundError(
                f"Heatmap file not found: {heatmap}"
            )

        if not overlay.exists():

            raise FileNotFoundError(
                f"Overlay file not found: {overlay}"
            )

    # =====================================================
    # HEALTH CHECK
    # =====================================================

    def is_ready(self) -> bool:
        """
        Check whether the explainability service is ready.

        Returns
        -------
        bool
            True if the adapter is initialized.
        """

        return self._adapter is not None

    # =====================================================
    # ADAPTER ACCESS
    # =====================================================

    @property
    def adapter(self):
        """
        Return the underlying explainability adapter.

        This is primarily useful for testing or advanced
        application integration.
        """

        return self._adapter