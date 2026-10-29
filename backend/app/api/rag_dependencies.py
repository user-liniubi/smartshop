from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.db.session import get_db
from backend.app.rag.embeddings import BgeEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.services.knowledge import KnowledgeService
from backend.app.services.llm import DeepSeekClient
from backend.app.services.rag import RAGService


@lru_cache
def get_embedding_provider() -> BgeEmbeddingProvider:
    settings = get_settings()
    return BgeEmbeddingProvider(
        settings.embedding_model,
        settings.embedding_device,
        local_files_only=settings.embedding_local_files_only,
    )


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore(get_settings().chroma_path)


@lru_cache
def get_llm_client() -> DeepSeekClient:
    return DeepSeekClient(get_settings())


def get_rag_service(
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[BgeEmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
    llm: Annotated[DeepSeekClient, Depends(get_llm_client)],
) -> RAGService:
    return RAGService(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
        llm=llm,
    )


def get_knowledge_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[BgeEmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
) -> KnowledgeService:
    return KnowledgeService(
        session=session,
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
    )
