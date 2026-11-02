from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.models import ChatSession, Handoff, User
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


def test_atomic_claim_reply_and_close(seeded_client, test_database):
    with test_database.session_factory() as session:
        session.add(
            User(
                username="agent_two",
                password_hash=hash_password("AgentTwo123!"),
                role="agent",
            )
        )
        session.commit()

    consumer_headers = login_headers(
        seeded_client,
        "consumer_demo",
        DEMO_PASSWORD,
    )
    first_agent_headers = login_headers(
        seeded_client,
        "agent_demo",
        AGENT_PASSWORD,
    )
    second_agent_headers = login_headers(
        seeded_client,
        "agent_two",
        "AgentTwo123!",
    )
    chat_session = seeded_client.post(
        "/chat/sessions",
        headers=consumer_headers,
    ).json()
    handoff = seeded_client.post(
        f"/chat/sessions/{chat_session['id']}/handoff",
        headers=consumer_headers,
        json={"reason": "需要人工处理"},
    ).json()

    first_claim = seeded_client.post(
        f"/agent/handoffs/{handoff['id']}/claim",
        headers=first_agent_headers,
    )
    second_claim = seeded_client.post(
        f"/agent/handoffs/{handoff['id']}/claim",
        headers=second_agent_headers,
    )
    context = seeded_client.get(
        f"/agent/sessions/{chat_session['id']}",
        headers=first_agent_headers,
    )
    other_context = seeded_client.get(
        f"/agent/sessions/{chat_session['id']}",
        headers=second_agent_headers,
    )
    other_reply = seeded_client.post(
        f"/agent/sessions/{chat_session['id']}/reply",
        headers=second_agent_headers,
        json={"content": "越权回复"},
    )
    reply = seeded_client.post(
        f"/agent/sessions/{chat_session['id']}/reply",
        headers=first_agent_headers,
        json={"content": "已收到，我来帮你核实。"},
    )
    history = seeded_client.get(
        f"/chat/sessions/{chat_session['id']}/messages",
        headers=consumer_headers,
    )
    closed = seeded_client.post(
        f"/agent/sessions/{chat_session['id']}/close",
        headers=first_agent_headers,
    )
    reply_after_close = seeded_client.post(
        f"/agent/sessions/{chat_session['id']}/reply",
        headers=first_agent_headers,
        json={"content": "关闭后的回复"},
    )

    assert first_claim.status_code == 200
    assert first_claim.json()["status"] == "claimed"
    assert first_claim.json()["claimed_at"] is not None
    assert second_claim.status_code == 409
    assert second_claim.json()["error"]["code"] == "handoff_already_claimed"
    assert context.status_code == 200
    assert context.json()["session"]["status"] == "human_active"
    assert other_context.status_code == 403
    assert other_reply.status_code == 403
    assert reply.status_code == 200
    assert history.status_code == 200
    assert history.json()[-1]["sender_type"] == "agent"
    assert history.json()[-1]["content"] == "已收到，我来帮你核实。"
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert closed.json()["closed_at"] is not None
    assert reply_after_close.status_code == 409
    assert reply_after_close.json()["error"]["code"] == "handoff_closed"
