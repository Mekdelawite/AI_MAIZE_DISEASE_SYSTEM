"""
=========================================================
Configuration File
=========================================================

This module stores all configurable values used by the
AI inference system.

Author : Nigusu Tgabu,Rediet Tsega,Samueal Admasu
Project: AI Maize Disease Detection and Advisory System
=========================================================
"""

from pathlib import Path

# -------------------------------------------------------
# Base Directories
# -------------------------------------------------------

# inference/
CURRENT_DIR = Path(__file__).resolve().parent

# ml_model/
ML_MODEL_DIR = CURRENT_DIR.parent

# Project Root
PROJECT_ROOT = ML_MODEL_DIR.parent

# -------------------------------------------------------
# Model Configuration
# -------------------------------------------------------

MODEL_DIR = ML_MODEL_DIR / "models"

MODEL_NAME = "best_model.h5"

MODEL_PATH = MODEL_DIR / MODEL_NAME

# -------------------------------------------------------
# Image Configuration
# -------------------------------------------------------

IMAGE_WIDTH = 224

IMAGE_HEIGHT = 224

IMAGE_SIZE = (IMAGE_WIDTH, IMAGE_HEIGHT)

IMAGE_CHANNELS = 3

# -------------------------------------------------------
# Prediction Configuration
# -------------------------------------------------------

TOP_K_PREDICTIONS = 3

CONFIDENCE_THRESHOLD = 60.0

# -------------------------------------------------------
# Supported Image Formats
# -------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# -------------------------------------------------------
# Maximum Image Size
# -------------------------------------------------------

MAX_IMAGE_SIZE_MB = 10

MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# -------------------------------------------------------
# Logging
# -------------------------------------------------------

LOG_DIR = PROJECT_ROOT / "logs"

LOG_FILE = LOG_DIR / "prediction.log"

# Create log directory automatically

LOG_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------
# Reports Directory
# -------------------------------------------------------

REPORTS_DIR = ML_MODEL_DIR / "reports"

REPORTS_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------
# TensorFlow
# -------------------------------------------------------

ENABLE_VERBOSE = False

# -------------------------------------------------------
# API Information
# -------------------------------------------------------

MODEL_VERSION = "1.0.0"

MODEL_ARCHITECTURE = "MobileNetV2"

PROJECT_NAME = "AI Maize Disease Detection System"
