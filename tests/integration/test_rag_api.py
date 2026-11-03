from backend.app.api.rag_dependencies import get_rag_service
from backend.app.main import app
from backend.app.schemas.rag import CitationResponse, RagAskResponse
from sample_data.seed import DEMO_PASSWORD


class FakeRagService:
    async def ask(self, *, question: str, product_id=None, top_k=None):
        return RagAskResponse(
            answer="降噪耳机提供十二个月质保。[1]",
            grounded=True,
            citations=[
                CitationResponse(
                    document_id=2,
                    chunk_id="[1] 2:0",
                    filename="warranty_policy.md",
                    title="质保规则",
                    heading="各品类期限",
                    excerpt="降噪耳机提供十二个月质保。",
                    similarity=0.88,
                )
            ],
            model="deepseek-chat",
        )


def test_rag_api_returns_answer_with_citation(seeded_client):
    app.dependency_overrides[get_rag_service] = lambda: FakeRagService()
    login = seeded_client.post(
        "/auth/login",
        json={"username": "consumer_demo", "password": DEMO_PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = seeded_client.post(
        "/api/v1/rag/ask",
        headers=headers,
        json={"question": "降噪耳机保修多久？", "product_id": 1},
    )

    assert response.status_code == 200
    assert response.json()["grounded"] is True
    assert response.json()["citations"][0]["filename"] == "warranty_policy.md"


def test_rag_api_requires_login(seeded_client):
    response = seeded_client.post(
        "/api/v1/rag/ask",
        json={"question": "耳机保修多久？"},
    )

    assert response.status_code == 401
