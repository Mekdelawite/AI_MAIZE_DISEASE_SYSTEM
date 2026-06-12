"""
=========================================================
Custom Exceptions
=========================================================

This module defines all custom exceptions used by the
AI inference engine.

Author : Nigusu Tgabu & Rediet Tsega and Samuel Admasu
Project: AI Maize Disease Detection System
=========================================================
"""


class InferenceError(Exception):
    """
    Base exception for all inference-related errors.
    """
    pass


class ImageNotFoundError(InferenceError):
    """
    Raised when the specified image file cannot be found.
    """
    pass


class InvalidImageError(InferenceError):
    """
    Raised when the file is not a valid image.
    """
    pass


class UnsupportedImageFormatError(InferenceError):
    """
    Raised when the image extension is not supported.
    """
    pass


class ImageTooLargeError(InferenceError):
    """
    Raised when the uploaded image exceeds the size limit.
    """
    pass


class ModelNotLoadedError(InferenceError):
    """
    Raised when the AI model cannot be loaded.
    """
    pass


class PredictionError(InferenceError):
    """
    Raised when prediction fails.
    """
    pass


class ConfigurationError(InferenceError):
    """
    Raised when configuration values are invalid.
    """
    pass