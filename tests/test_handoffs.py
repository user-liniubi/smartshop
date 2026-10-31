from sqlalchemy import select

from backend.app.models import ChatSession, Handoff
from sample_data.seed import AGENT_PASSWORD, DEMO_PASSWORD


def login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_handoff_request_is_idempotent_and_visible_to_agent(
    seeded_client,
    test_database,
):
    consumer_headers = login_headers(
        seeded_client,
        "consumer_demo",
        DEMO_PASSWORD,
    )
    agent_headers = login_headers(
        seeded_client,
        "agent_demo",
        AGENT_PASSWORD,
    )
    created_session = seeded_client.post("/chat/sessions", headers=consumer_headers)
    session_id = created_session.json()["id"]

    first = seeded_client.post(
        f"/chat/sessions/{session_id}/handoff",
        headers=consumer_headers,
        json={"reason": "需要人工判断"},
    )
    second = seeded_client.post(
        f"/chat/sessions/{session_id}/handoff",
        headers=consumer_headers,
        json={"reason": "再次申请"},
    )
    queue = seeded_client.get("/agent/handoffs", headers=agent_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["source"] == "user"
    assert queue.status_code == 200
    assert len(queue.json()) == 1
    with test_database.session_factory() as session:
        chat_session = session.get(ChatSession, session_id)
        handoff = session.scalar(select(Handoff))
    assert chat_session is not None
    assert chat_session.status == "need_human"
    assert handoff is not None


def test_handoff_permissions(seeded_client, test_database):
    owner_headers = login_headers(
        seeded_client,
        "consumer_demo",
        DEMO_PASSWORD,
    )
    other_headers = login_headers(
        seeded_client,
        "consumer_other",
        DEMO_PASSWORD,
    )
    agent_headers = login_headers(
        seeded_client,
        "agent_demo",
        AGENT_PASSWORD,
    )
    created_session = seeded_client.post("/chat/sessions", headers=owner_headers)
    session_id = created_session.json()["id"]

    other_request = seeded_client.post(
        f"/chat/sessions/{session_id}/handoff",
        headers=other_headers,
        json={"reason": "越权申请"},
    )
    consumer_queue = seeded_client.get(
        "/agent/handoffs",
        headers=owner_headers,
    )
    agent_request = seeded_client.post(
        f"/chat/sessions/{session_id}/handoff",
        headers=agent_headers,
        json={"reason": "客服申请"},
    )

    assert other_request.status_code == 404
    assert consumer_queue.status_code == 403
    assert agent_request.status_code == 403
