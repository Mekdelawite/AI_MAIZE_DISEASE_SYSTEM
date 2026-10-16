"""
=========================================================
Grad-CAM Layer Inspector
=========================================================

Inspects the trained model and identifies convolutional
layers that can be used for Grad-CAM.

Project: AI Maize Disease Detection System
=========================================================
"""

from pathlib import Path

import tensorflow as tf
from tensorflow.keras.models import load_model


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "ml_model"
    / "models"
    / "best_model.h5"
)


# ---------------------------------------------------------
# Load model
# ---------------------------------------------------------

print()
print("=" * 70)
print("GRAD-CAM MODEL INSPECTOR")
print("=" * 70)

print()
print(f"Model path:")
print(MODEL_PATH)

print()

if not MODEL_PATH.exists():

    print("ERROR: Model file was not found.")

    raise SystemExit(1)


print("Loading model...")

model = load_model(MODEL_PATH)

print("Model loaded successfully.")
print()


# ---------------------------------------------------------
# Basic model information
# ---------------------------------------------------------

print("=" * 70)
print("MODEL INFORMATION")
print("=" * 70)

print()

print("Model input shape :", model.input_shape)

print("Model output shape:", model.output_shape)

print()

print("Total layers      :", len(model.layers))

print()


# ---------------------------------------------------------
# All layers
# ---------------------------------------------------------

print("=" * 70)
print("ALL MODEL LAYERS")
print("=" * 70)

print()

for index, layer in enumerate(model.layers):

    print(
        f"{index:3d} | "
        f"{layer.name:35s} | "
        f"{layer.__class__.__name__}"
    )

print()


# ---------------------------------------------------------
# Convolutional layers
# ---------------------------------------------------------

print("=" * 70)
print("CONVOLUTIONAL LAYERS")
print("=" * 70)

print()

conv_layers = []

for index, layer in enumerate(model.layers):

    layer_type = layer.__class__.__name__

    if isinstance(
        layer,
        tf.keras.layers.Conv2D
    ):

        conv_layers.append(layer)

        print(
            f"Index       : {index}"
        )

        print(
            f"Name        : {layer.name}"
        )

        print(
            f"Type        : {layer_type}"
        )

        print(
            f"Output shape: {layer.output.shape}"
        )

        print("-" * 70)


# ---------------------------------------------------------
# Final convolutional layer
# ---------------------------------------------------------

print()

print("=" * 70)
print("RESULT")
print("=" * 70)

print()

if not conv_layers:

    print(
        "ERROR: No Conv2D layers were found."
    )

    raise SystemExit(1)


last_conv_layer = conv_layers[-1]

print(
    "Last Conv2D layer:"
)

print()

print(
    f"Name        : {last_conv_layer.name}"
)

print(
    f"Output shape: {last_conv_layer.output.shape}"
)

print()

print(
    "This layer is a candidate for Grad-CAM."
)

print()