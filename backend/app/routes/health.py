"""
=========================================================
Health API Routes
=========================================================
"""

from flask import Blueprint, jsonify


health_bp = Blueprint(
    "health",
    __name__,
)


@health_bp.get("/health")
def health_check():
    """
    Check whether the backend is running.
    """

    return jsonify(
        {
            "service": "backend",
            "status": "healthy",
        }
    )