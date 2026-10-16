def test_jwt_access_token_expiration(app):
    assert app.config["JWT_ACCESS_TOKEN_EXPIRES"] == 900


def test_max_upload_size(app):
    assert app.config["MAX_CONTENT_LENGTH"] == 5 * 1024 * 1024
