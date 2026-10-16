"""
=========================================================
Prediction Logger
=========================================================

Logs prediction events and errors.

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

import logging
from pathlib import Path

from config import LOG_FILE


# ---------------------------------------------------------
# Create logger
# ---------------------------------------------------------

LOGGER = logging.getLogger("MaizeAI")

LOGGER.setLevel(logging.INFO)

LOGGER.propagate = False


# Prevent duplicate handlers
if not LOGGER.handlers:

    formatter = logging.Formatter(

        "%(asctime)s | %(levelname)s | %(message)s",

        "%Y-%m-%d %H:%M:%S"

    )

    file_handler = logging.FileHandler(LOG_FILE)

    file_handler.setFormatter(formatter)

    LOGGER.addHandler(file_handler)


# ---------------------------------------------------------
# Success Log
# ---------------------------------------------------------

def log_prediction(

        image_name: str,

        disease: str,

        confidence: float,

        prediction_time: float

):

    LOGGER.info(

        f"SUCCESS | "

        f"Image={image_name} | "

        f"Disease={disease} | "

        f"Confidence={confidence:.2f}% | "

        f"Time={prediction_time:.4f}s"

    )


# ---------------------------------------------------------
# Error Log
# ---------------------------------------------------------

def log_error(

        image_name: str,

        error: str

):

    LOGGER.error(

        f"FAILED | "

        f"Image={image_name} | "

        f"Error={error}"

    )