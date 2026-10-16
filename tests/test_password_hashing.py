from backend.app.models import User


def test_password_is_bcrypt_hashed():
    user = User()
    password = "TestPassword123!"

    user.set_password(password)

    assert user.password_hash
    assert user.password_hash != password
    assert user.password_hash.startswith("$2")
    assert user.check_password(password) is True


def test_wrong_password_is_rejected():
    user = User()
    user.set_password("CorrectPassword123!")

    assert user.check_password("WrongPassword123!") is False


def test_password_hash_is_salted():
    user_one = User()
    user_two = User()
    password = "SamePassword123!"

    user_one.set_password(password)
    user_two.set_password(password)

    assert user_one.password_hash != user_two.password_hash
    assert user_one.check_password(password) is True
    assert user_two.check_password(password) is True
