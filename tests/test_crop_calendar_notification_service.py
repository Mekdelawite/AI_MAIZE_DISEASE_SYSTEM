from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from flask import Flask

from backend.app.services import crop_calendar_notification_service as notifications
from backend.app.services.crop_calendar_notification_service import CropCalendarNotificationService
from backend.app.services import smart_notification_scheduler as scheduler
from backend.app.services.smart_notification_scheduler import start_smart_notification_scheduler


def _profile(*, user_id=7, planting_date=None, coordinates=True, sms_opt_in=False):
    return SimpleNamespace(
        user_id=user_id, region="Oromia", woreda="Bako", kebele="Kebele 01",
        planting_date=planting_date, crop_growth_stage="development", soil_type="loam",
        available_water_capacity_mm_per_m=120, irrigation_status="rainfed",
        latitude=8.5 if coordinates else None, longitude=37.0 if coordinates else None,
        sms_opt_in=sms_opt_in,
    )


def _user(user_id=7, language="en"):
    return SimpleNamespace(id=user_id, is_active=True, role="farmer", phone_number="0911000000",
                           preferred_language=language)


def _persist_fake(monkeypatch):
    saved = {}

    def create(**kwargs):
        key = (kwargs["user"].id, kwargs["dedupe_key"])
        if key in saved:
            return None
        saved[key] = kwargs
        return SimpleNamespace(id=len(saved))

    monkeypatch.setattr(CropCalendarNotificationService, "_create_notification", create)
    return saved


def test_personalized_reminder_dates_use_saved_planting_date_and_bound_window():
    today = date(2026, 5, 1)
    profile = _profile(planting_date=date(2026, 5, 16))
    reminders = CropCalendarNotificationService.upcoming_activities(profile, today=today)

    assert [(item["activity_key"], item["scheduled_date"]) for item in reminders] == [
        ("land_preparation", "2026-05-02"),
        ("planting", "2026-05-15"),
        ("weed_inspection", "2026-06-10"),
    ]
    assert CropCalendarNotificationService.upcoming_activities(_profile(), today=today) == []
    assert CropCalendarNotificationService.upcoming_activities(
        _profile(planting_date=today - timedelta(days=366)), today=today
    ) == []


def test_due_crop_activity_is_created_once_and_scoped_to_farmer(monkeypatch):
    today = date(2026, 5, 15)
    saved = _persist_fake(monkeypatch)
    profile = _profile(user_id=7, planting_date=today + timedelta(days=1), coordinates=False)
    user = _user(7)

    first = CropCalendarNotificationService.process_farmer(user, profile, today=today)
    second = CropCalendarNotificationService.process_farmer(user, profile, today=today)
    other_farmer = CropCalendarNotificationService.process_farmer(
        _user(8), _profile(user_id=8, planting_date=today + timedelta(days=1), coordinates=False), today=today
    )

    assert first["crop_activity"] == 1
    assert second["crop_activity"] == 0
    assert other_farmer["crop_activity"] == 1
    assert len(saved) == 2
    assert all(key[0] in (7, 8) for key in saved)


def _patch_weather_and_advisories(monkeypatch, advisories):
    monkeypatch.setattr(notifications.WeatherService, "get_forecast_by_coordinates", lambda *_: {
        "provider": "Open-Meteo", "days": [{"date": "2026-05-15", "weather_code": 65, "precipitation_mm": 20}]
    })
    monkeypatch.setattr(notifications.WeatherService, "get_historical_water_weather", lambda *args: {
        "provider": "Open-Meteo Historical Weather API", "days": [{"date": "2026-05-14", "precipitation_mm": 0, "et0_mm": 2}]
    })
    monkeypatch.setattr(notifications.WeatherService, "get_current_weather_by_coordinates", lambda *_: {"temperature": 32})
    monkeypatch.setattr(notifications.CropCalendarService, "get_calendar", lambda *args, **kwargs: {"reference_date": "2026-05-15", "current_stage": {"stage": "planting"}})
    monkeypatch.setattr(notifications.SoilWaterService, "calculate", lambda *args: {
        "historical": {"net_water_balance_mm": -12, "stale": False}, "reliability": "moderate"
    })
    monkeypatch.setattr(notifications.AgriculturalAdvisoryService, "generate", lambda **kwargs: {
        "recommendations": advisories
    })


def test_forecast_and_soil_water_advisories_are_idempotent_and_bilingual(monkeypatch):
    today = date(2026, 5, 15)
    saved = _persist_fake(monkeypatch)
    advisories = [
        {"id": "forecast_heavy_rain", "priority": "medium"},
        {"id": "dryness_risk", "priority": "high"},
        {"id": "crop_stage", "priority": "routine"},
    ]
    _patch_weather_and_advisories(monkeypatch, advisories)
    profile = _profile(planting_date=today - timedelta(days=10), sms_opt_in=False)
    user = _user(language="am")
    sms = []
    monkeypatch.setattr(notifications.SMSService, "send_sms", lambda *args, **kwargs: sms.append(args))

    with Flask(__name__).app_context():
        result = CropCalendarNotificationService.process_farmer(user, profile, today=today)
        repeated = CropCalendarNotificationService.process_farmer(user, profile, today=today)

    assert result["weather_alert"] == 1
    assert result["soil_water_alert"] == 1  # no missing-input prompt for complete profile
    assert repeated["weather_alert"] == repeated["soil_water_alert"] == 0
    assert not sms
    assert all(row["title"][1] and row["message"][1] for row in saved.values())
    assert all(row["title"][0] and row["message"][0] for row in saved.values())


def test_opted_in_sms_failure_does_not_block_in_app_alert(monkeypatch):
    today = date(2026, 5, 15)
    saved = _persist_fake(monkeypatch)
    _patch_weather_and_advisories(monkeypatch, [{"id": "dryness_risk", "priority": "high"}])
    profile = _profile(planting_date=today - timedelta(days=10), sms_opt_in=True)

    def fail_sms(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(notifications.SMSService, "send_sms", fail_sms)
    result = CropCalendarNotificationService.process_farmer(_user(), profile, today=today)

    assert result["soil_water_alert"] == 1
    assert result["sms_attempts"] == 1
    assert any(row["notification_type"] == "soil_water_alert" for row in saved.values())


def test_newly_available_root_zone_estimate_creates_labeled_notification(monkeypatch):
    saved = _persist_fake(monkeypatch)
    _patch_weather_and_advisories(monkeypatch, [])
    monkeypatch.setattr(notifications.SoilWaterService, "calculate", lambda *args: {
        "historical": {"net_water_balance_mm": 0, "stale": False},
        "reliability": "moderate",
        "root_zone": {"available_water_mm": 24.0},
    })
    today = date(2026, 5, 15)
    result = CropCalendarNotificationService.process_farmer(
        _user(language="am"), _profile(planting_date=today - timedelta(days=10)), today=today
    )

    assert result["soil_water_alert"] == 1
    row = next(iter(saved.values()))
    assert "not a sensor measurement" in row["message"][0]
    assert "የሴንሰር መለኪያ አይደለም" in row["message"][1]


def test_missing_live_weather_creates_bilingual_fallback_guidance(monkeypatch):
    saved = _persist_fake(monkeypatch)
    _patch_weather_and_advisories(monkeypatch, [])

    def unavailable(*args, **kwargs):
        raise TimeoutError("weather provider unavailable")

    monkeypatch.setattr(notifications.WeatherService, "get_current_weather_by_coordinates", unavailable)
    today = date(2026, 5, 15)
    user, profile = _user(language="am"), _profile(planting_date=today - timedelta(days=10))

    with Flask(__name__).app_context():
        result = CropCalendarNotificationService.process_farmer(user, profile, today=today)
        repeated = CropCalendarNotificationService.process_farmer(user, profile, today=today)

    assert result["agricultural_advisory"] == 1
    assert repeated["agricultural_advisory"] == 0
    row = next(iter(saved.values()))
    assert row["title"][0] == "Live weather update unavailable"
    assert "no live measurements" in row["message"][0]
    assert row["title"][1] and row["message"][1]


def test_weather_api_failures_keep_calendar_and_saved_stage_advice_idempotent(monkeypatch):
    saved = _persist_fake(monkeypatch)
    today = date(2026, 5, 15)
    profile = _profile(planting_date=today + timedelta(days=1))
    user = _user(language="am")
    real_generate = notifications.AgriculturalAdvisoryService.generate
    real_soil_calculate = notifications.SoilWaterService.calculate

    def unavailable(*args, **kwargs):
        raise TimeoutError("provider timed out")

    _patch_weather_and_advisories(monkeypatch, [])
    monkeypatch.setattr(notifications.WeatherService, "get_forecast_by_coordinates", unavailable)
    monkeypatch.setattr(notifications.WeatherService, "get_historical_water_weather", unavailable)
    monkeypatch.setattr(notifications.WeatherService, "get_current_weather_by_coordinates", unavailable)
    monkeypatch.setattr(notifications.SoilWaterService, "calculate", real_soil_calculate)
    advisory_results = []
    advisory_inputs = []

    def generate(**kwargs):
        result = real_generate(**kwargs)
        advisory_results.append(result)
        advisory_inputs.append(kwargs)
        return result

    monkeypatch.setattr(notifications.AgriculturalAdvisoryService, "generate", generate)

    with Flask(__name__).app_context():
        first = CropCalendarNotificationService.process_farmer(
            user, profile, today=today
        )
        repeated = CropCalendarNotificationService.process_farmer(
            user, profile, today=today
        )

    assert first["crop_activity"] == 1
    assert first["agricultural_advisory"] == 1
    assert repeated["crop_activity"] == repeated["agricultural_advisory"] == 0
    assert len(saved) == 2
    assert any(row["dedupe_key"].startswith("activity:") for row in saved.values())
    fallback = next(row for row in saved.values() if row["notification_type"] == "agricultural_advisory")
    assert "No weather or soil-moisture measurements are estimated" in fallback["message"][0]
    assert "የአፈር እርጥበት መለኪያ አይገመትም" in fallback["message"][1]
    assert all(
        "crop_stage" in {item["id"] for item in result["recommendations"]}
        and {
            "advisoryMissingCurrentWeather",
            "advisoryMissingForecast",
            "advisoryMissingHistoricalWeather",
        }.issubset(result["missing_data_keys"])
        for result in advisory_results
    )
    assert all(
        values["current_weather"] is None
        and values["forecast"] is None
        and values["historical"] is None
        and values["soil_water"]["root_zone"] is None
        for values in advisory_inputs
    )


def test_run_daily_continues_to_other_farmers_after_weather_failure(monkeypatch):
    today = date(2026, 5, 15)
    _persist_fake(monkeypatch)
    first_user, second_user = _user(7), _user(8)
    first_profile = _profile(user_id=7)
    second_profile = _profile(user_id=8)
    second_profile.latitude = 8.6

    class FarmerQuery:
        def join(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [(first_user, first_profile), (second_user, second_profile)]

    monkeypatch.setattr(notifications.db.session, "query", lambda *_args: FarmerQuery())
    _patch_weather_and_advisories(monkeypatch, [])
    successful_forecasts = []

    def forecast(latitude, longitude):
        if latitude == first_profile.latitude:
            raise TimeoutError("Open-Meteo timed out")
        successful_forecasts.append((latitude, longitude))
        return {
            "provider": "Open-Meteo",
            "days": [{"date": today.isoformat(), "weather_code": 2, "precipitation_mm": 0}],
        }

    monkeypatch.setattr(notifications.WeatherService, "get_forecast_by_coordinates", forecast)

    with Flask(__name__).app_context():
        totals = CropCalendarNotificationService.run_daily()

    assert totals["farmers"] == 2
    assert totals["failed"] == 0
    assert successful_forecasts == [(second_profile.latitude, second_profile.longitude)]


def test_missing_location_still_notifies_of_missing_inputs_without_weather_calls(monkeypatch):
    saved = _persist_fake(monkeypatch)
    profile = _profile(planting_date=None, coordinates=False)

    def unexpected(*args, **kwargs):
        pytest.fail("weather provider must not be called without saved coordinates")

    monkeypatch.setattr(notifications.WeatherService, "get_forecast_by_coordinates", unexpected)
    result = CropCalendarNotificationService.process_farmer(_user(), profile, today=date(2026, 5, 15))

    assert result["soil_water_alert"] == 1
    assert len(saved) == 1


def test_scheduler_is_disabled_for_tests(monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=True, SMART_NOTIFICATIONS_ENABLED=True)
    starts = []
    monkeypatch.setattr(scheduler.threading.Thread, "start", lambda self: starts.append(self))

    start_smart_notification_scheduler(app)

    assert starts == []


def test_scheduler_is_suppressed_in_debug_reloader_parent(monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=False, SMART_NOTIFICATIONS_ENABLED=True)
    app.debug = True
    starts = []
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    monkeypatch.setattr(scheduler.threading.Thread, "start", lambda self: starts.append(self))

    start_smart_notification_scheduler(app)

    assert starts == []


def test_scheduler_starts_once_per_app_instance(monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=False, SMART_NOTIFICATIONS_ENABLED=True)
    starts = []
    monkeypatch.setattr(scheduler.threading.Thread, "start", lambda self: starts.append(self))

    start_smart_notification_scheduler(app)
    start_smart_notification_scheduler(app)

    assert len(starts) == 1


def test_scheduler_passes_reference_date_and_language_as_distinct_keywords(monkeypatch):
    today = date(2026, 5, 15)
    _patch_weather_and_advisories(monkeypatch, [])
    calls = []

    def calendar(*, region, woreda, kebele, reference_date, language):
        calls.append({
            "region": region,
            "woreda": woreda,
            "kebele": kebele,
            "reference_date": reference_date,
            "language": language,
        })
        return {"reference_date": reference_date.isoformat(), "current_stage": {"stage": "planting"}}

    monkeypatch.setattr(notifications.CropCalendarService, "get_calendar", calendar)
    CropCalendarNotificationService.process_farmer(
        _user(language="am"),
        _profile(planting_date=today - timedelta(days=10)),
        today=today,
        include_weather=True,
    )

    assert calls == [{
        "region": "Oromia",
        "woreda": "Bako",
        "kebele": "Kebele 01",
        "reference_date": today,
        "language": "am",
    }]
