from datetime import timedelta

from flask_jwt_extended import create_access_token

from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User


def _create_farmer(database):
    user = User(
        phone_number="0900000999",
        full_name="Calendar Test Farmer",
        role="farmer",
        preferred_language="en",
        is_active=True,
    )
    user.set_password("TestPassword123!")
    database.session.add(user)
    database.session.flush()
    database.session.add(
        FarmerProfile(
            user_id=user.id,
            region="Amhara",
            woreda="Bahir Dar Zuria",
            kebele=None,
        )
    )
    database.session.commit()
    return user


def test_crop_calendar_serializes_optional_kebele(client, database):
    user = _create_farmer(database)
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": "farmer"},
    )

    response = client.get(
        "/api/crop-calendar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["location"]["kebele"] is None
    assert payload["data"]["calendar"]


def test_crop_calendar_rejects_expired_jwt(client, database):
    user = _create_farmer(database)
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": "farmer"},
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/api/crop-calendar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
