
"""Focused checks for inference model reuse and mandatory validity gating."""

import importlib
import threading
import types
from pathlib import Path

import numpy as np


def test_diagnosis_services_share_predictor_instance(monkeypatch):
    from ml_model.ai_service.diagnosis_service import DiagnosisService

    class Predictor:
        def predict(self, _image_path):
            return {
                "prediction": {"class_id": 0},
                "top_predictions": [],
            }

    predictor = Predictor()
    monkeypatch.setattr(DiagnosisService, "_shared_predictor", predictor)

    first = DiagnosisService()
    second = DiagnosisService()

    assert first.predictor is predictor
    assert second.predictor is predictor


def test_gradcam_accepts_existing_model_without_loading(monkeypatch):
    """A supplied disease model prevents GradCAM from loading another copy."""
    import tensorflow as tf

    from ml_model.explainability.gradcam import GradCAM

    inputs = tf.keras.Input(shape=(8, 8, 3))
    conv_layer = tf.keras.layers.Conv2D(2, 3, name="test_conv")
    outputs = conv_layer(inputs)
    supplied = tf.keras.Model(inputs=inputs, outputs=outputs)

    def reject_duplicate_load(_self):
        raise AssertionError("Duplicate model load attempted")

    monkeypatch.setattr(GradCAM, "_load_model", reject_duplicate_load)

    instance = GradCAM(model=supplied, target_layer_name="test_conv")

    assert instance.model is supplied


def test_diagnosis_service_explainability_reuses_predictor_model(monkeypatch):
    """The production DiagnosisService path reuses its loaded disease model."""
    import tensorflow as tf

    from ml_model.ai_service.diagnosis_service import DiagnosisService

    # Import the exact GradCAM class used by the production explain module.
    DiagnosisService._configure_python_paths()
    explain_module = importlib.import_module("explain")
    production_gradcam = explain_module.GradCAM

    inputs = tf.keras.Input(shape=(8, 8, 3))
    conv_layer = tf.keras.layers.Conv2D(2, 3, name="Conv_1")
    outputs = conv_layer(inputs)
    supplied_model = tf.keras.Model(inputs=inputs, outputs=outputs)

    class Predictor:
        model = supplied_model

    gradcam_models = []
    real_gradcam_init = production_gradcam.__init__

    def guarded_gradcam_init(self, *args, **kwargs):
        assert kwargs.get("model") is supplied_model
        gradcam_models.append(kwargs["model"])
        real_gradcam_init(self, *args, **kwargs)

    def reject_duplicate_load(self):
        raise AssertionError("Grad-CAM attempted to load a second model")

    monkeypatch.setattr(
        production_gradcam,
        "_load_model",
        reject_duplicate_load,
    )
    monkeypatch.setattr(
        production_gradcam,
        "__init__",
        guarded_gradcam_init,
    )

    service = DiagnosisService(predictor=Predictor())
    explainability_service = service._get_explainability_service()

    assert explainability_service.adapter.service.gradcam.model is supplied_model
    assert gradcam_models == [supplied_model]


def test_concurrent_predictor_creation_loads_once(monkeypatch):
    """Concurrent initialization cannot publish more than one loaded predictor."""
    inference_dir = Path(__file__).resolve().parent
    monkeypatch.syspath_prepend(str(inference_dir))

    from ml_model.inference import predictor as predictor_module

    class FakeModel:
        def predict(self, *_args, **_kwargs):
            return np.zeros((1, 4), dtype=np.float32)

    calls = []

    fake_tf = types.SimpleNamespace(
        keras=types.SimpleNamespace(
            models=types.SimpleNamespace(
                load_model=lambda *_args, **_kwargs: (
                    calls.append(1) or FakeModel()
                )
            )
        )
    )

    monkeypatch.setattr(predictor_module, "tf", fake_tf)
    monkeypatch.setattr(predictor_module, "MODEL_PATH", "model.keras")
    monkeypatch.setattr(
        predictor_module.DiseasePredictor,
        "_instance",
        None,
    )

    results = []
    threads = [
        threading.Thread(
            target=lambda: results.append(
                predictor_module.DiseasePredictor()
            )
        )
        for _ in range(6)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(calls) == 1
    assert len(results) == 6
    assert len({id(result) for result in results}) == 1
