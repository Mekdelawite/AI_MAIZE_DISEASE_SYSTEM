def test_testing_configuration(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"].endswith("/ai_maize_disease_test")
    assert not app.config["SQLALCHEMY_DATABASE_URI"].endswith("/ai_maize_disease")


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "running"
    assert data["backend"] == "Flask"
