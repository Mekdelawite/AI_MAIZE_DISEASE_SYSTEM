"""
=========================================================
AI Diagnosis Service
=========================================================

Application-level service that combines:

    1. Fast disease prediction
    2. Top disease predictions
    3. Optional Grad-CAM explainability

Architecture:

    Flask API
        |
        v
    DiagnosisService
        |
        +--------------------------+
        |                          |
        v                          v
    DiseasePredictor       ExplainabilityService
        |                          |
        v                          v
    MobileNetV2                  Grad-CAM

Author : Nigusu Tigabu, Rediet Tsega, Sanueal Admasu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path
from typing import Any, Dict


class DiagnosisService:
    """
    Main application service for maize disease diagnosis.

    This service connects the existing prediction and
    explainability components without duplicating their logic.
    """

    def __init__(
        self,
        predictor=None,
        explainability_service=None,
    ):
        """
        Initialize the diagnosis service.

        Parameters
        ----------
        predictor:
            Optional DiseasePredictor instance.

        explainability_service:
            Optional ExplainabilityService instance.

        Supplying instances is useful for testing.
        """

        self._predictor = (
            predictor
            if predictor is not None
            else self._create_predictor()
        )

        self._explainability_service = (
            explainability_service
            if explainability_service is not None
            else self._create_explainability_service()
        )

    # =====================================================
    # PATH CONFIGURATION
    # =====================================================

    @staticmethod
    def _configure_python_paths():
        """
        Configure Python paths required by the AI modules.

        Project structure:

            AI_MAIZE_DISEASE_SYSTEM/
                ml_model/
                    inference/
                    explainability/
                    ai_service/

        The inference modules use local imports such as:

            from config import ...
            from preprocess import ...
            from utils import ...

        Therefore both ml_model and ml_model/inference
        must be available in sys.path.
        """

        import sys

        ml_model_dir = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

        inference_dir = (
            ml_model_dir
            / "inference"
        )

        explainability_dir = (
            ml_model_dir
            / "explainability"
        )

        required_paths = [
            ml_model_dir,
            inference_dir,
            explainability_dir,
        ]

        for path in required_paths:

            path_string = str(path)

            if path_string not in sys.path:

                sys.path.insert(
                    0,
                    path_string,
                )

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

        The predictor is loaded only once by its own
        singleton implementation.
        """

        try:

            cls._configure_python_paths()

            from inference.predictor import (
                DiseasePredictor,
            )

            return DiseasePredictor()

        except Exception as error:

            raise RuntimeError(
                "Unable to initialize DiseasePredictor."
            ) from error

    @classmethod
    def _create_explainability_service(cls):
        """
        Create the existing ExplainabilityService.
        """

        try:

            cls._configure_python_paths()

            from explainability_service import (
                ExplainabilityService,
            )

            return ExplainabilityService()

        except Exception:

            try:

                cls._configure_python_paths()

                from explainability.explainability_service import (
                    ExplainabilityService,
                )

                return ExplainabilityService()

            except Exception as error:

                raise RuntimeError(
                    "Unable to initialize "
                    "ExplainabilityService."
                ) from error

    # =====================================================
    # IMAGE VALIDATION
    # =====================================================

    @staticmethod
    def _validate_image_path(
        image_path: str,
    ) -> Path:
        """
        Validate the image path before diagnosis.
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

        Parameters
        ----------
        image_path:
            Path to the maize leaf image.

        explain:
            False:
                Fast disease prediction only.

            True:
                Disease prediction followed by
                Grad-CAM explanation.

        Returns
        -------
        dict
            Diagnosis result.
        """

        path = self._validate_image_path(
            image_path
        )

        try:

            # -------------------------------------------------
            # STEP 1 — FAST PREDICTION
            # -------------------------------------------------

            result = self._predictor.predict(
                str(path)
            )

            if not isinstance(result, dict):

                raise ValueError(
                    "DiseasePredictor returned "
                    "an invalid result."
                )

            if "prediction" not in result:

                raise ValueError(
                    "Prediction result is missing "
                    "'prediction'."
                )

            if "top_predictions" not in result:

                raise ValueError(
                    "Prediction result is missing "
                    "'top_predictions'."
                )

            # -------------------------------------------------
            # STEP 2 — OPTIONAL GRAD-CAM
            # -------------------------------------------------

            if explain:

                explanation = (
                    self._explainability_service.explain(
                        str(path)
                    )
                )

                self._validate_explanation(
                    explanation
                )

                # -------------------------------------------------
                # Make sure prediction and explanation refer
                # to the same predicted class.
                # -------------------------------------------------

                prediction_class_id = (
                    result["prediction"]
                    .get("class_id")
                )

                explanation_class_id = (
                    explanation.get("class_id")
                )

                if (
                    prediction_class_id
                    != explanation_class_id
                ):

                    raise ValueError(
                        "Prediction class does not "
                        "match explanation class."
                    )

                result["explainability"] = (
                    explanation
                )

            return result

        except Exception as error:

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

        This does not perform the normal predictor
        operation first.
        """

        path = self._validate_image_path(
            image_path
        )

        try:

            result = (
                self._explainability_service.explain(
                    str(path)
                )
            )

            self._validate_explanation(
                result
            )

            return result

        except Exception as error:

            raise RuntimeError(
                "Disease explanation failed."
            ) from error

    # =====================================================
    # SERVICE STATUS
    # =====================================================

    def is_ready(self) -> bool:
        """
        Check whether both diagnosis components
        are available.
        """

        try:

            predictor_ready = (
                self._predictor is not None
            )

            explanation_ready = (
                self._explainability_service
                is not None
            )

            if not predictor_ready:

                return False

            if not explanation_ready:

                return False

            # -------------------------------------------------
            # Ask explainability service if it supports
            # is_ready().
            # -------------------------------------------------

            if hasattr(
                self._explainability_service,
                "is_ready",
            ):

                return bool(
                    self._explainability_service.is_ready()
                )

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

        if not isinstance(
            explanation,
            dict,
        ):

            raise ValueError(
                "Explainability result must "
                "be a dictionary."
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

        # -----------------------------------------------------
        # Method
        # -----------------------------------------------------

        if explanation["method"] != "Grad-CAM":

            raise ValueError(
                "Unsupported explainability method: "
                f"{explanation['method']}"
            )

        # -----------------------------------------------------
        # Target layer
        # -----------------------------------------------------

        if not explanation["target_layer"]:

            raise ValueError(
                "Explainability target layer is empty."
            )

        # -----------------------------------------------------
        # Heatmap
        # -----------------------------------------------------

        heatmap = Path(
            str(
                explanation["heatmap"]
            )
        )

        if not heatmap.exists():

            raise FileNotFoundError(
                f"Heatmap file not found: {heatmap}"
            )

        if not heatmap.is_file():

            raise ValueError(
                f"Heatmap path is not a file: {heatmap}"
            )

        # -----------------------------------------------------
        # Overlay
        # -----------------------------------------------------

        overlay = Path(
            str(
                explanation["overlay"]
            )
        )

        if not overlay.exists():

            raise FileNotFoundError(
                f"Overlay file not found: {overlay}"
            )

        if not overlay.is_file():

            raise ValueError(
                f"Overlay path is not a file: {overlay}"
            )

        # -----------------------------------------------------
        # Heatmap shape
        # -----------------------------------------------------

        shape = explanation[
            "heatmap_shape"
        ]

        if not isinstance(
            shape,
            (list, tuple),
        ):

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
        """

        return self._explainability_service


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

    except Exception as error:

        print()
        print(
            "Service initialization failed:"
        )

        print(error)