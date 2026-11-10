
"""
=========================================================
AI Diagnosis Service
=========================================================

Application-level service that combines:

    1. Fast disease prediction
    2. Top disease predictions
    3. Optional Grad-CAM explainability

Grad-CAM is initialized lazily, only when requested.
This avoids loading a second model during normal diagnosis.

Author : Nigusu Tigabu, Rediet Tsega, Sanueal Admasu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path
from typing import Any, Dict
from threading import Lock


class DiagnosisService:
    """
    Main application service for maize disease diagnosis.

    Connects the existing prediction and explainability
    components without duplicating their logic.
    """

    def __init__(
        self,
        predictor=None,
        explainability_service=None,
    ):
        """
        Initialize the diagnosis service.

        The predictor is initialized immediately because it
        is required for normal diagnosis.

        Grad-CAM is initialized only when explicitly requested.
        """

        self._predictor = predictor if predictor is not None else self._get_shared_predictor()

        # Lazy initialization: do not load Grad-CAM here.
        self._explainability_service = explainability_service

        # Prevent multiple simultaneous Grad-CAM initializations.
        self._explainability_lock = Lock()

    _shared_predictor = None
    _shared_predictor_lock = Lock()

    @classmethod
    def _get_shared_predictor(cls):
        """Create the required predictor once per process, including retries."""
        if cls._shared_predictor is None:
            with cls._shared_predictor_lock:
                if cls._shared_predictor is None:
                    cls._shared_predictor = cls._create_predictor()
        return cls._shared_predictor

    # =====================================================
    # PATH CONFIGURATION
    # =====================================================

    
    @staticmethod
    def _configure_python_paths():
        """
        Configure Python paths required by the AI modules.
        """

        import sys

        # Project root:
        # AI_MAIZE_DISEASE_SYSTEM/
        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        # AI_MAIZE_DISEASE_SYSTEM/ml_model/
        ml_model_dir = project_root / "ml_model"

        inference_dir = ml_model_dir / "inference"
        explainability_dir = ml_model_dir / "explainability"

        required_paths = [
            project_root,
            ml_model_dir,
            inference_dir,
            explainability_dir,
        ]

        for path in reversed(required_paths):
            path_string = str(path)

            if path_string not in sys.path:
                sys.path.insert(0, path_string)

        return (
            ml_model_dir,
            inference_dir,
            explainability_dir,
        )


    # =====================================================
    # COMPONENT INITIALIZATION
    # =====================================================

    @classmethod
    def _create_predictor(cls):
        """
        Create the existing DiseasePredictor.
        """

        try:
            cls._configure_python_paths()

            from inference.predictor import DiseasePredictor

            return DiseasePredictor()

        except Exception as error:
            raise RuntimeError(
                f"Unable to initialize DiseasePredictor: {error}"
            ) from error

    def _create_explainability_service(self):
        """
        Create the existing ExplainabilityService.
        Called only when Grad-CAM is requested.
        """

        try:
            self._configure_python_paths()

            from explainability.explainability_service import (
                ExplainabilityService,
            )

            return ExplainabilityService(model=self._predictor.model)

        except Exception as error:
            raise RuntimeError(
                "Unable to initialize ExplainabilityService."
            ) from error

    def _get_explainability_service(self):
        """
        Initialize Grad-CAM on demand.

        The lock prevents concurrent requests from
        initializing multiple Grad-CAM instances.
        """

        if self._explainability_service is None:

            with self._explainability_lock:

                if self._explainability_service is None:
                    self._explainability_service = (
                        self._create_explainability_service()
                    )

        return self._explainability_service

    # =====================================================
    # IMAGE VALIDATION
    # =====================================================

    @staticmethod
    def _validate_image_path(image_path: str) -> Path:
        """
        Validate the image path before diagnosis.
        """

        if not image_path:
            raise ValueError("Image path cannot be empty.")

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Image path is not a file: {path}"
            )

        return path.resolve()

    # =====================================================
    # DIAGNOSIS
    # =====================================================

    def diagnose(
        self,
        image_path: str,
        explain: bool = False,
    ) -> Dict[str, Any]:
        """
        Diagnose a maize leaf image.

        explain=False:
            Fast disease prediction only.

        explain=True:
            Disease prediction followed by Grad-CAM.
        """

        path = self._validate_image_path(image_path)

        try:

            # -------------------------------------------------
            # STEP 1 — FAST DISEASE PREDICTION
            # -------------------------------------------------

            result = self._predictor.predict(str(path))

            if not isinstance(result, dict):
                raise ValueError(
                    "DiseasePredictor returned an invalid result."
                )

            if "prediction" not in result:
                raise ValueError(
                    "Prediction result is missing 'prediction'."
                )

            if "top_predictions" not in result:
                raise ValueError(
                    "Prediction result is missing 'top_predictions'."
                )

            # -------------------------------------------------
            # STEP 2 — OPTIONAL GRAD-CAM EXPLANATION
            # -------------------------------------------------

            if explain:

                explanation_service = (
                    self._get_explainability_service()
                )

                explanation = explanation_service.explain(
                    str(path)
                )

                self._validate_explanation(explanation)

                # Verify both components identify the same class.
                prediction_class_id = (
                    result["prediction"].get("class_id")
                )

                explanation_class_id = (
                    explanation.get("class_id")
                )

                if prediction_class_id != explanation_class_id:
                    raise ValueError(
                        "Prediction class does not match "
                        "explanation class."
                    )

                result["explainability"] = explanation

            return result

        except Exception as error:

            print(
                "[AI DIAGNOSIS] Prediction failed:",
                repr(error),
            )

            raise RuntimeError(
                "Disease diagnosis failed."
            ) from error

    # =====================================================
    # EXPLANATION-ONLY OPERATION
    # =====================================================

    def explain(
        self,
        image_path: str,
    ) -> Dict[str, Any]:
        """
        Generate a Grad-CAM explanation directly.

        This operation initializes Grad-CAM on demand.
        """

        path = self._validate_image_path(image_path)

        try:

            explanation_service = (
                self._get_explainability_service()
            )

            result = explanation_service.explain(
                str(path)
            )

            self._validate_explanation(result)

            return result

        except Exception as error:

            print(
                "[AI DIAGNOSIS] Explanation failed:",
                repr(error),
            )

            raise RuntimeError(
                "Disease explanation failed."
            ) from error

    # =====================================================
    # SERVICE STATUS
    # =====================================================

    def is_ready(self) -> bool:
        """
        Check readiness of the normal disease predictor.

        Grad-CAM is optional and must not prevent normal
        disease diagnosis from being available.
        """

        try:

            if self._predictor is None:
                return False

            if hasattr(self._predictor, "is_ready"):
                return bool(self._predictor.is_ready())

            return True

        except Exception:
            return False

    # =====================================================
    # EXPLANATION VALIDATION
    # =====================================================

    @staticmethod
    def _validate_explanation(
        explanation: Dict[str, Any],
    ) -> None:
        """
        Validate a Grad-CAM explanation result.
        """

        if not isinstance(explanation, dict):
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
            if field not in explanation
        ]

        if missing_fields:
            raise ValueError(
                "Explainability result is missing "
                f"required fields: {missing_fields}"
            )

        # -------------------------------------------------
        # METHOD
        # -------------------------------------------------

        if explanation["method"] != "Grad-CAM":
            raise ValueError(
                "Unsupported explainability method: "
                f"{explanation['method']}"
            )

        # -------------------------------------------------
        # TARGET LAYER
        # -------------------------------------------------

        if not explanation["target_layer"]:
            raise ValueError(
                "Explainability target layer is empty."
            )

        # -------------------------------------------------
        # HEATMAP
        # -------------------------------------------------

        heatmap = Path(str(explanation["heatmap"]))

        if not heatmap.exists():
            raise FileNotFoundError(
                f"Heatmap file not found: {heatmap}"
            )

        if not heatmap.is_file():
            raise ValueError(
                f"Heatmap path is not a file: {heatmap}"
            )

        # -------------------------------------------------
        # OVERLAY
        # -------------------------------------------------

        overlay = Path(str(explanation["overlay"]))

        if not overlay.exists():
            raise FileNotFoundError(
                f"Overlay file not found: {overlay}"
            )

        if not overlay.is_file():
            raise ValueError(
                f"Overlay path is not a file: {overlay}"
            )

        # -------------------------------------------------
        # HEATMAP SHAPE
        # -------------------------------------------------

        shape = explanation["heatmap_shape"]

        if not isinstance(shape, (list, tuple)):
            raise ValueError(
                "Heatmap shape must be a list or tuple."
            )

        if len(shape) != 2:
            raise ValueError(
                "Grad-CAM heatmap must be 2-dimensional."
            )

    # =====================================================
    # COMPONENT ACCESS
    # =====================================================

    @property
    def predictor(self):
        """
        Access the underlying DiseasePredictor.
        """

        return self._predictor

    @property
    def explainability_service(self):
        """
        Access the underlying ExplainabilityService.

        Accessing this property initializes Grad-CAM
        if it has not already been initialized.
        """

        return self._get_explainability_service()


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("DIAGNOSIS SERVICE MODULE")
    print("=" * 70)

    try:

        service = DiagnosisService()

        print()
        print("Service initialized successfully.")

        print(
            f"Service ready: {service.is_ready()}"
        )

        print(
            "Grad-CAM initialized:",
            service._explainability_service is not None,
        )

    except Exception as error:

        print()
        print("Service initialization failed:")
        print(error)
