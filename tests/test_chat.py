from backend.app.api.rag_dependencies import get_rag_service
from backend.app.main import app
from backend.app.schemas.rag import CitationResponse, RagAskResponse
from sample_data.seed import DEMO_PASSWORD


class FakeRagService:
    async def ask(self, *, question: str, product_id=None, top_k=None):
        return RagAskResponse(
            answer="耳机质保十二个月。[1]",
            grounded=True,
            citations=[
                CitationResponse(
                    document_id=1,
                    chunk_id="[1] 1:1",
                    filename="warranty_policy.md",
                    title="质保规则",
                    heading="耳机",
                    excerpt="降噪耳机提供十二个月质保。",
                    similarity=0.92,
                )
            ],
            model="deepseek-chat",
        )


def _login_headers(client, username: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_chat_messages_are_persisted_with_citations(seeded_client):
    app.dependency_overrides[get_rag_service] = lambda: FakeRagService()
    headers = _login_headers(seeded_client, "consumer_demo")

    created = seeded_client.post("/chat/sessions", headers=headers)
    assert created.status_code == 200
    session_id = created.json()["id"]

    sent = seeded_client.post(
        f"/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"content": "耳机保修多久？"},
    )
    history = seeded_client.get(
        f"/chat/sessions/{session_id}/messages",
        headers=headers,
    )

    assert sent.status_code == 200
    assert sent.json()["user_message"]["sender_type"] == "consumer"
    assert sent.json()["assistant_message"]["sender_type"] == "assistant"
    assert sent.json()["assistant_message"]["citations_json"][0]["filename"] == (
        "warranty_policy.md"
    )
    assert history.status_code == 200
    assert [message["sender_type"] for message in history.json()] == [
        "consumer",
        "assistant",
    ]


def test_consumer_cannot_read_another_users_chat(seeded_client):
    app.dependency_overrides[get_rag_service] = lambda: FakeRagService()
    owner_headers = _login_headers(seeded_client, "consumer_demo")
    other_headers = _login_headers(seeded_client, "consumer_other")

    created = seeded_client.post("/chat/sessions", headers=owner_headers)
    session_id = created.json()["id"]
    response = seeded_client.get(
        f"/chat/sessions/{session_id}/messages",
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "chat_session_not_found"
