import logging
from pathlib import Path

from sqlalchemy.exc import OperationalError

from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError
from backend.app.db.session import Database
from backend.app.models import IngestionJobStatus
from backend.app.rag.embeddings import BgeEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.repositories.ingestion_jobs import get_ingestion_job
from backend.app.services.knowledge import KnowledgeService
from backend.app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="smartshop.ingest_document",
    max_retries=2,
)
def ingest_document_task(self, task_id: str) -> dict:
    settings = get_settings()
    database = Database(settings.database_url, echo=settings.database_echo)

    try:
        with database.session_factory() as session:
            job = get_ingestion_job(session, task_id=task_id)
            if job is None:
                return {"task_id": task_id, "status": "missing"}
            if job.status == IngestionJobStatus.SUCCESS.value:
                return {
                    "task_id": task_id,
                    "status": job.status,
                    "document_id": job.document_id,
                }

            job.status = IngestionJobStatus.STARTED.value
            job.progress = 10
            session.commit()

            try:
                job.progress = 30
                session.commit()
                service = KnowledgeService(
                    session=session,
                    settings=settings,
                    embedder=BgeEmbeddingProvider(
                        settings.embedding_model,
                        settings.embedding_device,
                        local_files_only=settings.embedding_local_files_only,
                    ),
                    vector_store=ChromaVectorStore(settings.chroma_path),
                )
                result = service.ingest_file(
                    path=Path(job.source_path),
                    original_filename=job.filename,
                    product_id=job.product_id,
                )
                job = get_ingestion_job(session, task_id=task_id)
                if job is None:
                    return {"task_id": task_id, "status": "missing"}
                job.status = IngestionJobStatus.SUCCESS.value
                job.progress = 100
                job.document_id = result.document.id
                job.error_message = None
                session.commit()
            except OperationalError as exc:
                session.rollback()
                job = get_ingestion_job(session, task_id=task_id)
                if job is not None:
                    job.status = IngestionJobStatus.PENDING.value
                    job.progress = 0
                    job.error_message = "临时数据库错误，等待重试"
                    session.commit()
                raise self.retry(exc=exc, countdown=5) from None
            except AppError as exc:
                session.rollback()
                job = get_ingestion_job(session, task_id=task_id)
                if job is not None:
                    job.status = IngestionJobStatus.FAILURE.value
                    job.error_message = exc.message[:500]
                    session.commit()
            except Exception:
                session.rollback()
                logger.exception("Async ingestion failed task_id=%s", task_id)
                job = get_ingestion_job(session, task_id=task_id)
                if job is not None:
                    job.status = IngestionJobStatus.FAILURE.value
                    job.error_message = "文档索引失败，请检查文件后重试"
                    session.commit()

            job = get_ingestion_job(session, task_id=task_id)
            return {
                "task_id": task_id,
                "status": job.status if job else "missing",
                "document_id": job.document_id if job else None,
            }
    finally:
        database.dispose()
