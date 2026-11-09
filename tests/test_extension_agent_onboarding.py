import re
from datetime import datetime, timedelta, timezone

from flask_jwt_extended import create_access_token

from backend.app.extensions import db
from backend.app.models.administrative_division import (
    GeographyRegion,
    GeographyWoreda,
    GeographyZone,
)
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.extension_agent_activation import ExtensionAgentActivation
from backend.app.models.extension_agent_assignment_history import (
    ExtensionAgentAssignmentHistory,
)
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User
from backend.app.services.sms_service import SMSService


def _create_user(role, phone, *, active=True):
    user = User(
        phone_number=phone,
        full_name=f"{role} Test",
        role=role,
        preferred_language="en",
        is_active=active,
        password_hash="unused",
    )
    db.session.add(user)
    db.session.flush()
    return user


def _create_location(region_id, region_name, zone_id, zone_name, woreda_id, woreda_name):
    region = GeographyRegion(id=region_id, name_en=region_name)
    zone = GeographyZone(
        id=zone_id,
        region_id=region_id,
        name_en=zone_name,
    )
    woreda = GeographyWoreda(
        id=woreda_id,
        zone_id=zone_id,
        name_en=woreda_name,
    )
    db.session.add_all([region, zone, woreda])
    db.session.flush()
    return region, zone, woreda


def _token(user):
    return create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )


def _agent_payload(*, professional_info_verified=True):
    return {
        "phone_number": "0910112233",
        "full_name": "Maize Extension Agent",
        "email": "agent@example.org",
        "employee_id": "EA-001",
        "organization": "Agricultural Office",
        "region_id": "region-a",
        "zone_id": "zone-a",
        "woreda_id": "woreda-a",
        "verification_method": "sms",
        "professional_info_verified": professional_info_verified,
    }


def test_admin_activation_transfer_and_woreda_scoping(
    app,
    client,
    database,
    monkeypatch,
):
    admin = _create_user("admin", "0900000101")
    region_a, zone_a, woreda_a = _create_location(
        "region-a", "Amhara", "zone-a", "Bahir Dar", "woreda-a", "Bahir Dar Zuria"
    )
    region_b, zone_b, woreda_b = _create_location(
        "region-b", "Oromia", "zone-b", "Adama", "woreda-b", "Adama"
    )
    db.session.commit()

    sent_messages = []

    def fake_send_sms(phone, message, **kwargs):
        sent_messages.append((phone, message, kwargs))
        return {"success": True, "status": "sent", "sms_record_id": None}

    monkeypatch.setattr(SMSService, "send_sms", staticmethod(fake_send_sms))
    admin_headers = {"Authorization": f"Bearer {_token(admin)}"}

    rejected = client.post(
        "/api/admin/extension-agents",
        headers=admin_headers,
        json=_agent_payload(professional_info_verified=False),
    )
    assert rejected.status_code == 400
    assert User.query.filter_by(role="extension_agent").count() == 0

    created = client.post(
        "/api/admin/extension-agents",
        headers=admin_headers,
        json=_agent_payload(),
    )
    assert created.status_code == 201
    agent_id = created.get_json()["data"]["agent_id"]
    agent_user = db.session.get(User, agent_id)
    agent = db.session.get(ExtensionAgent, agent_id)
    assert agent_user.is_active is False
    assert agent.account_status == "pending_activation"
    assert agent.professional_info_verified is True
    assert agent.professional_info_verified_by_id == admin.id
    assert created.get_json()["data"]["professional_info_verified_by"] == admin.full_name
    assert agent.woreda_id == woreda_a.id
    assert "password" not in created.get_json()["data"]
    assert "code" not in created.get_json()["data"]
    assert "otp" not in created.get_json()["data"]
    assert len(sent_messages) == 1

    pending_login = client.post(
        "/api/auth/login",
        json={
            "phone_number": agent_user.phone_number,
            "password": "unactivated-password",
        },
    )
    assert pending_login.status_code == 403

    resend = client.post(
        f"/api/admin/extension-agents/{agent_id}/activation-code",
        headers=admin_headers,
        json={},
    )
    assert resend.status_code == 429

    code = re.search(r"code is (\d{6})", sent_messages[0][1]).group(1)
    wrong_contact_method = client.post(
        "/api/auth/extension-agent/activation/verify",
        json={"contact": agent.email, "code": code},
    )
    assert wrong_contact_method.status_code == 400
    wrong_code = "000000" if code != "000000" else "000001"
    invalid = client.post(
        "/api/auth/extension-agent/activation/verify",
        json={"contact": agent_user.phone_number, "code": wrong_code},
    )
    assert invalid.status_code == 400

    verified = client.post(
        "/api/auth/extension-agent/activation/verify",
        json={"contact": agent_user.phone_number, "code": code},
    )
    assert verified.status_code == 200
    activation_token = verified.get_json()["data"]["activation_token"]
    activated = client.post(
        "/api/auth/extension-agent/activation/complete",
        json={
            "activation_token": activation_token,
            "password": "MaizeCareAgent2026!",
        },
    )
    assert activated.status_code == 200
    assert db.session.get(ExtensionAgent, agent_id).account_status == "active"

    reused_code = client.post(
        "/api/auth/extension-agent/activation/verify",
        json={"contact": agent_user.phone_number, "code": code},
    )
    assert reused_code.status_code == 400

    login = client.post(
        "/api/auth/login",
        json={
            "phone_number": agent_user.phone_number,
            "password": "MaizeCareAgent2026!",
        },
    )
    assert login.status_code == 200
    agent_headers = {
        "Authorization": f"Bearer {login.get_json()['data']['access_token']}"
    }

    assigned_farmer = _create_user("farmer", "0900000102")
    foreign_farmer = _create_user("farmer", "0900000103")
    db.session.add_all(
        [
            FarmerProfile(
                user_id=assigned_farmer.id,
                region=region_a.name_en,
                woreda=woreda_a.name_en,
            ),
            FarmerProfile(
                user_id=foreign_farmer.id,
                region=region_b.name_en,
                woreda=woreda_b.name_en,
            ),
        ]
    )
    assigned_diagnosis = DiagnosisRecord(
        user_id=assigned_farmer.id,
        disease_class="Common Rust",
        confidence=0.9,
    )
    foreign_diagnosis = DiagnosisRecord(
        user_id=foreign_farmer.id,
        disease_class="Gray Leaf Spot",
        confidence=0.8,
    )
    db.session.add_all([assigned_diagnosis, foreign_diagnosis])
    db.session.commit()

    visible = client.get("/api/extension/diagnoses", headers=agent_headers)
    assert visible.status_code == 200
    assert [
        item["id"] for item in visible.get_json()["data"]["diagnoses"]
    ] == [assigned_diagnosis.id]
    changed_parameter = client.get(
        f"/api/extension/diagnoses?farmer_id={foreign_farmer.id}",
        headers=agent_headers,
    )
    assert changed_parameter.status_code == 200
    assert changed_parameter.get_json()["data"]["diagnoses"] == []

    transfer = client.patch(
        f"/api/admin/extension-agents/{agent_id}/assignment",
        headers=admin_headers,
        json={
            "region_id": region_b.id,
            "zone_id": zone_b.id,
            "woreda_id": woreda_b.id,
        },
    )
    assert transfer.status_code == 200
    after_transfer = client.get("/api/extension/diagnoses", headers=agent_headers)
    assert after_transfer.status_code == 200
    assert [
        item["id"] for item in after_transfer.get_json()["data"]["diagnoses"]
    ] == [foreign_diagnosis.id]
    history = ExtensionAgentAssignmentHistory.query.filter_by(
        user_id=agent_id
    ).order_by(ExtensionAgentAssignmentHistory.id).all()
    assert [(item.previous_woreda_id, item.new_woreda_id) for item in history] == [
        (None, woreda_a.id),
        (woreda_a.id, woreda_b.id),
    ]

    suspended = client.patch(
        f"/api/admin/extension-agents/{agent_id}/status",
        headers=admin_headers,
        json={"account_status": "suspended"},
    )
    assert suspended.status_code == 200
    assert client.get("/api/extension/diagnoses", headers=agent_headers).status_code == 401
    suspended_login = client.post(
        "/api/auth/login",
        json={
            "phone_number": agent_user.phone_number,
            "password": "MaizeCareAgent2026!",
        },
    )
    assert suspended_login.status_code == 403

    reactivated = client.patch(
        f"/api/admin/extension-agents/{agent_id}/status",
        headers=admin_headers,
        json={"account_status": "active"},
    )
    assert reactivated.status_code == 200
    reactivated_access = client.get(
        "/api/extension/diagnoses",
        headers=agent_headers,
    )
    assert reactivated_access.status_code == 200


def test_expired_agent_activation_code_is_rejected(
    client,
    database,
    monkeypatch,
):
    admin = _create_user("admin", "0900000201")
    _create_location(
        "region-a", "Amhara", "zone-a", "Bahir Dar", "woreda-a", "Bahir Dar Zuria"
    )
    db.session.commit()
    sent_messages = []
    monkeypatch.setattr(
        SMSService,
        "send_sms",
        staticmethod(
            lambda phone, message, **kwargs: (
                sent_messages.append(message)
                or {"success": True, "status": "sent", "sms_record_id": None}
            )
        ),
    )

    created = client.post(
        "/api/admin/extension-agents",
        headers={"Authorization": f"Bearer {_token(admin)}"},
        json=_agent_payload(),
    )
    assert created.status_code == 201
    user_id = created.get_json()["data"]["agent_id"]
    code = re.search(r"code is (\d{6})", sent_messages[0]).group(1)

    activation = db.session.get(ExtensionAgentActivation, user_id)
    activation.otp_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()

    expired = client.post(
        "/api/auth/extension-agent/activation/verify",
        json={
            "contact": "0910112233",
            "code": code,
        },
    )
    assert expired.status_code == 400
