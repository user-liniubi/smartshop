from sample_data.seed import DEMO_PASSWORD


def test_login_returns_signed_token_and_user(seeded_client):
    response = seeded_client.post(
        "/auth/login",
        json={"username": "consumer_demo", "password": DEMO_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"].count(".") == 1
    assert body["user"]["id"] > 0
    assert body["user"]["username"] == "consumer_demo"
    assert body["user"]["role"] == "consumer"


def test_login_rejects_wrong_password_and_unknown_user_with_same_error(seeded_client):
    wrong_password = seeded_client.post(
        "/auth/login",
        json={"username": "consumer_demo", "password": "Wrong123!"},
    )
    unknown_user = seeded_client.post(
        "/auth/login",
        json={"username": "missing_user", "password": "Wrong123!"},
    )

    expected = {
        "error": {
            "code": "invalid_credentials",
            "message": "用户名或密码错误",
        }
    }
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == expected


def test_login_validates_request_body(client):
    response = client.post(
        "/auth/login",
        json={"username": "x", "password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
