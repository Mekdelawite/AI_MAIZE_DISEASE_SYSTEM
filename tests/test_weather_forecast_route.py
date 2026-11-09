from flask_jwt_extended import create_access_token
from datetime import datetime, timezone
from types import SimpleNamespace
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


def test_weather_provider_timeout_is_retried_then_temporarily_suppressed(monkeypatch):
    calls = []

    def timeout(*args, **kwargs):
        calls.append(kwargs)
        raise requests.Timeout("provider timed out")

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", timeout)
    monkeypatch.setattr(weather_service.time, "sleep", lambda _seconds: None)

    with pytest.raises(requests.RequestException):
        WeatherService._get_json("test-provider", "https://weather.invalid", {"lat": 1}, cache_seconds=10)
    with pytest.raises(requests.RequestException, match="temporarily unavailable"):
        WeatherService._get_json("test-provider", "https://weather.invalid", {"lat": 2}, cache_seconds=10)

    assert len(calls) == 3
    assert all(call["timeout"] == (4, 8) for call in calls)


@pytest.mark.parametrize("timeout_error", [requests.ConnectTimeout, requests.ReadTimeout])
def test_weather_connect_and_read_timeouts_use_bounded_exponential_retries(
    monkeypatch,
    timeout_error,
):
    calls = []
    delays = []

    def timeout(*args, **kwargs):
        calls.append(kwargs)
        raise timeout_error("timed out")

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", timeout)
    monkeypatch.setattr(weather_service.time, "sleep", delays.append)

    with pytest.raises(requests.RequestException, match=timeout_error.__name__):
        WeatherService._get_json(
            "timeout-provider",
            "https://weather.invalid",
            {"lat": 1},
            cache_seconds=10,
        )

    assert len(calls) == 3
    assert delays == [0.25, 0.5]
    assert all(call["timeout"] == (4, 8) for call in calls)


def test_weather_request_retries_then_caches_success(monkeypatch):
    calls = []
    response = SimpleNamespace(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: {"daily": {"time": ["2026-11-04"]}},
    )

    def request(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise requests.ReadTimeout("temporary read timeout")
        return response

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", request)
    monkeypatch.setattr(weather_service.time, "sleep", lambda _seconds: None)

    first = WeatherService._get_json(
        "retry-provider", "https://weather.invalid", {}, cache_seconds=30
    )
    second = WeatherService._get_json(
        "retry-provider", "https://weather.invalid", {}, cache_seconds=30
    )

    assert first == second == {"daily": {"time": ["2026-11-04"]}}
    assert len(calls) == 2


def test_weather_server_error_is_retried_but_client_error_is_not(monkeypatch):
    class FakeResponse:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self.payload = payload

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"HTTP {self.status_code}")
                error.response = self
                raise error

        def json(self):
            return self.payload

    calls = []

    def request(*args, **kwargs):
        calls.append(kwargs)
        return FakeResponse(503) if len(calls) == 1 else FakeResponse(200, {"ok": True})

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", request)
    monkeypatch.setattr(weather_service.time, "sleep", lambda _seconds: None)

    assert WeatherService._get_json(
        "server-error-provider", "https://weather.invalid", {}, cache_seconds=10
    ) == {"ok": True}
    assert len(calls) == 2

    calls.clear()
    monkeypatch.setattr(
        weather_service.requests,
        "get",
        lambda *args, **kwargs: (calls.append(kwargs) or FakeResponse(400)),
    )
    with pytest.raises(requests.HTTPError):
        WeatherService._get_json(
            "client-error-provider", "https://weather.invalid", {}, cache_seconds=10
        )
    assert len(calls) == 1


def test_invalid_json_is_retried_and_never_cached(monkeypatch):
    calls = []

    def invalid_json():
        raise ValueError("invalid JSON")

    def request(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=invalid_json,
        )

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", request)
    monkeypatch.setattr(weather_service.time, "sleep", lambda _seconds: None)

    with pytest.raises(requests.RequestException, match="invalid weather response"):
        WeatherService._get_json(
            "invalid-json-provider",
            "https://weather.invalid",
            {},
            cache_seconds=10,
        )
    assert len(calls) == 3
    assert not weather_service._RESPONSE_CACHE


def test_forecast_cache_reuses_nearby_open_meteo_coordinates(monkeypatch):
    calls = []
    response = SimpleNamespace(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: {
            "latitude": 8.5,
            "longitude": 37.0,
            "timezone": "Africa/Addis_Ababa",
            "current": {"time": "2026-11-04T12:00"},
            "daily": {
                "time": ["2026-11-04"],
                "weather_code": [2],
                "temperature_2m_max": [24.0],
                "temperature_2m_min": [13.0],
                "precipitation_sum": [1.2],
                "precipitation_probability_max": [40],
                "wind_speed_10m_max": [8.0],
                "et0_fao_evapotranspiration": [3.1],
            },
        },
    )

    def request(*args, **kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", request)

    first = WeatherService.get_forecast_by_coordinates(8.501, 37.001)
    second = WeatherService.get_forecast_by_coordinates(8.504, 37.004)

    assert first == second
    assert first["days"][0]["precipitation_mm"] == 1.2
    assert first["days"][0]["et0_mm"] == 3.1
    assert len(calls) == 1


def test_invalid_forecast_payload_is_not_cached(monkeypatch):
    calls = []
    response = SimpleNamespace(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: {"daily": {"time": []}},
    )

    def request(*args, **kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setattr(weather_service, "_RESPONSE_CACHE", {})
    monkeypatch.setattr(weather_service, "_UNAVAILABLE_UNTIL", {})
    monkeypatch.setattr(weather_service.requests, "get", request)
    monkeypatch.setattr(weather_service.time, "sleep", lambda _seconds: None)

    with pytest.raises(requests.RequestException, match="invalid weather response"):
        WeatherService._get_json(
            "invalid-provider",
            "https://weather.invalid",
            {},
            cache_seconds=30,
            response_validator=WeatherService._validate_forecast_payload,
        )

    assert not weather_service._RESPONSE_CACHE
    assert len(calls) == 3
