"""
=========================================================
User Model
=========================================================

Database model for system users.

Supported roles:
    - farmer
    - extension_agent
    - admin
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone

import bcrypt

from backend.app.extensions import db


class User(db.Model):
    """
    Application user.

    Stores authentication and basic profile information.
    """

    __tablename__ = "users"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # =====================================================
    # ACCOUNT INFORMATION
    # =====================================================

    phone_number = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name = db.Column(
        db.String(150),
        nullable=False,
    )

    role = db.Column(
        db.String(30),
        nullable=False,
        default="farmer",
        index=True,
    )

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    # =====================================================
    # LANGUAGE
    # =====================================================

    preferred_language = db.Column(
        db.String(5),
        nullable=False,
        default="en",
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )
    # =====================================================
    # PASSWORD METHODS
    # =====================================================

    def set_password(
        self,
        password: str,
    ) -> None:
        """
        Hash and store a password.
        """

        password_bytes = password.encode("utf-8")

        self.password_hash = (
            bcrypt.hashpw(
                password_bytes,
                bcrypt.gensalt(),
            )
            .decode("utf-8")
        )

    def check_password(
        self,
        password: str,
    ) -> bool:
        """
        Verify a password against the stored hash.
        """

        if not self.password_hash:
            return False

        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} "
            f"phone={self.phone_number!r} "
            f"role={self.role!r}>"
        )