"""
=========================================================
Component 4 - Diagnosis History API Tests
=========================================================

Controlled tests for:
- Authentication
- User ownership
- History listing
- Limit handling
- Single diagnosis retrieval
- Advisory inclusion
- Cross-user protection
- Safe deletion

This test creates one temporary diagnosis record and
deletes only that temporary record.
=========================================================
"""

from backend.app.main import create_app
from backend.app.extensions import db
from backend.app.models import DiagnosisRecord, AdvisoryRecord
from flask_jwt_extended import create_access_token


def make_token(app, user_id):
    with app.app_context():
        return create_access_token(identity=str(user_id))


def main():
    app = create_app("development")
    app.config["TESTING"] = True

    client = app.test_client()

    print("\n=================================================")
    print("COMPONENT 4 - DIAGNOSIS HISTORY API TEST")
    print("=================================================\n")

    # -------------------------------------------------
    # 1. Unauthenticated access
    # -------------------------------------------------

    response = client.get("/api/diagnosis/history")

    print("1. Unauthenticated history request:")
    print("   Status:", response.status_code)

    assert response.status_code == 401

    print("   PASS\n")

    # -------------------------------------------------
    # 2. Create temporary diagnosis + advisory
    # -------------------------------------------------

    with app.app_context():

        temp_diagnosis = DiagnosisRecord(
            user_id=1,
            image_filename="component4_test.jpg",
            image_path="uploads/component4_test.jpg",
            disease_class="Blight",
            confidence=91.25,
            model_name="Component4TestModel",
            model_version="test",
            prediction_time=0.10,
            explainability_requested=False,
        )

        db.session.add(temp_diagnosis)
        db.session.flush()

        temp_advisory = AdvisoryRecord(
            user_id=1,
            diagnosis_id=temp_diagnosis.id,
            language="en",
            advisory_text="Component 4 temporary advisory test.",
            source="component4_test",
        )

        db.session.add(temp_advisory)
        db.session.commit()

        temp_id = temp_diagnosis.id

        print("2. Temporary diagnosis created:")
        print("   Diagnosis ID:", temp_id)
        print("   PASS\n")

    # -------------------------------------------------
    # 3. User 1 history
    # -------------------------------------------------

    token_user1 = make_token(app, 1)

    response = client.get(
        "/api/diagnosis/history",
        headers={
            "Authorization": f"Bearer {token_user1}"
        },
    )

    print("3. User 1 diagnosis history:")
    print("   Status:", response.status_code)

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["data"]["user_id"] == 1

    diagnoses = data["data"]["diagnoses"]

    assert len(diagnoses) > 0

    # Every returned record must belong to user 1.
    for diagnosis in diagnoses:
        assert diagnosis["user_id"] == 1

    print("   Returned records:", len(diagnoses))
    print("   Ownership filtering: PASS")
    print("   PASS\n")

    # -------------------------------------------------
    # 4. Limit parameter
    # -------------------------------------------------

    response = client.get(
        "/api/diagnosis/history?limit=2",
        headers={
            "Authorization": f"Bearer {token_user1}"
        },
    )

    print("4. History limit=2:")
    print("   Status:", response.status_code)

    assert response.status_code == 200

    data = response.get_json()

    assert len(data["data"]["diagnoses"]) <= 2

    print("   Returned records:", len(data["data"]["diagnoses"]))
    print("   PASS\n")

    # -------------------------------------------------
    # 5. Invalid limit
    # -------------------------------------------------

    response = client.get(
        "/api/diagnosis/history?limit=abc",
        headers={
            "Authorization": f"Bearer {token_user1}"
        },
    )

    print("5. Invalid limit:")
    print("   Status:", response.status_code)

    assert response.status_code == 400

    print("   PASS\n")

    # -------------------------------------------------
    # 6. Get own diagnosis
    # -------------------------------------------------

    response = client.get(
        f"/api/diagnosis/history/{temp_id}",
        headers={
            "Authorization": f"Bearer {token_user1}"
        },
    )

    print("6. User 1 retrieves own diagnosis:")
    print("   Status:", response.status_code)

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["data"]["id"] == temp_id
    assert data["data"]["user_id"] == 1

    # Advisory must be included.
    assert data["data"]["advisory"] is not None
    assert (
        data["data"]["advisory"]["advisory_text"]
        == "Component 4 temporary advisory test."
    )

    print("   Diagnosis retrieval: PASS")
    print("   Advisory inclusion: PASS")
    print("   PASS\n")

    # -------------------------------------------------
    # 7. Cross-user protection
    # -------------------------------------------------

    # Existing diagnosis 14 belongs to user 2.
    response = client.get(
        "/api/diagnosis/history/14",
        headers={
            "Authorization": f"Bearer {token_user1}"
        },
    )

    print("7. User 1 attempts to access user 2 diagnosis:")
    print("   Status:", response.status_code)

    assert response.status_code == 404

    print("   Ownership protection: PASS")
    print("   PASS\n")

    # -------------------------------------------------
    # 8. User 1 cannot delete user 2 diagnosis
    # -------------------------------------------------

    response = client.delete(
        "/api/diagnosis/history/14",
        headers={
            "Authorization": f"Bearer {token_user1}"
        },
    )

    print("8. User 1 attempts to delete user 2 diagnosis:")
    print("   Status:", response.status_code)

    assert response.status_code == 404

    print("   Delete ownership protection: PASS")
    print("   PASS\n")

    # -------------------------------------------------
    # 9. Verify temporary advisory exists
    # -------------------------------------------------

    with app.app_context():

        advisory = AdvisoryRecord.query.filter_by(
            diagnosis_id=temp_id
        ).first()

        assert advisory is not None

        print("9. Temporary advisory exists before deletion:")
        print("   Advisory ID:", advisory.id)
        print("   PASS\n")

    # -------------------------------------------------
    # 10. Delete temporary diagnosis
    # -------------------------------------------------

    response = client.delete(
        f"/api/diagnosis/history/{temp_id}",
        headers={
            "Authorization": f"Bearer {token_user1}"
        },
    )

    print("10. Delete temporary diagnosis:")
    print("    Status:", response.status_code)

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True

    print("    PASS\n")

    # -------------------------------------------------
    # 11. Verify diagnosis is deleted
    # -------------------------------------------------

    with app.app_context():

        deleted_diagnosis = db.session.get(
            DiagnosisRecord,
            temp_id,
        )

        assert deleted_diagnosis is None

        print("11. Verify diagnosis deletion:")
        print("    Diagnosis removed: PASS")

        # Check advisory cascade.
        deleted_advisory = AdvisoryRecord.query.filter_by(
            diagnosis_id=temp_id
        ).first()

        assert deleted_advisory is None

        print("    Advisory cascade: PASS")
        print("    PASS\n")

    # -------------------------------------------------
    # FINAL
    # -------------------------------------------------

    print("=================================================")
    print("COMPONENT 4 TEST RESULT: ALL TESTS PASSED")
    print("=================================================")


if __name__ == "__main__":
    main()