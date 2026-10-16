
from __future__ import annotations

from pathlib import Path

from flask_jwt_extended import create_access_token

from backend.app.main import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.advisory_record import AdvisoryRecord


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent

IMAGE_PATH = (
    PROJECT_ROOT
    / "ml_model"
    / "inference"
    / "test_images"
    / "sample.jpg"
)


# =========================================================
# HELPERS
# =========================================================

def make_token(
    app,
    user_id: int,
) -> str:
    """
    Create a JWT token for the test user.

    The application expects the JWT subject to be a
    string, so the user ID is converted to string.
    """

    with app.app_context():
        return create_access_token(
            identity=str(user_id)
        )


def assert_success(
    response,
    label: str,
):
    """
    Verify that an API response is successful.
    """

    print(
        f"{label}: HTTP {response.status_code}"
    )

    if response.status_code != 200:
        print(
            response.get_json()
        )

    assert response.status_code == 200

    body = response.get_json()

    assert body["success"] is True
    assert "data" in body

    return body["data"]


# =========================================================
# MAIN TEST
# =========================================================

def main():

    app = create_app("development")
    client = app.test_client()

    with app.app_context():

        # =================================================
        # FIND EXISTING TEST FARMER
        # =================================================

        user = (
            User.query
            .filter_by(
                phone_number="0968083366"
            )
            .first()
        )

        if user is None:

            raise RuntimeError(
                "Expected test farmer "
                "0968083366 was not found."
            )

        user_id = user.id

        print()
        print("=" * 60)
        print(
            "COMPONENT 5 - "
            "TREATMENT / ADVISORY DATABASE TEST"
        )
        print("=" * 60)

        print(
            "USER ID:",
            user_id,
        )

        print(
            "IMAGE:",
            IMAGE_PATH,
        )

        # =================================================
        # VERIFY TEST IMAGE
        # =================================================

        assert IMAGE_PATH.exists(), (
            f"Test image not found: {IMAGE_PATH}"
        )

        # =================================================
        # AUTHENTICATION
        # =================================================

        token = make_token(
            app,
            user_id,
        )

        headers = {
            "Authorization": f"Bearer {token}"
        }

        # =================================================
        # RECORD COUNTS BEFORE TEST
        # =================================================

        diagnosis_before = (
            DiagnosisRecord.query
            .filter_by(
                user_id=user_id
            )
            .count()
        )

        advisory_before = (
            AdvisoryRecord.query
            .filter_by(
                user_id=user_id
            )
            .count()
        )

        print()
        print("Records before:")
        print(
            "  Diagnoses:",
            diagnosis_before,
        )
        print(
            "  Advisories:",
            advisory_before,
        )

        # =================================================
        # ENGLISH COMPLETE DIAGNOSIS
        # =================================================

        with open(
            IMAGE_PATH,
            "rb",
        ) as image_file:

            response = client.post(
                "/api/diagnosis/complete",
                headers=headers,
                data={
                    "image": (
                        image_file,
                        "component5_sample.jpg",
                    ),
                    "language": "en",
                    "explain": "false",
                },
                content_type="multipart/form-data",
            )

        data_en = assert_success(
            response,
            "1. Complete diagnosis EN",
        )

        # =================================================
        # CHECK ENGLISH DIAGNOSIS
        # =================================================

        diagnosis_en = data_en["diagnosis"]

        prediction_en = (
            diagnosis_en["prediction"]
        )

        database_en = data_en["database"]

        diagnosis_id_en = (
            database_en["diagnosis_id"]
        )

        advisory_id_en = (
            database_en["advisory_id"]
        )

        print()
        print("English diagnosis:")

        print(
            "  Diagnosis ID:",
            diagnosis_id_en,
        )

        print(
            "  Disease:",
            prediction_en["class_name"],
        )

        print(
            "  Confidence:",
            prediction_en["confidence"],
        )

        assert diagnosis_id_en is not None
        assert advisory_id_en is not None

        # =================================================
        # CHECK ENGLISH ADVISORY
        # =================================================

        advisory_en = data_en["advisory"]

        print()
        print("English advisory:")

        print(
            "  Language:",
            advisory_en["language"],
        )

        print(
            "  Disease:",
            advisory_en["disease"],
        )

        print(
            "  Severity:",
            advisory_en["severity"],
        )

        print(
            "  Management items:",
            len(
                advisory_en["management"]
            ),
        )

        assert (
            advisory_en["language"]
            == "en"
        )

        assert advisory_en["disease"]

        assert advisory_en["description"]

        assert isinstance(
            advisory_en["management"],
            list,
        )

        assert len(
            advisory_en["management"]
        ) > 0, (
            "English advisory does not "
            "contain management/treatment "
            "information."
        )

        # =================================================
        # CHECK ENGLISH DATABASE RECORDS
        # =================================================

        diagnosis_record_en = (
            db.session.get(
                DiagnosisRecord,
                diagnosis_id_en,
            )
        )

        advisory_record_en = (
            db.session.get(
                AdvisoryRecord,
                advisory_id_en,
            )
        )

        assert diagnosis_record_en is not None

        assert advisory_record_en is not None

        assert (
            diagnosis_record_en.user_id
            == user_id
        )

        assert (
            advisory_record_en.user_id
            == user_id
        )

        assert (
            advisory_record_en.diagnosis_id
            == diagnosis_id_en
        )

        assert (
            advisory_record_en.language
            == "en"
        )

        assert (
            advisory_record_en.advisory_text
        )

        print()
        print(
            "English database linkage: PASS"
        )

        # =================================================
        # CHECK HISTORY LIST
        # =================================================

        history_response = client.get(
            "/api/diagnosis/history",
            headers=headers,
        )

        history_data = assert_success(
            history_response,
            "2. Diagnosis history",
        )

        diagnoses = (
            history_data["diagnoses"]
        )

        history_item = next(
            (
                item
                for item in diagnoses
                if item["id"]
                == diagnosis_id_en
            ),
            None,
        )

        assert history_item is not None

        assert (
            history_item["user_id"]
            == user_id
        )

        assert (
            history_item["disease_class"]
            == prediction_en["class_name"]
        )

        print(
            "History diagnosis linkage: PASS"
        )

        # =================================================
        # CHECK DIAGNOSIS DETAIL + ADVISORY
        # =================================================

        detail_response = client.get(
            f"/api/diagnosis/history/"
            f"{diagnosis_id_en}",
            headers=headers,
        )

        detail_data = assert_success(
            detail_response,
            "3. Diagnosis detail",
        )

        assert "advisory" in detail_data

        assert (
            detail_data["advisory"]["id"]
            == advisory_id_en
        )

        assert (
            detail_data["advisory"]["language"]
            == "en"
        )

        print(
            "Diagnosis detail advisory linkage: PASS"
        )

        # =================================================
        # AMHARIC COMPLETE DIAGNOSIS
        # =================================================

        with open(
            IMAGE_PATH,
            "rb",
        ) as image_file:

            response = client.post(
                "/api/diagnosis/complete",
                headers=headers,
                data={
                    "image": (
                        image_file,
                        "component5_sample_am.jpg",
                    ),
                    "language": "am",
                    "explain": "false",
                },
                content_type="multipart/form-data",
            )

        data_am = assert_success(
            response,
            "4. Complete diagnosis AM",
        )

        # =================================================
        # CHECK AMHARIC DIAGNOSIS
        # =================================================

        diagnosis_am = data_am["diagnosis"]

        prediction_am = (
            diagnosis_am["prediction"]
        )

        database_am = data_am["database"]

        diagnosis_id_am = (
            database_am["diagnosis_id"]
        )

        advisory_id_am = (
            database_am["advisory_id"]
        )

        print()
        print("Amharic diagnosis:")

        print(
            "  Diagnosis ID:",
            diagnosis_id_am,
        )

        print(
            "  Disease:",
            prediction_am["class_name"],
        )

        print(
            "  Confidence:",
            prediction_am["confidence"],
        )

        assert diagnosis_id_am is not None

        assert advisory_id_am is not None

        # =================================================
        # CHECK AMHARIC ADVISORY
        # =================================================

        advisory_am = data_am["advisory"]

        print()
        print("Amharic advisory:")

        print(
            "  Language:",
            advisory_am["language"],
        )

        print(
            "  Disease:",
            advisory_am["disease"],
        )

        print(
            "  Severity:",
            advisory_am["severity"],
        )

        print(
            "  Management items:",
            len(
                advisory_am["management"]
            ),
        )

        assert (
            advisory_am["language"]
            == "am"
        )

        assert advisory_am["disease"]

        assert advisory_am["description"]

        assert isinstance(
            advisory_am["management"],
            list,
        )

        assert len(
            advisory_am["management"]
        ) > 0, (
            "Amharic advisory does not "
            "contain management/treatment "
            "information."
        )

        # =================================================
        # CHECK AMHARIC DATABASE RECORD
        # =================================================

        advisory_record_am = (
            db.session.get(
                AdvisoryRecord,
                advisory_id_am,
            )
        )

        assert (
            advisory_record_am is not None
        )

        assert (
            advisory_record_am.user_id
            == user_id
        )

        assert (
            advisory_record_am.diagnosis_id
            == diagnosis_id_am
        )

        assert (
            advisory_record_am.language
            == "am"
        )

        assert (
            advisory_record_am.advisory_text
        )

        print(
            "Amharic database linkage: PASS"
        )

        # =================================================
        # CHECK AMHARIC DIAGNOSIS DETAIL
        # =================================================

        detail_response_am = client.get(
            f"/api/diagnosis/history/"
            f"{diagnosis_id_am}",
            headers=headers,
        )

        detail_data_am = assert_success(
            detail_response_am,
            "5. Amharic diagnosis detail",
        )

        assert (
            "advisory"
            in detail_data_am
        )

        assert (
            detail_data_am["advisory"]["id"]
            == advisory_id_am
        )

        assert (
            detail_data_am["advisory"]["language"]
            == "am"
        )

        print(
            "Amharic diagnosis detail "
            "advisory linkage: PASS"
        )

        # =================================================
        # FINAL COUNTS
        # =================================================

        diagnosis_after = (
            DiagnosisRecord.query
            .filter_by(
                user_id=user_id
            )
            .count()
        )

        advisory_after = (
            AdvisoryRecord.query
            .filter_by(
                user_id=user_id
            )
            .count()
        )

        print()
        print("Records after:")

        print(
            "  Diagnoses:",
            diagnosis_after,
        )

        print(
            "  Advisories:",
            advisory_after,
        )

        # Exactly two complete diagnosis
        # workflows should create exactly:
        #
        #   +2 diagnosis records
        #   +2 advisory records

        assert (
            diagnosis_after
            == diagnosis_before + 2
        )

        assert (
            advisory_after
            == advisory_before + 2
        )

        # =================================================
        # FINAL RESULT
        # =================================================

        print()
        print("=" * 60)
        print(
            "COMPONENT 5 TEST PASSED"
        )
        print("=" * 60)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()

