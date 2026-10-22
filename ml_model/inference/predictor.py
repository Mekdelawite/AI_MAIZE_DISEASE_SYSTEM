"""
=========================================================
AI Disease Predictor
=========================================================

Loads the trained model once and performs
high-performance inference.

Grad-CAM explainability is optional and is only
initialized when explicitly requested.

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path
from threading import Lock
import os
import sys

# Some Windows launch environments omit System32 from PATH. TensorFlow's
# native extensions still need the Microsoft runtime DLLs stored there.
_DLL_DIRECTORY_HANDLES = []
if os.name == "nt" and hasattr(os, "add_dll_directory"):
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    system_dll_directory = system_root / "System32"
    if system_dll_directory.is_dir():
        system_dll_path = str(system_dll_directory)
        current_path_entries = {
            entry.rstrip("\\/").casefold()
            for entry in os.environ.get("PATH", "").split(os.pathsep)
            if entry
        }
        if system_dll_path.rstrip("\\/").casefold() not in current_path_entries:
            os.environ["PATH"] = os.pathsep.join(
                [system_dll_path, os.environ.get("PATH", "")]
            )
        _DLL_DIRECTORY_HANDLES.append(
            os.add_dll_directory(system_dll_path)
        )
        print(
            "[DIAGNOSIS SERVICE] Registered Windows runtime DLL path:",
            system_dll_path,
        )

import numpy as np
import tensorflow as tf

from config import (
    MODEL_PATH,
    ENABLE_VERBOSE,
    MODEL_ARCHITECTURE,
    MODEL_VERSION,
    CONFIDENCE_THRESHOLD,
)

from preprocess import ImagePreprocessor

from utils import (
    Timer,
    get_best_prediction,
    get_top_predictions,
)

from logger import (
    log_prediction,
    log_error,
)

from exceptions import PredictionError


class DiseasePredictor:
    """
    Singleton predictor.

    The main prediction model is loaded only once
    during the lifetime of the application.

    Grad-CAM is loaded lazily only when explain=True.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):

        with cls._lock:

            if cls._instance is None:

                instance = super().__new__(cls)

                instance._explainability_adapter = None

                instance._load_model()

                # Cache only a fully initialized predictor. If model loading
                # fails, the next request can retry cleanly.
                cls._instance = instance

        return cls._instance

    # =====================================================
    # MODEL LOADING
    # =====================================================

    def _load_model(self):

        try:

            print("Loading AI model...")

            self.model = tf.keras.models.load_model(
                MODEL_PATH,
                compile=False,
            )

            print("Model loaded successfully.")

            self._warmup()

        except Exception as error:

            raise PredictionError(
                f"Unable to load model.\n{error}"
            )

    # =====================================================
    # MODEL WARMUP
    # =====================================================

    def _warmup(self):
        """
        Warm-up TensorFlow to reduce latency
        on the first real prediction.
        """

        dummy = np.zeros(
            (1, 224, 224, 3),
            dtype=np.float32
        )

        self.model.predict(
            dummy,
            verbose=0
        )

    # =====================================================
    # LAZY EXPLAINABILITY INITIALIZATION
    # =====================================================

    def _get_explainability_adapter(self):
        """
        Load the Grad-CAM adapter only when needed.

        Normal predictions do not initialize Grad-CAM.
        """

        if self._explainability_adapter is not None:

            return self._explainability_adapter

        try:

            # -------------------------------------------------
            # Find ml_model directory
            # -------------------------------------------------

            ml_model_dir = (
                Path(__file__).resolve().parents[1]
            )

            explainability_dir = (
                ml_model_dir / "explainability"
            )

            # -------------------------------------------------
            # Add explainability directory to sys.path
            # -------------------------------------------------

            explainability_path = str(
                explainability_dir
            )

            if explainability_path not in sys.path:

                sys.path.insert(
                    0,
                    explainability_path
                )

            # -------------------------------------------------
            # Import Grad-CAM adapter only when required
            # -------------------------------------------------

            from explainability_adapter import (
                ExplainabilityAdapter
            )

            # -------------------------------------------------
            # Initialize adapter
            # -------------------------------------------------

            self._explainability_adapter = (
                ExplainabilityAdapter()
            )

            print(
                "Explainability adapter initialized."
            )

            return self._explainability_adapter

        except Exception as error:

            raise PredictionError(
                "Unable to initialize "
                f"Grad-CAM explainability.\n{error}"
            )

    # =====================================================
    # PREDICTION
    # =====================================================

    def predict(
        self,
        image_path: str,
        explain: bool = False
    ):
        """
        Perform maize disease prediction.

        Parameters
        ----------
        image_path : str
            Path to the maize leaf image.

        explain : bool
            False:
                Fast prediction only.

            True:
                Prediction + Grad-CAM explanation.

        Returns
        -------
        dict
            Prediction result.

        Examples
        --------
        Fast prediction:

            predictor.predict(
                "test_images/sample.jpg"
            )

        Prediction with explanation:

            predictor.predict(
                "test_images/sample.jpg",
                explain=True
            )
        """

        timer = Timer()

        try:

            # =================================================
            # IMAGE PREPROCESSING
            # =================================================

            tensor = ImagePreprocessor.preprocess(
                image_path
            )

            # =================================================
            # MODEL PREDICTION
            # =================================================

            probabilities = self.model.predict(
                tensor,
                verbose=(
                    0
                    if not ENABLE_VERBOSE
                    else 1
                )
            )

            # =================================================
            # BEST PREDICTION
            # =================================================

            best = get_best_prediction(
                probabilities
            )

            # =================================================
            # TOP PREDICTIONS
            # =================================================

            top = get_top_predictions(
                probabilities
            )

            # =================================================
            # PREDICTION TIME
            # =================================================

            prediction_time = timer.stop()

            best["prediction_time"] = (
                prediction_time
            )

            best["model"] = (
                MODEL_ARCHITECTURE
            )

            best["version"] = (
                MODEL_VERSION
            )

            best["status"] = (
                "High Confidence"
                if best["confidence"]
                >= CONFIDENCE_THRESHOLD
                else "Low Confidence"
            )

            # =================================================
            # BASE RESULT
            # =================================================

            result = {
                "prediction": best,
                "top_predictions": top
            }

            # =================================================
            # OPTIONAL GRAD-CAM
            # =================================================

            if explain:

                adapter = (
                    self._get_explainability_adapter()
                )

                explanation = (
                    adapter.explain(
                        image_path
                    )
                )

                # -------------------------------------------------
                # Verify prediction consistency
                # -------------------------------------------------

                if (
                    explanation["class_id"]
                    != best["class_id"]
                ):

                    raise PredictionError(
                        "Grad-CAM class does not "
                        "match prediction class."
                    )

                # -------------------------------------------------
                # Add explanation to result
                # -------------------------------------------------

                result["explainability"] = {

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
                    ]
                }

            # =================================================
            # LOG PREDICTION
            # =================================================

            log_prediction(

                image_name=Path(
                    image_path
                ).name,

                disease=best[
                    "display_name"
                ],

                confidence=best[
                    "confidence"
                ],

                prediction_time=(
                    prediction_time
                )
            )

            # =================================================
            # RETURN RESULT
            # =================================================

            return result

        except Exception as error:

            log_error(

                image_name=Path(
                    image_path
                ).name,

                error=str(error)
            )

            raise
