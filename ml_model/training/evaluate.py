import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns

from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from sklearn.metrics import (
    confusion_matrix,
    classification_report
)

# ======================
# Configuration
# ======================

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 16

TEST_DIR = "../dataset/test"

# ======================
# Load Model
# ======================

model = load_model("../models/best_model.h5")

# ======================
# Test Generator
# ======================

test_datagen = ImageDataGenerator(
    preprocessing_function=tf.keras.applications.mobilenet_v2.preprocess_input
)

test_generator = test_datagen.flow_from_directory(
    TEST_DIR,
    target_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=False
)

# ======================
# Predictions
# ======================

predictions = model.predict(test_generator)

y_pred = np.argmax(predictions, axis=1)

y_true = test_generator.classes

class_names = list(test_generator.class_indices.keys())

# ======================
# Classification Report
# ======================

print("\nClassification Report:\n")

report = classification_report(
    y_true,
    y_pred,
    target_names=class_names
)

print(report)

# ======================
# Confusion Matrix
# ======================

cm = confusion_matrix(y_true, y_pred)

plt.figure(figsize=(8,6))

sns.heatmap(
    cm,
    annot=True,
    fmt='d',
    cmap='Blues',
    xticklabels=class_names,
    yticklabels=class_names
)

plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix")

os.makedirs("../reports", exist_ok=True)

plt.savefig("../reports/confusion_matrix.png")
plt.close()

print("\nConfusion matrix saved.")