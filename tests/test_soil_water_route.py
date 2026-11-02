from flask_jwt_extended import create_access_token

from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User


def test_soil_water_route_uses_only_authenticated_farmers_profile(client, database, monkeypatch):
    from backend.app.routes import crop_calendar

    farmers = []
    for phone, latitude in (("0900000971", 10.25), ("0900000972", 11.75)):
        user = User(phone_number=phone, full_name="Water test", role="farmer", preferred_language="en", is_active=True)
        user.set_password("TestPassword123!")
        database.session.add(user)
        database.session.flush()
        database.session.add(FarmerProfile(user_id=user.id, region="Amhara", woreda="Test", latitude=latitude, longitude=37.5))
        farmers.append(user)
    database.session.commit()

    requested_coordinates = []
    def historical(latitude, longitude, start_date, end_date):
        requested_coordinates.append((latitude, longitude))
        return {"provider": "Open-Meteo Historical Weather API (reanalysis)", "days": []}
    monkeypatch.setattr(crop_calendar.WeatherService, "get_historical_water_weather", historical)
    monkeypatch.setattr(crop_calendar.WeatherService, "get_forecast_by_coordinates", lambda latitude, longitude: {"provider": "Open-Meteo", "days": []})
    monkeypatch.setattr(crop_calendar.WeatherService, "get_current_weather_by_coordinates", lambda latitude, longitude, units="metric": {"temperature": 24, "humidity": 55, "timestamp": "2026-06-01T12:00:00Z"})

    token = create_access_token(identity=str(farmers[1].id), additional_claims={"role": "farmer"})
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.put("/api/profile", headers=headers, json={
        "planting_date": "2026-06-01", "soil_type": "loam",
        "available_water_capacity_mm_per_m": 140, "crop_growth_stage": "mid_season",
        "irrigation_status": "rainfed",
    })
    assert saved.status_code == 200
    invalid = client.put("/api/profile", headers=headers, json={"available_water_capacity_mm_per_m": 301})
    assert invalid.status_code == 400
    response = client.get("/api/crop-calendar/soil-water", headers=headers)

    assert response.status_code == 200
    assert requested_coordinates == [(11.75, 37.5)]
    assert response.get_json()["data"]["root_zone"] is None
    assert response.get_json()["data"]["advisories"]["stage"]["basis"] == "farmer_confirmed"


def test_soil_water_route_rejects_non_farmer_role(client, database):
    user = User(phone_number="0900000973", full_name="Agent", role="extension_agent", preferred_language="en", is_active=True)
    user.set_password("TestPassword123!")
    database.session.add(user)
    database.session.commit()
    token = create_access_token(identity=str(user.id), additional_claims={"role": "extension_agent"})

    response = client.get("/api/crop-calendar/soil-water", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
