from backend.app.models import User
from backend.app.services.registration_otp_service import RegistrationOTPService
from backend.app.services.sms_service import SMSService


def test_register_login_and_me(client, database, monkeypatch):
    monkeypatch.setattr(RegistrationOTPService, "_generate_otp", staticmethod(lambda: "123456"))
    monkeypatch.setattr(SMSService, "send_sms", staticmethod(lambda *args, **kwargs: {"success": True}))

    otp_response = client.post("/api/auth/registration-otp/request", json={
        "phone_number": "0900000010",
    })
    assert otp_response.status_code == 200

    verify_response = client.post("/api/auth/registration-otp/verify", json={
        "phone_number": "+251900000010",
        "otp": "123456",
    })
    assert verify_response.status_code == 200

    register_response = client.post("/api/auth/register", json={
        "phone_number": "0900000010",
        "full_name": "Test Farmer",
        "password": "TestPassword123!",
        "role": "farmer",
        "preferred_language": "en",
        "region": "Amhara",
        "woreda": "Bahir Dar Zuria",
    })

    assert register_response.status_code in (200, 201)
    register_data = register_response.get_json()
    assert register_data["success"] is True

    user = User.query.filter_by(phone_number="+251900000010").first()
    assert user is not None
    assert user.password_hash != "TestPassword123!"
    assert user.check_password("TestPassword123!") is True

    login_response = client.post("/api/auth/login", json={
        "phone_number": "0900000010",
        "password": "TestPassword123!",
    })

    assert login_response.status_code == 200
    login_data = login_response.get_json()
    assert login_data["success"] is True
    assert "data" in login_data
    assert "access_token" in login_data["data"]

    token = login_data["data"]["access_token"]
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    me_data = me_response.get_json()
    assert me_data["success"] is True

    duplicate_response = client.post("/api/auth/registration-otp/request", json={
        "phone_number": "0900000010",
    })
    assert duplicate_response.status_code == 409


def test_auth_me_requires_token(client, database):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
