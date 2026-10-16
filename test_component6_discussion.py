
from flask_jwt_extended import create_access_token

from backend.app.main import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.discussion_post import DiscussionPost
from backend.app.models.discussion_reply import DiscussionReply


FARMER_1_PHONE = "0999000001"
FARMER_2_PHONE = "0999000002"
AGENT_PHONE = "0999000003"
ADMIN_PHONE = "0999000099"


def make_token(app, user_id, role):
    with app.app_context():
        return create_access_token(
            identity=str(user_id),
            additional_claims={"role": role},
        )


def assert_success(response, expected_status=200):
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got "
        f"{response.status_code}: {response.get_json()}"
    )

    body = response.get_json()

    assert body is not None
    assert body.get("success") is True
    assert "data" in body

    return body["data"]


def assert_error(response, expected_status):
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got "
        f"{response.status_code}: {response.get_json()}"
    )

    body = response.get_json()

    assert body is not None

    if body.get("success") is False:
        assert "error" in body
    else:
        assert "msg" in body


def extract_post_list(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in ("items", "posts", "results", "data", "result"):
        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            posts = extract_post_list(value)

            if posts:
                return posts

    return []


def get_post_ids(posts):
    return {
        int(post["id"])
        for post in posts
        if isinstance(post, dict) and "id" in post
    }


def cleanup_test_data(app, verbose=True):
    with app.app_context():

        test_phones = {
            FARMER_1_PHONE,
            FARMER_2_PHONE,
            AGENT_PHONE,
            ADMIN_PHONE,
        }

        users = (
            User.query
            .filter(User.phone_number.in_(test_phones))
            .all()
        )

        if not users:
            return

        user_ids = {user.id for user in users}

        replies = (
            DiscussionReply.query
            .filter(
                db.or_(
                    DiscussionReply.farmer_id.in_(user_ids),
                    DiscussionReply.extension_agent_id.in_(user_ids),
                )
            )
            .all()
        )

        for reply in replies:
            db.session.delete(reply)

        posts = (
            DiscussionPost.query
            .filter(DiscussionPost.author_id.in_(user_ids))
            .all()
        )

        for post in posts:
            db.session.delete(post)

        diagnoses = (
            DiagnosisRecord.query
            .filter(DiagnosisRecord.user_id.in_(user_ids))
            .all()
        )

        for diagnosis in diagnoses:
            db.session.delete(diagnosis)

        profiles = (
            FarmerProfile.query
            .filter(FarmerProfile.user_id.in_(user_ids))
            .all()
        )

        for profile in profiles:
            db.session.delete(profile)

        db.session.flush()

        for user in users:
            db.session.delete(user)

        db.session.commit()

        remaining = (
            User.query
            .filter(User.phone_number.in_(test_phones))
            .count()
        )

        assert remaining == 0

        if verbose:
            print("Temporary Component 6 records removed.")
            print("Cleanup verification: PASS")


def main():
    app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()

    cleanup_test_data(app, verbose=False)

    try:
        with app.app_context():
            farmer1 = User(
                phone_number=FARMER_1_PHONE,
                full_name="Component 6 Farmer One",
                role="farmer",
                preferred_language="en",
                is_active=True,
            )
            farmer1.set_password("TestPassword123!")

            farmer2 = User(
                phone_number=FARMER_2_PHONE,
                full_name="Component 6 Farmer Two",
                role="farmer",
                preferred_language="en",
                is_active=True,
            )
            farmer2.set_password("TestPassword123!")

            agent = User(
                phone_number=AGENT_PHONE,
                full_name="Component 6 Extension Agent",
                role="extension_agent",
                preferred_language="en",
                is_active=True,
            )
            agent.set_password("TestPassword123!")

            admin = User(
                phone_number=ADMIN_PHONE,
                full_name="Component 6 Admin",
                role="admin",
                preferred_language="en",
                is_active=True,
            )
            admin.set_password("TestPassword123!")

            db.session.add_all(
                [farmer1, farmer2, agent, admin]
            )
            db.session.commit()

            farmer1_id = farmer1.id
            farmer2_id = farmer2.id
            agent_id = agent.id
            admin_id = admin.id

            farmer1_profile = FarmerProfile(
                user_id=farmer1_id,
                region="Amhara",
                woreda="Bahir Dar Zuria",
                kebele="Test Kebele",
                latitude=11.5742,
                longitude=37.3614,
                sms_opt_in=False,
            )

            farmer2_profile = FarmerProfile(
                user_id=farmer2_id,
                region="Oromia",
                woreda="Other Woreda",
                kebele="Other Kebele",
                latitude=9.0,
                longitude=38.0,
                sms_opt_in=False,
            )

            db.session.add_all(
                [farmer1_profile, farmer2_profile]
            )

            diagnosis1 = DiagnosisRecord(
                user_id=farmer1_id,
                disease_class="Blight",
                confidence=0.91,
                model_name="MobileNetV2",
                model_version="component6_test",
                prediction_time=0.25,
                explainability_requested=False,
            )

            diagnosis2 = DiagnosisRecord(
                user_id=farmer2_id,
                disease_class="Common_Rust",
                confidence=0.88,
                model_name="MobileNetV2",
                model_version="component6_test",
                prediction_time=0.25,
                explainability_requested=False,
            )

            db.session.add_all(
                [diagnosis1, diagnosis2]
            )
            db.session.commit()

            diagnosis1_id = diagnosis1.id
            diagnosis2_id = diagnosis2.id

        farmer1_headers = {
            "Authorization": (
                f"Bearer {make_token(app, farmer1_id, 'farmer')}"
            )
        }

        farmer2_headers = {
            "Authorization": (
                f"Bearer {make_token(app, farmer2_id, 'farmer')}"
            )
        }

        agent_headers = {
            "Authorization": (
                f"Bearer {make_token(app, agent_id, 'extension_agent')}"
            )
        }

        admin_headers = {
            "Authorization": (
                f"Bearer {make_token(app, admin_id, 'admin')}"
            )
        }

        response = client.get(
            "/api/discussion/posts",
        )
        assert_error(response, 401)

        response = client.post(
            "/api/discussion/posts",
            headers=farmer1_headers,
            json={
                "post_type": "question",
                "title": "Why are maize leaves turning yellow?",
                "content": "My maize leaves are becoming yellow.",
                "diagnosis_id": diagnosis1_id,
            },
        )

        data = assert_success(response, 201)
        question_id = data["id"]

        with app.app_context():
            question = db.session.get(
                DiscussionPost,
                question_id,
            )
            assert question.author_id == farmer1_id

        response = client.post(
            "/api/discussion/posts",
            headers=agent_headers,
            json={
                "post_type": "question",
                "title": "Invalid question",
                "content": "This should fail.",
            },
        )
        assert_error(response, 403)

        response = client.post(
            "/api/discussion/posts",
            headers=agent_headers,
            json={
                "post_type": "advisory",
                "title": "Northern Leaf Blight Advisory",
                "content": "Inspect maize fields for disease symptoms.",
                "target_region": "Amhara",
                "target_woreda": "Bahir Dar Zuria",
                "target_kebele": "Test Kebele",
                "priority": "important",
                "diagnosis_id": diagnosis1_id,
            },
        )

        data = assert_success(response, 201)
        advisory_id = data["id"]

        response = client.post(
            "/api/discussion/posts",
            headers=agent_headers,
            json={
                "post_type": "announcement",
                "title": "Farmer Training Announcement",
                "content": "A maize training will be held next week.",
                "target_region": "Amhara",
            },
        )

        data = assert_success(response, 201)
        announcement_id = data["id"]

        response = client.post(
            "/api/discussion/posts",
            headers=agent_headers,
            json={
                "post_type": "alert",
                "title": "Urgent Disease Alert",
                "content": "Disease symptoms have been reported.",
                "target_region": "Amhara",
                "target_woreda": "Bahir Dar Zuria",
                "priority": "urgent",
            },
        )

        data = assert_success(response, 201)
        alert_id = data["id"]

        response = client.post(
            "/api/discussion/posts",
            headers=agent_headers,
            json={
                "post_type": "announcement",
                "title": "General Agriculture Announcement",
                "content": "General maize farming information.",
            },
        )

        data = assert_success(response, 201)
        general_id = data["id"]

        response = client.get(
            "/api/discussion/posts",
            headers=farmer1_headers,
        )

        farmer1_posts = extract_post_list(
            assert_success(response)
        )
        farmer1_ids = get_post_ids(farmer1_posts)

        assert question_id in farmer1_ids
        assert advisory_id in farmer1_ids
        assert announcement_id in farmer1_ids
        assert alert_id in farmer1_ids
        assert general_id in farmer1_ids

        response = client.get(
            "/api/discussion/posts",
            headers=farmer2_headers,
        )

        farmer2_posts = extract_post_list(
            assert_success(response)
        )
        farmer2_ids = get_post_ids(farmer2_posts)

        assert question_id in farmer2_ids
        assert advisory_id not in farmer2_ids
        assert announcement_id not in farmer2_ids
        assert alert_id not in farmer2_ids
        assert general_id in farmer2_ids

        response = client.get(
            "/api/discussion/posts",
            headers=agent_headers,
        )

        agent_posts = extract_post_list(
            assert_success(response)
        )
        agent_ids = get_post_ids(agent_posts)

        assert question_id in agent_ids
        assert advisory_id in agent_ids
        assert announcement_id in agent_ids
        assert alert_id in agent_ids
        assert general_id in agent_ids

        response = client.get(
            "/api/discussion/posts",
            headers=farmer1_headers,
            query_string={"search": "Northern Leaf Blight"},
        )

        search_posts = extract_post_list(
            assert_success(response)
        )

        assert advisory_id in get_post_ids(search_posts)

        response = client.get(
            "/api/discussion/posts",
            headers=farmer1_headers,
            query_string={"post_type": "advisory"},
        )

        advisory_posts = extract_post_list(
            assert_success(response)
        )

        assert advisory_posts

        for post in advisory_posts:
            assert post["post_type"] == "advisory"

        response = client.post(
            f"/api/discussion/posts/{question_id}/replies",
            headers=farmer2_headers,
            json={
                "content": "I have noticed the same problem.",
            },
        )

        data = assert_success(response, 201)
        farmer_reply_id = data["id"]

        response = client.post(
            f"/api/discussion/posts/{question_id}/replies",
            headers=agent_headers,
            json={
                "content": "Please inspect the affected leaves.",
            },
        )

        data = assert_success(response, 201)
        extension_reply_id = data["id"]

        response = client.get(
            f"/api/discussion/posts/{question_id}",
            headers=farmer1_headers,
        )

        detail = assert_success(response)

        assert detail["id"] == question_id

        reply_ids = {
            int(reply["id"])
            for reply in detail.get("replies", [])
            if "id" in reply
        }

        assert farmer_reply_id in reply_ids
        assert extension_reply_id in reply_ids

        response = client.get(
            f"/api/discussion/posts/{advisory_id}",
            headers=farmer2_headers,
        )
        assert_error(response, 403)

        response = client.post(
            "/api/discussion/posts",
            headers=farmer1_headers,
            json={
                "post_type": "question",
                "title": "Cross user diagnosis",
                "content": "This should fail.",
                "diagnosis_id": diagnosis2_id,
            },
        )
        assert_error(response, 403)

        response = client.post(
            "/api/discussion/posts",
            headers=farmer1_headers,
            json={
                "post_type": "question",
                "title": "Invalid diagnosis",
                "content": "This should fail.",
                "diagnosis_id": 999999999,
            },
        )
        assert_error(response, 404)

        response = client.post(
            "/api/discussion/posts",
            headers=farmer1_headers,
            json={
                "post_type": "advisory",
                "title": "Invalid advisory",
                "content": "This should fail.",
            },
        )
        assert_error(response, 403)

        response = client.post(
            "/api/discussion/posts",
            headers=agent_headers,
            json={
                "post_type": "announcement",
                "title": "Invalid priority",
                "content": "This should fail.",
                "priority": "critical",
            },
        )
        assert_error(response, 400)

        response = client.post(
            "/api/discussion/posts",
            headers=agent_headers,
            json={
                "post_type": "announcement",
                "title": "Invalid location",
                "content": "This should fail.",
                "target_woreda": "Bahir Dar Zuria",
            },
        )
        assert_error(response, 400)

        response = client.get(
            "/api/discussion/posts/999999999",
            headers=farmer1_headers,
        )
        assert_error(response, 404)

        response = client.get(
            "/api/discussion/posts",
            headers=admin_headers,
        )
        assert_success(response)

        response = client.post(
            f"/api/discussion/posts/{question_id}/like",
            headers=farmer1_headers,
        )
        data = assert_success(response)
        assert data["liked"] is True
        assert data["likes_count"] == 1

        response = client.post(
            f"/api/discussion/posts/{question_id}/like",
            headers=farmer1_headers,
        )
        data = assert_success(response)
        assert data["likes_count"] == 1

        response = client.delete(
            f"/api/discussion/posts/{question_id}/like",
            headers=farmer1_headers,
        )
        data = assert_success(response)
        assert data["liked"] is False
        assert data["likes_count"] == 0

        response = client.patch(
            f"/api/discussion/posts/{question_id}",
            headers=farmer1_headers,
            json={"title": "Updated community question"},
        )
        assert_success(response)

        response = client.patch(
            f"/api/discussion/posts/{question_id}",
            headers=farmer2_headers,
            json={"title": "Unauthorized edit"},
        )
        assert_error(response, 403)

        with app.app_context():
            post = db.session.get(
                DiscussionPost,
                advisory_id,
            )

            assert post.author_id == agent_id
            assert post.target_region == "Amhara"
            assert post.target_woreda == "Bahir Dar Zuria"
            assert post.target_kebele == "Test Kebele"
            assert post.priority == "important"

            alert = db.session.get(
                DiscussionPost,
                alert_id,
            )

            assert alert.priority == "urgent"

            farmer_reply = db.session.get(
                DiscussionReply,
                farmer_reply_id,
            )

            assert farmer_reply.farmer_id == farmer2_id
            assert farmer_reply.extension_agent_id is None

            extension_reply = db.session.get(
                DiscussionReply,
                extension_reply_id,
            )

            assert extension_reply.extension_agent_id == agent_id
            assert extension_reply.farmer_id is None

            question = db.session.get(
                DiscussionPost,
                question_id,
            )

            db.session.delete(question)
            db.session.commit()

            assert db.session.get(
                DiscussionPost,
                question_id,
            ) is None

            assert db.session.get(
                DiscussionReply,
                farmer_reply_id,
            ) is None

            assert db.session.get(
                DiscussionReply,
                extension_reply_id,
            ) is None

        print("\nCOMPONENT 6: ALL TESTS PASSED")
        print("Discussion & Agricultural Communication System: COMPLETE")

    finally:
        cleanup_test_data(app)


if __name__ == "__main__":
    main()
