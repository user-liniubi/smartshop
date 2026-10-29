from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.db.session import Database
from backend.app.models import Product
from backend.app.rag.embeddings import BgeEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.services.knowledge import KnowledgeService
from sample_data.knowledge_documents import DEMO_KNOWLEDGE_DOCUMENTS


def main() -> None:
    settings = get_settings()
    database = Database(settings.database_url, echo=settings.database_echo)
    embedder = BgeEmbeddingProvider(
        settings.embedding_model,
        settings.embedding_device,
        local_files_only=settings.embedding_local_files_only,
    )
    vector_store = ChromaVectorStore(settings.chroma_path)

    try:
        with database.session_factory() as session:
            product_ids = {product.name: product.id for product in session.scalars(select(Product))}
            service = KnowledgeService(
                session=session,
                settings=settings,
                embedder=embedder,
                vector_store=vector_store,
            )

            for demo_document in DEMO_KNOWLEDGE_DOCUMENTS:
                path = settings.knowledge_docs_dir / demo_document.filename
                product_id = (
                    product_ids.get(demo_document.product_name)
                    if demo_document.product_name
                    else None
                )
                result = service.ingest_file(
                    path=path,
                    original_filename=demo_document.filename,
                    product_id=product_id,
                )
                duplicate_marker = "duplicate" if result.duplicate else "indexed"
                print(f"{duplicate_marker}: {result.document.filename} chunks={result.chunk_count}")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
