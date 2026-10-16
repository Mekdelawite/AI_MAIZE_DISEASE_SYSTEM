from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

from backend.app.routes.auth import roles_required


def create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["JWT_SECRET_KEY"] = "test-rbac-secret-key-for-pytest-2026"
    JWTManager(app)

    @app.get("/admin-only")
    @jwt_required()
    @roles_required("admin")
    def admin_only():
        return jsonify({"success": True, "role": "admin"})

    @app.get("/extension-only")
    @jwt_required()
    @roles_required("extension_agent")
    def extension_only():
        return jsonify({"success": True, "role": "extension_agent"})

    return app


def auth_header(app, role):
    with app.app_context():
        token = create_access_token(identity="1", additional_claims={"role": role})
    return {"Authorization": f"Bearer {token}"}


def test_rbac_allows_authorized_role():
    app = create_test_app()
    client = app.test_client()

    response = client.get(
        "/admin-only",
        headers=auth_header(app, "admin"),
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_rbac_blocks_unauthorized_role():
    app = create_test_app()
    client = app.test_client()

    response = client.get(
        "/admin-only",
        headers=auth_header(app, "farmer"),
    )

    assert response.status_code == 403
    data = response.get_json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_rbac_supports_extension_agent_role():
    app = create_test_app()
    client = app.test_client()

    response = client.get(
        "/extension-only",
        headers=auth_header(app, "extension_agent"),
    )

    assert response.status_code == 200
    assert response.get_json()["role"] == "extension_agent"


def test_rbac_is_case_and_whitespace_insensitive():
    app = create_test_app()
    client = app.test_client()

    response = client.get(
        "/admin-only",
        headers=auth_header(app, "  ADMIN  "),
    )

    assert response.status_code == 200
