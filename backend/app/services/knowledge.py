import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.exceptions import AppError
from backend.app.models import (
    Document,
    DocumentChunk,
    KnowledgeDocumentStatus,
    Product,
)
from backend.app.rag.chunking import chunk_sections
from backend.app.rag.embeddings import BgeEmbeddingProvider
from backend.app.rag.parsing import parse_document
from backend.app.rag.vector_store import ChromaVectorStore, VectorChunk
from backend.app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeUploadResponse,
)


class KnowledgeService:
    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        embedder: BgeEmbeddingProvider,
        vector_store: ChromaVectorStore,
    ) -> None:
        self.session = session
        self.settings = settings
        self.embedder = embedder
        self.vector_store = vector_store

    def ingest_file(
        self,
        *,
        path: Path,
        original_filename: str,
        product_id: int | None = None,
    ) -> KnowledgeUploadResponse:
        if not path.is_file():
            raise AppError(
                status_code=404,
                code="document_file_not_found",
                message="知识文件不存在",
            )

        size = path.stat().st_size
        if size > self.settings.max_upload_bytes:
            raise AppError(
                status_code=413,
                code="document_too_large",
                message="知识文件超过大小限制",
            )
        if product_id is not None and self.session.get(Product, product_id) is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message="关联商品不存在",
            )

        content_hash = self._sha256(path)
        existing = self.session.scalar(select(Document).where(Document.sha256 == content_hash))
        if existing is not None:
            return KnowledgeUploadResponse(
                document=KnowledgeDocumentResponse.model_validate(existing),
                chunk_count=len(existing.chunks),
                duplicate=True,
            )

        parsed = parse_document(path)
        chunks = chunk_sections(
            parsed.sections,
            chunk_size=self.settings.rag_chunk_size,
            overlap=self.settings.rag_chunk_overlap,
        )
        if not chunks:
            raise AppError(
                status_code=400,
                code="empty_document",
                message="知识文件没有可索引文本",
            )

        document = Document(
            product_id=product_id,
            filename=Path(original_filename).name,
            title=parsed.title,
            source_type=parsed.source_type,
            sha256=content_hash,
            status=KnowledgeDocumentStatus.PROCESSING.value,
            content_path=str(path),
        )
        self.session.add(document)
        self.session.flush()

        vector_chunks = [
            VectorChunk(
                vector_id=f"{document.id}:{chunk.chunk_index}",
                content=chunk.content,
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                filename=document.filename,
                title=document.title,
                product_id=product_id,
                page=chunk.page,
                heading=chunk.heading,
            )
            for chunk in chunks
        ]
        vector_ids = [chunk.vector_id for chunk in vector_chunks]

        try:
            embeddings = self.embedder.embed_documents([chunk.content for chunk in chunks])
            for chunk, vector_chunk in zip(chunks, vector_chunks, strict=True):
                self.session.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page,
                        heading=chunk.heading,
                        content=chunk.content,
                        text_hash=chunk.text_hash,
                        vector_id=vector_chunk.vector_id,
                    )
                )

            self.vector_store.upsert(vector_chunks, embeddings)
            document.status = KnowledgeDocumentStatus.INDEXED.value
            self.session.commit()
            self.session.refresh(document)
        except Exception as exc:
            self.session.rollback()
            self.vector_store.delete(vector_ids)
            if isinstance(exc, AppError):
                raise
            raise AppError(
                status_code=500,
                code="knowledge_index_failed",
                message="知识文件索引失败",
            ) from None

        return KnowledgeUploadResponse(
            document=KnowledgeDocumentResponse.model_validate(document),
            chunk_count=len(chunks),
            duplicate=False,
        )

    def list_documents(self) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document).order_by(Document.created_at.desc(), Document.id.desc())
            )
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
