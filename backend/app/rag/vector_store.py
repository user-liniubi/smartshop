from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

COLLECTION_NAME = "knowledge_chunks"


@dataclass(frozen=True)
class VectorChunk:
    vector_id: str
    content: str
    document_id: int
    chunk_index: int
    filename: str
    title: str
    product_id: int | None
    page: int | None
    heading: str | None


@dataclass(frozen=True)
class RetrievedChunk:
    vector_id: str
    content: str
    document_id: int
    chunk_index: int
    filename: str
    title: str
    page: int | None
    heading: str | None
    similarity: float


class ChromaVectorStore:
    """Persistent Chroma collection for knowledge chunks."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.path))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        chunks: list[VectorChunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return

        self._collection.upsert(
            ids=[chunk.vector_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.content for chunk in chunks],
            metadatas=[
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "filename": chunk.filename,
                    "title": chunk.title,
                    "product_id": chunk.product_id or 0,
                    "page": chunk.page or 0,
                    "heading": chunk.heading or "",
                }
                for chunk in chunks
            ],
        )

    def query(
        self,
        embedding: list[float],
        *,
        top_k: int,
        product_id: int | None = None,
    ) -> list[RetrievedChunk]:
        where: dict[str, Any] | None = None
        if product_id is not None:
            where = {"product_id": {"$in": [product_id, 0]}}

        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0]

        retrieved: list[RetrievedChunk] = []
        for vector_id, content, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=True,
        ):
            retrieved.append(
                RetrievedChunk(
                    vector_id=vector_id,
                    content=content or "",
                    document_id=int(metadata["document_id"]),
                    chunk_index=int(metadata["chunk_index"]),
                    filename=str(metadata["filename"]),
                    title=str(metadata["title"]),
                    page=int(metadata["page"]) or None,
                    heading=str(metadata["heading"]) or None,
                    similarity=1.0 - float(distance),
                )
            )
        return retrieved

    def delete(self, vector_ids: list[str]) -> None:
        if vector_ids:
            self._collection.delete(ids=vector_ids)
