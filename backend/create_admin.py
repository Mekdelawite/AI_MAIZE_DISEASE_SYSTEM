"""
=========================================================
Create Development Admin Account
=========================================================

Creates one administrator account for development/testing.

This script is intentionally separate from the public
registration API.

=========================================================
"""

from __future__ import annotations

import getpass

from backend.app.main import app
from backend.app.extensions import db
from backend.app.models.user import User


def main() -> None:

    print("=" * 60)
    print("AI MAIZE DISEASE SYSTEM")
    print("Development Admin Account Creation")
    print("=" * 60)

    phone_number = input(
        "Admin phone number: "
    ).strip()

    full_name = input(
        "Admin full name: "
    ).strip()

    password = getpass.getpass(
        "Admin password: "
    )

    confirm_password = getpass.getpass(
        "Confirm password: "
    )

    if password != confirm_password:
        print(
            "ERROR: Passwords do not match."
        )
        return

    if len(password) < 8:
        print(
            "ERROR: Password must contain "
            "at least 8 characters."
        )
        return

    with app.app_context():

        existing_user = (
            User.query
            .filter_by(
                phone_number=phone_number
            )
            .first()
        )

        if existing_user is not None:
            print(
                "ERROR: A user with this phone "
                "number already exists."
            )
            return

        admin = User(
            phone_number=phone_number,
            full_name=full_name,
            role="admin",
            preferred_language="en",
            is_active=True,
        )

        admin.set_password(password)

        try:

            db.session.add(admin)
            db.session.commit()

        except Exception as error:

            db.session.rollback()

            print(
                "ERROR: Failed to create admin:"
            )
            print(error)

            return

        print()
        print("=" * 60)
        print("ADMIN CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"ID:    {admin.id}")
        print(f"Name:  {admin.full_name}")
        print(f"Phone: {admin.phone_number}")
        print(f"Role:  {admin.role}")
        print("=" * 60)


if __name__ == "__main__":
    main()