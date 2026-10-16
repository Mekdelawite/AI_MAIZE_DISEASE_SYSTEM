from backend.app.models import User


def test_database_persistence(database):
    user = User(
        phone_number="0900000001",
        full_name="Test Farmer",
        password_hash="test-hash",
        role="farmer",
        preferred_language="en",
    )
    database.session.add(user)
    database.session.commit()

    saved = User.query.filter_by(phone_number="0900000001").first()
    assert saved is not None
    assert saved.id is not None
    assert saved.role == "farmer"
    assert saved.preferred_language == "en"


def test_database_starts_clean(database):
    assert User.query.count() == 0
