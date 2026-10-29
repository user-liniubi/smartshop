import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.app.api.dependencies import AgentUser
from backend.app.api.rag_dependencies import get_knowledge_service
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import AppError
from backend.app.rag.parsing import SUPPORTED_EXTENSIONS
from backend.app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeUploadResponse,
)
from backend.app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/upload", response_model=KnowledgeUploadResponse)
def upload_document(
    current_agent: AgentUser,
    file: Annotated[UploadFile, File()],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    product_id: Annotated[int | None, Form(gt=0)] = None,
) -> KnowledgeUploadResponse:
    """Upload and synchronously index one knowledge document."""

    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in SUPPORTED_EXTENSIONS:
        raise AppError(
            status_code=400,
            code="unsupported_document_type",
            message="仅支持 Markdown、TXT 和 PDF 文件",
        )

    payload = file.file.read(settings.max_upload_bytes + 1)
    file.file.close()
    if len(payload) > settings.max_upload_bytes:
        raise AppError(
            status_code=413,
            code="document_too_large",
            message="知识文件超过大小限制",
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    content_hash = hashlib.sha256(payload).hexdigest()[:16]
    target_path = settings.upload_dir / f"{Path(filename).stem}-{content_hash}{suffix}"
    target_path.write_bytes(payload)

    try:
        result = service.ingest_file(
            path=target_path,
            original_filename=filename,
            product_id=product_id,
        )
        if result.duplicate:
            target_path.unlink(missing_ok=True)
        return result
    except Exception:
        target_path.unlink(missing_ok=True)
        raise


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
def list_documents(
    current_agent: AgentUser,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> list[KnowledgeDocumentResponse]:
    return [
        KnowledgeDocumentResponse.model_validate(document) for document in service.list_documents()
    ]
