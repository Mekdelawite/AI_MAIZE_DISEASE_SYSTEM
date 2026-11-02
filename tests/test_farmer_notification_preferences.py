from datetime import datetime, timezone
from types import SimpleNamespace

from flask import Flask
from flask_jwt_extended import create_access_token

from backend.app.extensions import db
from backend.app.models import FarmerProfile, User
from backend.app.services.farmer_targeting_service import FarmerTargetingService

from backend.app.routes.profile import DEFAULT_NOTIFICATION_PREFERENCES, _valid_notification_preferences
from backend.app.services.crop_calendar_notification_service import CropCalendarNotificationService


def test_default_preferences_preserve_existing_delivery_categories():
    assert DEFAULT_NOTIFICATION_PREFERENCES["reminder_days_before"] == 0
    assert all(channels == {"in_app": True, "sms": True} for channels in DEFAULT_NOTIFICATION_PREFERENCES["categories"].values())
    assert DEFAULT_NOTIFICATION_PREFERENCES["timezone"] == "Africa/Addis_Ababa"


def test_preferences_reject_invalid_timing_and_timezone():
    value = {
        **DEFAULT_NOTIFICATION_PREFERENCES,
        "categories": {key: dict(channels) for key, channels in DEFAULT_NOTIFICATION_PREFERENCES["categories"].items()},
        "quiet_hours": dict(DEFAULT_NOTIFICATION_PREFERENCES["quiet_hours"]),
    }
    assert _valid_notification_preferences(value)
    value["reminder_days_before"] = 4
    assert not _valid_notification_preferences(value)


def test_quiet_hours_cross_midnight_and_critical_policy():
    app = Flask(__name__)
    app.config["CRITICAL_ALERTS_BYPASS_QUIET_HOURS"] = True
    profile = SimpleNamespace(notification_preferences={
        "categories": {}, "quiet_hours": {"enabled": True, "start": "21:00", "end": "07:00"},
        "timezone": "Africa/Addis_Ababa",
    })
    with app.app_context():
        # 20:30 UTC is 23:30 in Addis Ababa, inside the quiet period.
        assert CropCalendarNotificationService.quiet_now(profile, now=datetime(2026, 1, 1, 20, 30, tzinfo=timezone.utc))
        assert not CropCalendarNotificationService.quiet_now(profile, now=datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc), critical=True)
        app.config["CRITICAL_ALERTS_BYPASS_QUIET_HOURS"] = False
        assert CropCalendarNotificationService.quiet_now(profile, now=datetime(2026, 1, 1, 20, 30, tzinfo=timezone.utc), critical=True)


def test_invalid_saved_preferences_fall_back_without_affecting_scheduler():
    profile = SimpleNamespace(notification_preferences={
        "categories": "invalid", "reminder_days_before": 99,
        "quiet_hours": {"enabled": True, "start": "nonsense", "end": "07:00"}, "timezone": "Invalid/Zone",
    })
    safe = CropCalendarNotificationService.preferences(profile)
    assert safe["reminder_days_before"] == 0
    assert safe["timezone"] == "Africa/Addis_Ababa"
    assert safe["quiet_hours"]["enabled"] is False
    assert safe["categories"]["important_alerts"] == {"in_app": True, "sms": True}


def _create_farmer(database, phone, *, role="farmer"):
    user = User(phone_number=phone, full_name="Preference Test", role=role, preferred_language="en", is_active=True, password_hash="unused")
    database.session.add(user)
    database.session.flush()
    if role == "farmer":
        database.session.add(FarmerProfile(user_id=user.id, region="Oromia", woreda="Adama", sms_opt_in=True))
    database.session.commit()
    return user


def _headers(app, user):
    with app.app_context():
        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_profile_preferences_default_persist_and_remain_farmer_owned(client, app, database):
    farmer = _create_farmer(database, "0911000201")
    other = _create_farmer(database, "0911000202")
    farmer_headers = _headers(app, farmer)
    other_headers = _headers(app, other)

    default = client.get("/api/profile", headers=farmer_headers).get_json()["data"]["farmer_profile"]["notification_preferences"]
    assert default == DEFAULT_NOTIFICATION_PREFERENCES
    updated = {
        **DEFAULT_NOTIFICATION_PREFERENCES,
        "categories": {key: dict(value) for key, value in DEFAULT_NOTIFICATION_PREFERENCES["categories"].items()},
        "quiet_hours": {**DEFAULT_NOTIFICATION_PREFERENCES["quiet_hours"], "enabled": True},
        "reminder_days_before": 2,
    }
    updated["categories"]["crop_activity"]["in_app"] = False
    updated["categories"]["important_alerts"]["sms"] = False
    response = client.put("/api/profile", json={"notification_preferences": updated}, headers=farmer_headers)
    assert response.status_code == 200
    saved = client.get("/api/profile", headers=farmer_headers).get_json()["data"]["farmer_profile"]
    assert saved["notification_preferences"] == updated
    assert saved["sms_opt_in"] is True  # category-level choice does not rewrite master consent
    other_saved = client.get("/api/profile", headers=other_headers).get_json()["data"]["farmer_profile"]
    assert other_saved["notification_preferences"] == DEFAULT_NOTIFICATION_PREFERENCES


def test_profile_notification_preferences_require_auth_and_farmer_role(client, app, database):
    assert client.get("/api/profile").status_code == 401
    extension_agent = _create_farmer(database, "0911000203", role="extension_agent")
    response = client.put("/api/profile", json={"notification_preferences": DEFAULT_NOTIFICATION_PREFERENCES}, headers=_headers(app, extension_agent))
    assert response.status_code == 403


def test_sms_category_and_in_app_preferences_are_independent(database):
    farmer = _create_farmer(database, "0911000204")
    profile = db.session.get(FarmerProfile, farmer.id)
    profile.notification_preferences = {
        **DEFAULT_NOTIFICATION_PREFERENCES,
        "categories": {key: dict(value) for key, value in DEFAULT_NOTIFICATION_PREFERENCES["categories"].items()},
    }
    profile.notification_preferences["categories"]["important_alerts"]["sms"] = False
    database.session.commit()
    sms_targets = FarmerTargetingService.find_farmers("Oromia")
    app_targets = FarmerTargetingService.find_farmers("Oromia", sms_only=False)
    assert all(item["user_id"] != farmer.id for item in sms_targets)
    assert any(item["user_id"] == farmer.id for item in app_targets)
