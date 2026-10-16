from backend.app.models import DiagnosisRecord, User
from flask_jwt_extended import create_access_token


def create_user(database, phone, name):
    user = User(
        phone_number=phone,
        full_name=name,
        password_hash="test-hash",
        role="farmer",
        preferred_language="en",
    )
    database.session.add(user)
    database.session.commit()
    return user


def create_diagnosis(database, user_id):
    record = DiagnosisRecord(
        user_id=user_id,
        image_filename="test_leaf.jpg",
        image_path="uploads/test_leaf.jpg",
        disease_class="Blight",
        confidence=0.90,
        model_name="MobileNetV2",
        model_version="test",
        prediction_time=0.2,
        explainability_requested=False,
    )
    database.session.add(record)
    database.session.commit()
    return record


def auth_header(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def test_farmer_cannot_delete_another_farmers_diagnosis(client, database, app):
    owner = create_user(database, "0900000101", "Owner Farmer")
    other_farmer = create_user(database, "0900000102", "Other Farmer")
    diagnosis = create_diagnosis(database, owner.id)

    response = client.delete(
        f"/api/diagnosis/history/{diagnosis.id}",
        headers=auth_header(app, other_farmer.id),
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "DIAGNOSIS_NOT_FOUND"

    remaining = database.session.get(DiagnosisRecord, diagnosis.id)
    assert remaining is not None
    assert remaining.user_id == owner.id


def test_farmer_can_delete_own_diagnosis(client, database, app):
    owner = create_user(database, "0900000103", "Owner Farmer")
    diagnosis = create_diagnosis(database, owner.id)

    response = client.delete(
        f"/api/diagnosis/history/{diagnosis.id}",
        headers=auth_header(app, owner.id),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["diagnosis_id"] == diagnosis.id

    assert database.session.get(DiagnosisRecord, diagnosis.id) is None


def test_delete_diagnosis_requires_authentication(client, database):
    owner = create_user(database, "0900000104", "Owner Farmer")
    diagnosis = create_diagnosis(database, owner.id)

    response = client.delete(
        f"/api/diagnosis/history/{diagnosis.id}"
    )

    assert response.status_code == 401
    assert database.session.get(DiagnosisRecord, diagnosis.id) is not None
