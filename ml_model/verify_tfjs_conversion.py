"""Compare the source Keras model and TF.js Layers model on labeled test images.

Run this in the existing Ubuntu WSL Keras 3.14.1 environment. The script uses
the inference pipeline's RGB conversion, 224x224 Pillow resize, and
MobileNetV2 preprocess_input exactly once, then sends the same tensors to both
models. Node.js and the frontend's @tensorflow/tfjs package run the converted
model's forward pass.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import tensorflow as tf
from PIL import Image


PROJECT = Path("/mnt/d/Projects/AI_MAIZE_DISEASE_SYSTEM")
SOURCE_MODEL = PROJECT / "ml_model/models/best_model.h5"
TFJS_MODEL = PROJECT / "frontend/public/models/maize/model.json"
TEST_DIR = PROJECT / "ml_model/dataset/test"
CLASS_DIRS = ["Blight", "Common_Rust", "Gray_Leaf_Spot", "Healthy"]
CLASS_NAMES = ["Northern Leaf Blight", "Common Rust", "Gray Leaf Spot", "Healthy"]
NODE_SCRIPT = PROJECT / "frontend/scripts/compare_tfjs_predictions.mjs"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-per-class", type=int, default=3)
    parser.add_argument("--report", type=Path, default=PROJECT / "ml_model/reports/tfjs_prediction_parity.json")
    args = parser.parse_args()

    if not SOURCE_MODEL.is_file() or not TFJS_MODEL.is_file():
        raise FileNotFoundError("The source H5 model or converted TF.js model.json is missing.")

    model = tf.keras.models.load_model(SOURCE_MODEL, compile=False)
    if model.input_shape != (None, 224, 224, 3) or model.output_shape != (None, 4):
        raise ValueError(f"Unexpected source model shape: {model.input_shape} -> {model.output_shape}")

    samples: list[dict] = []
    tensors: list[np.ndarray] = []
    for class_id, class_dir in enumerate(CLASS_DIRS):
        paths = sorted(
            path for path in (TEST_DIR / class_dir).rglob("*")
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )[: args.samples_per_class]
        if not paths:
            raise RuntimeError(f"No labeled test images found in {TEST_DIR / class_dir}")
        for path in paths:
            with Image.open(path) as image:
                resized = image.convert("RGB").resize((224, 224))
                pixels = np.asarray(resized, dtype=np.float32)
            tensor = tf.keras.applications.mobilenet_v2.preprocess_input(pixels)
            tensors.append(tensor)
            samples.append({
                "file": str(path.relative_to(TEST_DIR)),
                "label_id": class_id,
                "label": CLASS_NAMES[class_id],
            })

    inputs = np.stack(tensors).astype(np.float32)
    keras_probabilities = model.predict(inputs, verbose=0).astype(np.float64)
    payload = [
        {"input": tensor.reshape(-1).tolist()}
        for tensor in inputs
    ]

    node_exe = os.environ.get("NODE_EXE", "/mnt/c/Program Files/nodejs/node.exe")
    node_script_win = subprocess.check_output(["wslpath", "-w", str(NODE_SCRIPT)], text=True).strip()
    model_json_win = subprocess.check_output(["wslpath", "-w", str(TFJS_MODEL)], text=True).strip()
    process = subprocess.run(
        [node_exe, node_script_win, model_json_win],
        input=json.dumps(payload, separators=(",", ":")),
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise RuntimeError(f"TensorFlow.js comparison process failed:\n{process.stdout}\n{process.stderr}")
    tfjs_probabilities = np.asarray(json.loads(process.stdout), dtype=np.float64)
    if tfjs_probabilities.shape != keras_probabilities.shape:
        raise ValueError(f"Output shape mismatch: Keras={keras_probabilities.shape}, TF.js={tfjs_probabilities.shape}")

    differences = np.abs(keras_probabilities - tfjs_probabilities)
    keras_classes = keras_probabilities.argmax(axis=1)
    tfjs_classes = tfjs_probabilities.argmax(axis=1)
    records = []
    for index, sample in enumerate(samples):
        records.append({
            **sample,
            "keras_class": CLASS_NAMES[int(keras_classes[index])],
            "tfjs_class": CLASS_NAMES[int(tfjs_classes[index])],
            "class_matches": bool(keras_classes[index] == tfjs_classes[index]),
            "max_abs_probability_difference": float(differences[index].max()),
            "keras_probabilities": keras_probabilities[index].tolist(),
            "tfjs_probabilities": tfjs_probabilities[index].tolist(),
        })

    report = {
        "source_model": str(SOURCE_MODEL),
        "keras_version": tf.keras.__version__ if hasattr(tf.keras, "__version__") else "see runtime metadata",
        "tensorflow_version": tf.__version__,
        "tfjs_converter_version": "4.22.0",
        "input_preprocessing": "Pillow RGB resize 224x224; MobileNetV2 preprocess_input once",
        "class_order": CLASS_NAMES,
        "sample_count": len(records),
        "predicted_class_matches": int(sum(record["class_matches"] for record in records)),
        "mean_absolute_probability_difference": float(differences.mean()),
        "max_absolute_probability_difference": float(differences.max()),
        "samples": records,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))
    for record in records:
        print(
            f"{record['file']}: true={record['label']}; Keras={record['keras_class']}; "
            f"TF.js={record['tfjs_class']}; max_abs_diff={record['max_abs_probability_difference']:.8f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
