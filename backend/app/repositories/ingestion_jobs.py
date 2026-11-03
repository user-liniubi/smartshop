from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import IngestionJob


def create_ingestion_job(
    session: Session,
    *,
    task_id: str,
    filename: str,
    source_path: str,
    product_id: int | None,
) -> IngestionJob:
    job = IngestionJob(
        task_id=task_id,
        filename=filename,
        source_path=source_path,
        product_id=product_id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_ingestion_job(session: Session, *, task_id: str) -> IngestionJob | None:
    return session.scalar(select(IngestionJob).where(IngestionJob.task_id == task_id))
