import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# Load model
model = load_model("../models/best_model.h5")

# Class labels
classes = [
    "Blight",
    "Common_Rust",
    "Gray_Leaf_Spot",
    "Healthy"
]

# Image path
img_path = "test_images/Corn_Blight (1134).jpg"

# Load image
img = image.load_img(
    img_path,
    target_size=(224, 224)
)

# Convert to array
img_array = image.img_to_array(img)

# Add batch dimension
img_array = np.expand_dims(img_array, axis=0)

# MobileNetV2 preprocessing
img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)

# Prediction
prediction = model.predict(img_array)

predicted_index = np.argmax(prediction)

disease = classes[predicted_index]

confidence = float(np.max(prediction)) * 100

print("\nPrediction Result")
print("--------------------")
print(f"Disease: {disease}")
print(f"Confidence: {confidence:.2f}%")