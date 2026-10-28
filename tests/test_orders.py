from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token
from backend.app.models import Order, User
from sample_data.seed import DEMO_PASSWORD


def login_headers(client, username: str = "consumer_demo") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def get_order_id(test_database, order_no: str) -> int:
    with test_database.session_factory() as session:
        order = session.scalar(select(Order).where(Order.order_no == order_no))
        assert order is not None
        return order.id


def test_consumer_can_read_own_order(seeded_client, test_database):
    order_id = get_order_id(test_database, "A10086")
    response = seeded_client.get(
        f"/orders/{order_id}",
        headers=login_headers(seeded_client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["order_no"] == "A10086"
    assert body["status"] == "delivered"
    assert body["product"]["name"] == "SmartShop 降噪耳机 Pro"


def test_consumer_cannot_read_another_users_order(seeded_client, test_database):
    other_user_order_id = get_order_id(test_database, "A10088")
    response = seeded_client.get(
        f"/orders/{other_user_order_id}",
        headers=login_headers(seeded_client, "consumer_demo"),
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "order_not_found",
            "message": "订单不存在",
        }
    }


def test_order_query_requires_valid_token(seeded_client, test_database):
    order_id = get_order_id(test_database, "A10086")
    missing = seeded_client.get(f"/orders/{order_id}")
    invalid = seeded_client.get(
        f"/orders/{order_id}",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_token"


def test_tampered_or_expired_token_is_rejected(seeded_client, test_database):
    settings = get_settings()
    order_id = get_order_id(test_database, "A10086")

    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        assert user is not None
        user_id = user.id
        role = user.role

    valid_token = create_access_token(
        user_id=user_id,
        role=role,
        secret=settings.auth_secret,
        expires_minutes=60,
    )
    payload, signature = valid_token.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    tampered_token = f"{payload}.{replacement}{signature[1:]}"
    expired_token = create_access_token(
        user_id=user_id,
        role=role,
        secret=settings.auth_secret,
        expires_minutes=60,
        now=datetime.now(UTC) - timedelta(hours=2),
    )

    tampered = seeded_client.get(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    expired = seeded_client.get(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert tampered.status_code == 401
    assert expired.status_code == 401


def test_order_id_must_be_positive(seeded_client):
    response = seeded_client.get(
        "/orders/0",
        headers=login_headers(seeded_client),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
