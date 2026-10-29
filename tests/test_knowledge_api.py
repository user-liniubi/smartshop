from backend.app.api.rag_dependencies import get_embedding_provider, get_vector_store
from backend.app.core.config import Settings, get_settings
from backend.app.main import app
from backend.app.rag.vector_store import VectorChunk
from sample_data.seed import AGENT_PASSWORD


class FakeEmbedder:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserted: list[VectorChunk] = []

    def upsert(self, chunks: list[VectorChunk], embeddings: list[list[float]]) -> None:
        assert len(chunks) == len(embeddings)
        self.upserted.extend(chunks)

    def delete(self, vector_ids: list[str]) -> None:
        pass


def test_agent_can_upload_list_and_deduplicate_knowledge(
    seeded_client,
    tmp_path,
):
    settings = Settings(
        _env_file=None,
        app_env="test",
        upload_dir=tmp_path / "uploads",
        chroma_path=tmp_path / "chroma",
        auth_secret="test-agent-secret-with-at-least-32-chars",
        rag_chunk_size=200,
        rag_chunk_overlap=20,
    )
    vector_store = FakeVectorStore()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbedder()
    app.dependency_overrides[get_vector_store] = lambda: vector_store

    try:
        login = seeded_client.post(
            "/auth/login",
            json={"username": "agent_demo", "password": AGENT_PASSWORD},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        payload = "# 耳机 FAQ\n\n## 质保\n\n耳机质保十二个月。".encode()

        first = seeded_client.post(
            "/knowledge/upload",
            headers=headers,
            files={"file": ("faq.md", payload, "text/markdown")},
        )
        duplicate = seeded_client.post(
            "/knowledge/upload",
            headers=headers,
            files={"file": ("faq.md", payload, "text/markdown")},
        )
        documents = seeded_client.get("/knowledge/documents", headers=headers)

        assert first.status_code == 200
        assert first.json()["duplicate"] is False
        assert first.json()["chunk_count"] >= 1
        assert duplicate.status_code == 200
        assert duplicate.json()["duplicate"] is True
        assert documents.status_code == 200
        assert len(documents.json()) == 1
        assert len(vector_store.upserted) == first.json()["chunk_count"]
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_embedding_provider, None)
        app.dependency_overrides.pop(get_vector_store, None)
