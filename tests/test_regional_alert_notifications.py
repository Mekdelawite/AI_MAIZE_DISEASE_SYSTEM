from unittest.mock import patch

from flask_jwt_extended import create_access_token

from backend.app.models import FarmerNotification, FarmerProfile, SMSRecord, User


def _auth_headers(app, user_id, role):
    with app.app_context():
        token = create_access_token(
            identity=str(user_id),
            additional_claims={"role": role},
        )
    return {"Authorization": f"Bearer {token}"}


def _create_users(database):
    admin = User(phone_number="0911000001", full_name="Admin", role="admin")
    admin.set_password("TestPassword123!")
    farmer = User(
        phone_number="0911000002",
        full_name="Farmer",
        role="farmer",
        preferred_language="en",
    )
    farmer.set_password("TestPassword123!")
    database.session.add_all([admin, farmer])
    database.session.flush()
    database.session.add(
        FarmerProfile(
            user_id=farmer.id,
            region="Oromia",
            woreda="Bahir Dar",
            kebele="01",
            sms_opt_in=True,
        )
    )
    database.session.commit()
    return admin, farmer


def test_regional_notification_schema_failure_does_not_block_sms(client, app, database):
    admin, _farmer = _create_users(database)
    headers = _auth_headers(app, admin.id, "admin")
    def fail_notification_commit():
        raise RuntimeError("farmer_notifications table unavailable")

    with patch.object(database.session, "commit", side_effect=fail_notification_commit), patch(
        "backend.app.routes.regional_alert.SMSService.send_sms",
        return_value={"phone": "0911000002", "status": "sent"},
    ) as send_sms:
        response = client.post(
            "/api/admin/regional-alerts",
            json={
                "regions": ["Oromia"],
                "message_en": "Inspect affected maize fields.",
                "message_am": "የበቆሎ ስፍራውን ይመርምሩ።",
                "method": "both",
            },
            headers=headers,
        )

    assert response.status_code == 201
    assert response.get_json()["success"] is True
    assert response.get_json()["app_notification_error"] == "Could not persist app notifications."
    send_sms.assert_called_once()


def test_regional_notification_retry_does_not_duplicate(client, app, database):
    admin, _farmer = _create_users(database)
    headers = _auth_headers(app, admin.id, "admin")
    payload = {
        "regions": ["Oromia"],
        "message_en": "Inspect affected maize fields.",
        "message_am": "የበቆሎ ስፍራውን ይመርምሩ።",
        "method": "app",
    }

    first = client.post("/api/admin/regional-alerts", json=payload, headers=headers)
    second = client.post("/api/admin/regional-alerts", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.get_json()["app_notifications_created"] == 0

    assert database.session.query(FarmerNotification).count() == 1


def test_farmer_notification_center_returns_full_history_and_persists_read_state(client, app, database):
    _admin, farmer = _create_users(database)
    other = User(phone_number="0911000003", full_name="Other Farmer", role="farmer")
    other.set_password("TestPassword123!")
    database.session.add(other)
    database.session.flush()

    rows = [
        FarmerNotification(
            user_id=farmer.id,
            title_en=f"Alert {index}",
            title_am=f"ማስጠንቀቂያ {index}",
            message_en=f"Full notification message {index}",
            message_am=f"ሙሉ መልዕክት {index}",
            region="Oromia",
            notification_type="weather_alert",
        )
        for index in range(35)
    ]
    other_row = FarmerNotification(
        user_id=other.id,
        title_en="Private",
        title_am="የግል",
        message_en="Other farmer notification",
        message_am="ሌላ ገበሬ ማስታወቂያ",
        region="Oromia",
    )
    database.session.add_all([*rows, other_row])
    database.session.commit()

    headers = _auth_headers(app, farmer.id, "farmer")
    response = client.get("/api/farmer/notifications", headers=headers)
    items = response.get_json()["notifications"]
    assert response.status_code == 200
    assert len(items) == 35
    assert items[0]["message"]
    assert items[0]["notification_type"] == "weather_alert"

    unread = client.get("/api/farmer/notifications/unread-count", headers=headers)
    assert unread.get_json()["count"] == 35

    foreign_read = client.patch(
        f"/api/farmer/notifications/{other_row.id}/read", headers=headers
    )
    assert foreign_read.status_code == 404
    assert other_row.is_read is False

    one_read = client.patch(
        f"/api/farmer/notifications/{items[0]['id']}/read", headers=headers
    )
    assert one_read.status_code == 200
    assert database.session.get(FarmerNotification, items[0]["id"]).is_read is True

    all_read = client.patch("/api/farmer/notifications/read-all", headers=headers)
    assert all_read.status_code == 200
    assert all_read.get_json()["updated"] == 34
    assert client.get("/api/farmer/notifications/unread-count", headers=headers).get_json()["count"] == 0


def test_non_farmer_cannot_read_farmer_notifications(client, app, database):
    admin, _farmer = _create_users(database)
    response = client.get(
        "/api/farmer/notifications",
        headers=_auth_headers(app, admin.id, "admin"),
    )
    assert response.status_code == 403


def test_regional_sms_respects_opt_in_and_skips_recent_duplicates(client, app, database):
    admin, farmer = _create_users(database)
    profile = FarmerProfile.query.filter_by(user_id=farmer.id).one()
    profile.sms_opt_in = False
    database.session.add(SMSRecord(
        user_id=farmer.id,
        recipient_phone=farmer.phone_number,
        recipient_type="farmer",
        message="Check rainfall in your area.",
        language="en",
        notification_type="regional_alert",
        status="sent",
        region="Oromia",
    ))
    database.session.commit()

    with patch("backend.app.routes.regional_alert.SMSService.send_sms") as send_sms:
        response = client.post(
            "/api/admin/regional-alerts",
            json={
                "regions": ["Oromia"],
                "message_en": "Check rainfall in your area.",
                "message_am": "በአካባቢዎ ያለውን ዝናብ ይመልከቱ።",
                "method": "sms",
            },
            headers=_auth_headers(app, admin.id, "admin"),
        )

    assert response.status_code == 201
    assert response.get_json()["sms_eligible_count"] == 0
    assert response.get_json()["sms_duplicates_skipped"] == 0
    send_sms.assert_not_called()

    profile.sms_opt_in = True
    database.session.commit()
    with patch("backend.app.routes.regional_alert.SMSService.send_sms") as send_sms:
        response = client.post(
            "/api/admin/regional-alerts",
            json={
                "regions": ["Oromia"],
                "message_en": "Check rainfall in your area.",
                "message_am": "በአካባቢዎ ያለውን ዝናብ ይመልከቱ።",
                "method": "sms",
            },
            headers=_auth_headers(app, admin.id, "admin"),
        )

    assert response.status_code == 201
    assert response.get_json()["sms_eligible_count"] == 1
    assert response.get_json()["sms_duplicates_skipped"] == 1
    send_sms.assert_not_called()
