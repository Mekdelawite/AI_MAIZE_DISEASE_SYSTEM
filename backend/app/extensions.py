"""
=========================================================
Flask Extensions
=========================================================

Centralized Flask extensions for the AI Maize Disease
Detection System.

Currently:
    - Flask-SQLAlchemy
    - Flask-JWT-Extended

Keeping extensions separate prevents circular imports
between the application factory and database models.
=========================================================
"""

from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


# =========================================================
# DATABASE
# =========================================================

db = SQLAlchemy()
migrate = Migrate()


# =========================================================
# JWT
# =========================================================

jwt = JWTManager()