from flask_jwt_extended import create_access_token

from backend.app.extensions import db
from backend.app.models.administrative_division import (
    GeographyRegion,
    GeographyWoreda,
    GeographyZone,
)
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.outbreak_alert import OutbreakAlert
from backend.app.models.user import User


def _user(role, phone):
    user = User(
        phone_number=phone,
        full_name=f"{role} Test",
        role=role,
        preferred_language="en",
        is_active=True,
        password_hash="unused",
    )
    db.session.add(user)
    db.session.flush()
    return user


def _token(user):
    return create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )


def test_outbreak_alert_list_is_scoped_for_extension_agents(client, database):
    agent = _user("extension_agent", "0900000981")
    farmer = _user("farmer", "0900000982")
    admin = _user("admin", "0900000983")
    region = GeographyRegion(id="test-region", name_en="Amhara")
    zone = GeographyZone(
        id="test-zone",
        region_id=region.id,
        name_en="Bahir Dar",
    )
    woreda = GeographyWoreda(
        id="test-woreda",
        zone_id=zone.id,
        name_en="Bahir Dar Zuria",
    )
    db.session.add_all([region, zone, woreda])
    db.session.add(
        ExtensionAgent(
            user_id=agent.id,
            region=region.name_en,
            zone=zone.name_en,
            woreda=woreda.name_en,
            region_id=region.id,
            zone_id=zone.id,
            woreda_id=woreda.id,
        )
    )
    db.session.add_all(
        [
            OutbreakAlert(
                disease_class="Common Rust",
                risk_level="high",
                risk_score=80,
                region="Amhara",
                woreda="Bahir Dar Zuria",
            ),
            OutbreakAlert(
                disease_class="Gray Leaf Spot",
                risk_level="moderate",
                risk_score=45,
                region="Oromia",
                woreda="Adama",
            ),
        ]
    )
    db.session.commit()

    agent_response = client.get(
        "/api/outbreak-alerts",
        headers={"Authorization": f"Bearer {_token(agent)}"},
    )
    farmer_response = client.get(
        "/api/outbreak-alerts",
        headers={"Authorization": f"Bearer {_token(farmer)}"},
    )
    admin_response = client.get(
        "/api/outbreak-alerts",
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )

    assert agent_response.status_code == 200
    assert len(agent_response.get_json()["data"]) == 1
    assert farmer_response.status_code == 403
    assert admin_response.status_code == 200
    assert len(admin_response.get_json()["data"]) == 2
