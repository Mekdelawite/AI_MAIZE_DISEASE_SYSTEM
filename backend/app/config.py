"""
=========================================================
Backend Configuration
=========================================================

Central configuration for the AI Maize Disease Detection
System backend.

Project:
    AI Maize Disease Detection System

Backend:
    Flask

=========================================================
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()
# =========================================================
# PROJECT PATHS
# =========================================================

# backend/app/config.py
APP_DIR = Path(__file__).resolve().parent

# D:\Projects\AI_MAIZE_DISEASE_SYSTEM
PROJECT_ROOT = APP_DIR.parent.parent


# =========================================================
# FLASK CONFIGURATION
# =========================================================

class Config:
    """
    Base Flask configuration.
    """

    # -----------------------------------------------------
    # Application
    # -----------------------------------------------------

    APP_NAME = "AI Maize Disease Detection System"

    ENV = os.getenv(
        "FLASK_ENV",
        "development",
    )

    DEBUG = (
        os.getenv(
            "FLASK_DEBUG",
            "0",
        ).lower()
        in {"1", "true", "yes"}
    )

    # -----------------------------------------------------
    # API
    # -----------------------------------------------------

    API_PREFIX = "/api"
        # -----------------------------------------------------
    # JWT Authentication
    # -----------------------------------------------------

    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "dev-change-this-jwt-secret-key",
    )

    JWT_ACCESS_TOKEN_EXPIRES = int(
        os.getenv(
            "JWT_ACCESS_TOKEN_EXPIRES",
        )
    )
        # -----------------------------------------------------
    # Password Recovery
    # -----------------------------------------------------

    PASSWORD_RESET_OTP_LENGTH = int(
        os.getenv(
            "PASSWORD_RESET_OTP_LENGTH",
            "6",
        )
    )

    PASSWORD_RESET_OTP_EXPIRES_MINUTES = int(
        os.getenv(
            "PASSWORD_RESET_OTP_EXPIRES_MINUTES",
            "5",
        )
    )

    PASSWORD_RESET_MAX_ATTEMPTS = int(
        os.getenv(
            "PASSWORD_RESET_MAX_ATTEMPTS",
            "5",
        )
    )

    PASSWORD_RESET_COOLDOWN_SECONDS = int(
        os.getenv(
            "PASSWORD_RESET_COOLDOWN_SECONDS",
            "60",
        )
    )
    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        database_url = make_url(DATABASE_URL)
        # requirements.txt installs Psycopg 3. Keep ordinary PostgreSQL URLs
        # working while selecting its SQLAlchemy dialect explicitly.
        if database_url.drivername in {"postgres", "postgresql"}:
            database_url = database_url.set(drivername="postgresql+psycopg")
        DATABASE_URL = database_url.render_as_string(hide_password=False)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # -----------------------------------------------------
    # Language
    # -----------------------------------------------------

    DEFAULT_LANGUAGE = "en"

    SUPPORTED_LANGUAGES = (
        "en",
        "am",
    )
        # -----------------------------------------------------
    # Weather API
    # -----------------------------------------------------

    WEATHER_API_KEY = os.getenv(
        "WEATHER_API_KEY",
        "",
    )

    WEATHER_API_URL = (
        "https://api.openweathermap.org/data/2.5/weather"
    )
        # -----------------------------------------------------
    # SMS / Africa's Talking
    # -----------------------------------------------------

    AFRICASTALKING_USERNAME = os.getenv(
        "AFRICASTALKING_USERNAME",
        "",
    )

    AFRICASTALKING_API_KEY = os.getenv(
        "AFRICASTALKING_API_KEY",
        "",
    )

    AFRICASTALKING_SENDER_ID = os.getenv(
        "AFRICASTALKING_SENDER_ID",
        "",
    )

    AFRICASTALKING_ENVIRONMENT = os.getenv(
        "AFRICASTALKING_ENVIRONMENT",
        "sandbox",
    )
    # -----------------------------------------------------
    # Upload configuration
    # -----------------------------------------------------

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    ALLOWED_IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    # -----------------------------------------------------
    # AI model paths
    # -----------------------------------------------------

    ML_MODEL_DIR = (
        PROJECT_ROOT
        / "ml_model"
    )

    MODEL_DIR = (
        ML_MODEL_DIR
        / "models"
    )

    MODEL_PATH = (
        MODEL_DIR
        / "best_model.h5"
    )

    # -----------------------------------------------------
    # AI services
    # -----------------------------------------------------

    AI_SERVICE_DIR = (
        ML_MODEL_DIR
        / "ai_service"
    )

    INFERENCE_DIR = (
        ML_MODEL_DIR
        / "inference"
    )

    KNOWLEDGE_BASE_DIR = (
        ML_MODEL_DIR
        / "knowledge_base"
    )

    ADVISOR_DIR = (
        ML_MODEL_DIR
        / "advisor"
    )

    EXPLAINABILITY_DIR = (
        ML_MODEL_DIR
        / "explainability"
    )

    # -----------------------------------------------------
    # Upload directory
    # -----------------------------------------------------

    UPLOAD_DIR = (
        PROJECT_ROOT
        / "uploads"
    )


class DevelopmentConfig(Config):
    """
    Development configuration.
    """

    DEBUG = True


class TestingConfig(Config):
    """
    Testing configuration.
    """

    TESTING = True
    DEBUG = False
    if Config.DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = Config.DATABASE_URL.rsplit("/", 1)[0] + "/ai_maize_disease_test"


class ProductionConfig(Config):
    """
    Production configuration.
    """

    DEBUG = False


# =========================================================
# CONFIGURATION SELECTOR
# =========================================================

CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(
    environment: str | None = None,
) -> type[Config]:
    """
    Return the configuration class for the requested
    environment.
    """

    environment = (
        environment
        or os.getenv(
            "FLASK_ENV",
            "development",
        )
    ).lower()

    return CONFIG_MAP.get(
        environment,
        DevelopmentConfig,
    )
