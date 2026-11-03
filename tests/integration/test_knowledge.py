from sqlalchemy import func, select

from backend.app.core.config import Settings
from backend.app.db.session import Database
from backend.app.models import Base, Document, DocumentChunk, Product
from backend.app.rag.vector_store import VectorChunk
from backend.app.services.knowledge import KnowledgeService
from sample_data.seed import seed_demo_data


class FakeEmbedder:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(index + 1), 0.5, 0.25] for index, _ in enumerate(texts)]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserted: list[VectorChunk] = []
        self.deleted: list[str] = []

    def upsert(
        self,
        chunks: list[VectorChunk],
        embeddings: list[list[float]],
    ) -> None:
        assert len(chunks) == len(embeddings)
        self.upserted.extend(chunks)

    def delete(self, vector_ids: list[str]) -> None:
        self.deleted.extend(vector_ids)


def test_knowledge_service_indexes_and_deduplicates_document(tmp_path):
    test_database = Database("sqlite+pysqlite:///:memory:")
    with test_database.engine.begin() as connection:
        Base.metadata.create_all(connection)

    document_path = tmp_path / "warranty.md"
    document_path.write_text(
        "# 质保规则\n\n## 耳机\n\n降噪耳机提供十二个月质保。",
        encoding="utf-8",
    )
    settings = Settings(
        _env_file=None,
        upload_dir=tmp_path / "uploads",
        chroma_path=tmp_path / "chroma",
        rag_chunk_size=100,
        rag_chunk_overlap=10,
    )
    vector_store = FakeVectorStore()

    with test_database.session_factory() as session:
        seed_demo_data(session)
        headphones = session.scalar(select(Product).where(Product.name == "SmartShop 降噪耳机 Pro"))
        assert headphones is not None
        service = KnowledgeService(
            session=session,
            settings=settings,
            embedder=FakeEmbedder(),
            vector_store=vector_store,
        )

        first = service.ingest_file(
            path=document_path,
            original_filename="warranty.md",
            product_id=headphones.id,
        )
        duplicate = service.ingest_file(
            path=document_path,
            original_filename="warranty.md",
            product_id=headphones.id,
        )

        assert first.duplicate is False
        assert first.chunk_count >= 1
        assert duplicate.duplicate is True
        assert duplicate.document.id == first.document.id
        assert len(vector_store.upserted) == first.chunk_count
        assert session.scalar(select(func.count()).select_from(Document)) == 1
        assert session.scalar(select(func.count()).select_from(DocumentChunk)) == first.chunk_count

    test_database.dispose()


def test_knowledge_upload_requires_agent_role(seeded_client):
    consumer_login = seeded_client.post(
        "/auth/login",
        json={"username": "consumer_demo", "password": "Demo123!"},
    )
    response = seeded_client.post(
        "/knowledge/upload",
        headers={"Authorization": f"Bearer {consumer_login.json()['access_token']}"},
        files={"file": ("faq.md", b"# FAQ\n\ncontent", "text/markdown")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "agent_role_required"
