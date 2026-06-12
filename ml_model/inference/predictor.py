import time
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model # type: ignore

from preprocess import preprocess_image
from labels import CLASS_NAMES


MODEL_PATH = "../models/best_model.h5"


class DiseasePredictor:

    def __init__(self):

        print("Loading AI model...")

        self.model = load_model(MODEL_PATH)

        print("Model loaded successfully.")

    def predict(self, image_path):

        start = time.time()

        image = preprocess_image(image_path)

        prediction = self.model.predict(image, verbose=0)

        predicted_index = np.argmax(prediction)

        confidence = float(np.max(prediction)) * 100

        prediction_time = round(time.time() - start, 3)

        return {
            "disease": CLASS_NAMES[predicted_index],
            "confidence": round(confidence, 2),
            "prediction_time": prediction_time
        }