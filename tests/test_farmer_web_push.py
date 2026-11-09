import base64
import json
from datetime import datetime, timedelta, timezone
import pywebpush
from flask_jwt_extended import create_access_token
from sqlalchemy.orm.attributes import flag_modified

from backend.app.extensions import db
from backend.app.models import (
    FarmerNotification,
    FarmerProfile,
    FarmerPushDelivery,
    FarmerPushSubscription,
    User,
)
from backend.app.routes.profile import DEFAULT_NOTIFICATION_PREFERENCES
from backend.app.services.web_push_service import WebPushService


def _key(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _create_farmer(database, phone, *, role="farmer", push=True):
    user = User(
        phone_number=phone,
        full_name="Push Test Farmer",
        password_hash="test-hash",
        role=role,
        preferred_language="en",
        is_active=True,
    )
    database.session.add(user)
    database.session.flush()
    if role == "farmer":
        preferences = {
            **DEFAULT_NOTIFICATION_PREFERENCES,
            "categories": {
                category: {
                    **channels,
                    "push": push,
                }
                for category, channels in DEFAULT_NOTIFICATION_PREFERENCES["categories"].items()
            },
        }
        database.session.add(FarmerProfile(
            user_id=user.id,
            region="Oromia",
            woreda="Adama",
            sms_opt_in=False,
            notification_preferences=preferences,
        ))
    database.session.commit()
    return user


def _headers(app, user):
    with app.app_context():
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role},
        )
    return {"Authorization": f"Bearer {token}"}


def _subscription(endpoint="https://fcm.googleapis.com/wp/device/123"):
    public_key = bytes([4]) + bytes(range(1, 65))
    return {
        "endpoint": endpoint,
        "expirationTime": None,
        "keys": {
            "p256dh": _key(public_key),
            "auth": _key(bytes(range(16))),
        },
    }


def _configure_push(app, monkeypatch):
    public_key = bytes([4]) + bytes(range(1, 65))
    monkeypatch.setitem(app.config, "WEB_PUSH_VAPID_PUBLIC_KEY", _key(public_key))
    monkeypatch.setitem(app.config, "WEB_PUSH_VAPID_PRIVATE_KEY", "test-private-key")
    monkeypatch.setitem(app.config, "WEB_PUSH_VAPID_SUBJECT", "mailto:push@example.test")


def test_push_config_and_subscription_endpoints_are_authenticated_and_farmer_only(
    client, app, database, monkeypatch
):
    farmer = _create_farmer(database, "0911000301")
    other_farmer = _create_farmer(database, "0911000302")
    extension_agent = _create_farmer(database, "0911000303", role="extension_agent")
    _configure_push(app, monkeypatch)

    assert client.get("/api/farmer/push/config").status_code == 401
    response = client.get("/api/farmer/push/config", headers=_headers(app, farmer))
    assert response.status_code == 200
    assert response.get_json()["public_key"] == app.config["WEB_PUSH_VAPID_PUBLIC_KEY"]
    assert client.get(
        "/api/farmer/push/config",
        headers=_headers(app, extension_agent),
    ).status_code == 403

    created = client.post(
        "/api/farmer/push/subscriptions",
        json=_subscription(),
        headers=_headers(app, farmer),
    )
    assert created.status_code == 201
    repeated = client.post(
        "/api/farmer/push/subscriptions",
        json=_subscription(),
        headers=_headers(app, farmer),
    )
    assert repeated.status_code == 201
    assert FarmerPushSubscription.query.count() == 1

    conflict = client.post(
        "/api/farmer/push/subscriptions",
        json=_subscription(),
        headers=_headers(app, other_farmer),
    )
    assert conflict.status_code == 409
    assert client.delete(
        "/api/farmer/push/subscriptions",
        json={"endpoint": _subscription()["endpoint"]},
        headers=_headers(app, other_farmer),
    ).get_json()["removed"] is False
    assert FarmerPushSubscription.query.one().user_id == farmer.id

    removed = client.delete(
        "/api/farmer/push/subscriptions",
        json={"endpoint": _subscription()["endpoint"]},
        headers=_headers(app, farmer),
    )
    assert removed.status_code == 200
    assert removed.get_json()["removed"] is True
    assert FarmerPushSubscription.query.count() == 0


def test_subscription_payload_validation_and_unconfigured_push(
    client, app, database, monkeypatch
):
    farmer = _create_farmer(database, "0911000304")
    headers = _headers(app, farmer)
    monkeypatch.setitem(app.config, "WEB_PUSH_VAPID_PUBLIC_KEY", "")
    monkeypatch.setitem(app.config, "WEB_PUSH_VAPID_PRIVATE_KEY", "")
    monkeypatch.setitem(app.config, "WEB_PUSH_VAPID_SUBJECT", "")
    response = client.post(
        "/api/farmer/push/subscriptions",
        json={"endpoint": "http://insecure.example.test/push", "keys": {}},
        headers=headers,
    )
    assert response.status_code == 503

    public_key = bytes([4]) + bytes(range(1, 65))
    app.config.update(
        WEB_PUSH_VAPID_PUBLIC_KEY=_key(public_key),
        WEB_PUSH_VAPID_PRIVATE_KEY="private",
        WEB_PUSH_VAPID_SUBJECT="mailto:push@example.test",
    )
    invalid = client.post(
        "/api/farmer/push/subscriptions",
        json={"endpoint": "https://push.example.test/push", "keys": {"p256dh": "bad", "auth": "bad"}},
        headers=headers,
    )
    assert invalid.status_code == 400


def test_push_delivery_is_generic_and_idempotent(client, app, database, monkeypatch):
    farmer = _create_farmer(database, "0911000305")
    _configure_push(app, monkeypatch)
    profile = db.session.get(FarmerProfile, farmer.id)
    profile.notification_preferences = {
        **profile.notification_preferences,
        "categories": {
            **profile.notification_preferences["categories"],
            "crop_activity": {
                **profile.notification_preferences["categories"]["crop_activity"],
                "in_app": False,
            },
        },
    }
    subscription = FarmerPushSubscription(
        user_id=farmer.id,
        **{
            "endpoint": _subscription()["endpoint"],
            "p256dh": _subscription()["keys"]["p256dh"],
            "auth": _subscription()["keys"]["auth"],
        },
    )
    notification = FarmerNotification(
        user_id=farmer.id,
        title_en="Private disease details",
        title_am="የግል ዝርዝር",
        message_en="Private farmer-specific details",
        message_am="የግል ዝርዝር",
        region="Oromia",
        notification_type="crop_activity",
        dedupe_key="push-idempotency-test",
    )
    database.session.add_all([subscription, notification])
    database.session.commit()
    sent = []

    def fake_webpush(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)

    assert WebPushService.enqueue_notification(notification) == 1
    assert WebPushService.enqueue_notification(notification) == 0
    assert len(sent) == 1
    payload = json.loads(sent[0]["data"])
    assert payload == {
        "title": "MaizeCare AI",
        "body": "A new farm update is ready. Open MaizeCare AI to view it.",
        "url": "/farmer/dashboard",
    }
    assert "Private" not in sent[0]["data"]
    delivery = FarmerPushDelivery.query.one()
    assert delivery.status == "sent"
    assert delivery.attempts == 1
    headers = _headers(app, farmer)
    assert client.get("/api/farmer/notifications", headers=headers).get_json()["notifications"] == []
    assert client.get(
        "/api/farmer/notifications/unread-count",
        headers=headers,
    ).get_json()["count"] == 0


def test_push_respects_category_and_quiet_hours(client, app, database, monkeypatch):
    farmer = _create_farmer(database, "0911000306")
    _configure_push(app, monkeypatch)
    profile = db.session.get(FarmerProfile, farmer.id)
    profile.notification_preferences = {
        **profile.notification_preferences,
        "quiet_hours": {
            "enabled": True,
            "start": "00:00",
            "end": "23:59",
        },
    }
    database.session.add(FarmerPushSubscription(
        user_id=farmer.id,
        **{
            "endpoint": _subscription()["endpoint"],
            "p256dh": _subscription()["keys"]["p256dh"],
            "auth": _subscription()["keys"]["auth"],
        },
    ))
    notification = FarmerNotification(
        user_id=farmer.id,
        title_en="Update",
        title_am="ማሳወቂያ",
        message_en="Details",
        message_am="ዝርዝር",
        region="Oromia",
        notification_type="crop_activity",
        dedupe_key="push-quiet-test",
    )
    database.session.add(notification)
    database.session.commit()
    sent = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kwargs: sent.append(kwargs))

    assert WebPushService.enqueue_notification(notification) == 1
    delivery = FarmerPushDelivery.query.one()
    assert delivery.status == "pending"
    assert not sent

    profile.notification_preferences["quiet_hours"]["enabled"] = False
    flag_modified(profile, "notification_preferences")
    delivery.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    database.session.commit()
    assert WebPushService.deliver_pending() == 1
    assert FarmerPushDelivery.query.one().status == "sent"

    profile.notification_preferences["categories"]["crop_activity"]["push"] = False
    flag_modified(profile, "notification_preferences")
    second = FarmerNotification(
        user_id=farmer.id,
        title_en="Update",
        title_am="ማሳወቂያ",
        message_en="Details",
        message_am="ዝርዝር",
        region="Oromia",
        notification_type="crop_activity",
        dedupe_key="push-category-opt-out-test",
    )
    database.session.add(second)
    database.session.commit()
    assert WebPushService.enqueue_notification(second) == 0


def test_expired_endpoint_is_removed(client, app, database, monkeypatch):
    farmer = _create_farmer(database, "0911000307")
    _configure_push(app, monkeypatch)
    subscription = FarmerPushSubscription(
        user_id=farmer.id,
        **{
            "endpoint": _subscription()["endpoint"],
            "p256dh": _subscription()["keys"]["p256dh"],
            "auth": _subscription()["keys"]["auth"],
        },
    )
    notification = FarmerNotification(
        user_id=farmer.id,
        title_en="Update",
        title_am="ማሳወቂያ",
        message_en="Details",
        message_am="ዝርዝር",
        region="Oromia",
        notification_type="crop_activity",
        dedupe_key="push-expired-test",
    )
    database.session.add_all([subscription, notification])
    database.session.commit()

    class ExpiredPushError(pywebpush.WebPushException):
        status_code = 410

    def expired_webpush(**kwargs):
        raise ExpiredPushError("subscription expired")

    monkeypatch.setattr(pywebpush, "webpush", expired_webpush)
    assert WebPushService.enqueue_notification(notification) == 1
    assert FarmerPushSubscription.query.count() == 0
