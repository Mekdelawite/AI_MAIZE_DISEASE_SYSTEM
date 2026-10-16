"""
=========================================================
Utility Functions
=========================================================

Common utility functions used throughout the
AI inference module.

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

import time
from typing import Dict, List

import numpy as np

from config import TOP_K_PREDICTIONS
from labels import DISEASES


# ---------------------------------------------------------
# Timer
# ---------------------------------------------------------

class Timer:
    """
    Simple timer for measuring prediction time.
    """

    def __init__(self):
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        """
        Returns elapsed time in seconds.
        """
        return round(time.perf_counter() - self.start_time, 4)


# ---------------------------------------------------------
# Confidence Formatting
# ---------------------------------------------------------

def format_confidence(confidence: float) -> float:
    """
    Convert confidence to percentage.
    """

    return round(float(confidence) * 100, 2)


# ---------------------------------------------------------
# Top K Predictions
# ---------------------------------------------------------

def get_top_predictions(probabilities: np.ndarray) -> List[Dict]:
    """
    Return top K predictions.

    Parameters
    ----------
    probabilities : ndarray
        Raw model output.

    Returns
    -------
    List[Dict]
    """

    probabilities = probabilities.flatten()

    indices = np.argsort(probabilities)[::-1][:TOP_K_PREDICTIONS]

    results = []

    for index in indices:

        disease = DISEASES[index]

        results.append({

            "class_id": disease.id,

            "class_name": disease.class_name,

            "display_name": disease.display_name,

            "scientific_name": disease.scientific_name,

            "confidence": format_confidence(
                probabilities[index]
            )
        })

    return results


# ---------------------------------------------------------
# Final Prediction
# ---------------------------------------------------------

def get_best_prediction(probabilities: np.ndarray) -> Dict:
    """
    Return the highest confidence prediction.
    """

    top_prediction = get_top_predictions(probabilities)[0]

    return top_prediction