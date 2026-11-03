from flask_jwt_extended import create_access_token
from datetime import datetime, timezone
import requests
import pytest

from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User
from backend.app.services import weather_service
from backend.app.services.weather_service import WeatherService


def _farmer_with_coordinates(database):
    user = User(
        phone_number="0900000888",
        full_name="Forecast Test Farmer",
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
            latitude=11.6,
            longitude=37.4,
        )
    )
    database.session.commit()
    return user


def test_farmer_forecast_uses_authenticated_saved_coordinates(
    client, database, monkeypatch
):
    user = _farmer_with_coordinates(database)
    calls = []

    def forecast_lookup(**kwargs):
        calls.append(kwargs)
        return {
            "provider": "Open-Meteo",
            "provider_timestamp": "2026-10-31T09:00",
            "timezone": "Africa/Addis_Ababa",
            "timezone_abbreviation": "EAT",
            "days": [{"date": "2026-10-31", "precipitation_mm": 2.4}],
        }

    monkeypatch.setattr(
        WeatherService,
        "get_forecast_by_coordinates",
        forecast_lookup,
    )
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": "farmer"},
    )

    response = client.get(
        "/api/weather/farmer/forecast",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert response.get_json()["data"]["farmer_location"]["region"] == "Amhara"
    assert calls == [{"latitude": 11.6, "longitude": 37.4}]


def test_farmer_forecast_requires_authentication(client):
    response = client.get("/api/weather/farmer/forecast")

    assert response.status_code == 401


def test_farmer_forecast_requires_saved_coordinates(client, database):
    user = User(
        phone_number="0900000777",
        full_name="No Coordinates Farmer",
        role="farmer",
        preferred_language="en",
        is_active=True,
    )
    user.set_password("TestPassword123!")
    database.session.add(user)
    database.session.flush()
    database.session.add(
        FarmerProfile(user_id=user.id, region="Amhara", woreda="Test Woreda")
    )
    database.session.commit()
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": "farmer"},
    )

    response = client.get(
        "/api/weather/farmer/forecast",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "LOCATION_NOT_CONFIGURED"


def test_current_weather_keeps_timestamp_and_rainfall_window_when_available():
    timestamp = 1_798_768_800

    weather = WeatherService._format_weather_response(
        {
            "dt": timestamp,
            "rain": {"3h": 4.2},
        }
    )

    assert weather["timestamp"] == datetime.fromtimestamp(
        timestamp, tz=timezone.utc
    ).isoformat()
    assert weather["rainfall_mm"] == 4.2
    assert weather["rainfall_period_hours"] == 3
    without_rain = WeatherService._format_weather_response({})
    assert "rainfall_mm" not in without_rain


def test_weather_provider_timeout_is_retried_once_then_temporarily_suppressed(monkeypatch):
    calls = []

    def timeout(*args, **kwargs):
        calls.append(kwargs)
        raise requests.Timeout("provider timed out")

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", timeout)

    with pytest.raises(requests.RequestException):
        WeatherService._get_json("test-provider", "https://weather.invalid", {"lat": 1}, cache_seconds=10)
    with pytest.raises(requests.RequestException, match="temporarily unavailable"):
        WeatherService._get_json("test-provider", "https://weather.invalid", {"lat": 2}, cache_seconds=10)

    assert len(calls) == 2
    assert all(call["timeout"] == (2, 3) for call in calls)
