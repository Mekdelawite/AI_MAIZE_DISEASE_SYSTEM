"""
=========================================================
AI Maize Disease Detection System
Flask Backend Application
=========================================================
"""

from __future__ import annotations

from flask_jwt_extended import JWTManager
from flask import Flask, jsonify
from flask_cors import CORS

from backend.app.config import get_config
from backend.app.extensions import (
    db,
    jwt,
)

# ---------------------------------------------------------
# Database models
# ---------------------------------------------------------
# Importing the models registers them with SQLAlchemy.
from backend.app.models import (
    User,
    DiagnosisRecord,
    AdvisoryRecord,
    ExtensionAgent,
    ExtensionComment,
    FarmerProfile,
    SMSRecord,
    OfflineSyncRecord,
)

# ---------------------------------------------------------
# API routes
# ---------------------------------------------------------

from backend.app.routes.health import health_bp
from backend.app.routes.diagnosis import diagnosis_bp
from backend.app.routes.advisory import advisory_bp
from backend.app.routes.complete_diagnosis import (
    complete_diagnosis_bp,
)
from backend.app.routes.auth import auth_bp
from backend.app.routes.profile import profile_bp
from backend.app.routes.weather import weather_bp
from backend.app.routes.extension import extension_bp
from backend.app.routes.admin import admin_bp
from backend.app.routes.discussion import discussion_bp
from backend.app.routes.sms import sms_bp
from backend.app.routes.outbreak_alert import outbreak_alert_bp
from backend.app.routes.report import report_bp
from backend.app.routes.crop_calendar import crop_calendar_bp
from backend.app.routes.sync import sync_bp
from backend.app.routes.sync_batch import sync_batch_bp
from backend.app.routes.regional_alert import regional_alert_bp
def create_app(
    environment: str | None = None,
) -> Flask:
    """
    Application factory.
    """

    # =====================================================
    # CREATE FLASK APPLICATION
    # =====================================================

    app = Flask(__name__)

    # =====================================================
    # CONFIGURATION
    # =====================================================

    config_class = get_config(environment)

    app.config.from_object(config_class)

    # =====================================================
    # CORS
    # =====================================================

    CORS(app)

    # =====================================================
    # DATABASE
    # =====================================================

    db.init_app(app)
    
    jwt.init_app(app)
    # =====================================================
    # DIRECTORIES
    # =====================================================

    upload_dir = app.config["UPLOAD_DIR"]

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =====================================================
    # JSON
    # =====================================================

    app.config["JSON_SORT_KEYS"] = False

    # =====================================================
    # BLUEPRINTS
    # =====================================================

    app.register_blueprint(
        health_bp
    )

    app.register_blueprint(
        diagnosis_bp
    )

    app.register_blueprint(
        advisory_bp
    )

    app.register_blueprint(
        complete_diagnosis_bp
    )
    app.register_blueprint(
    auth_bp
    )
    
    app.register_blueprint(profile_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(extension_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(sms_bp)
    app.register_blueprint(outbreak_alert_bp)
    app.register_blueprint(discussion_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(crop_calendar_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(sync_batch_bp)
    app.register_blueprint(regional_alert_bp)

    # =====================================================
    # ROOT ENDPOINT
    # =====================================================

    @app.get("/")
    def root():

        return jsonify(
            {
                "service": (
                    "AI Maize Disease "
                    "Detection System"
                ),
                "backend": "Flask",
                "status": "running",
                "environment": app.config["ENV"],
                "version": "1.0.0",
            }
        )

    return app


# =========================================================
# APPLICATION INSTANCE
# =========================================================

app = create_app()


# =========================================================
# DEVELOPMENT SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
