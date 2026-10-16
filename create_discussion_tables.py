"""
=========================================================
Create Discussion Board Tables
=========================================================

One-time database setup for the Discussion &
Agricultural Communication System.

Creates only missing tables.
Does not delete or modify existing application data.
=========================================================
"""

from backend.app.main import create_app
from backend.app.extensions import db

# Import models so SQLAlchemy registers their tables.
from backend.app.models import (
    DiscussionPost,
    DiscussionReply,
)


app = create_app()


with app.app_context():
    print("=" * 60)
    print("CREATING DISCUSSION BOARD TABLES")
    print("=" * 60)

    db.create_all()

    print()
    print("Discussion Board tables are ready.")
    print()
    print("Expected tables:")
    print("  - discussion_posts")
    print("  - discussion_replies")
    print()
    print("DONE")