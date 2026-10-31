from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Handoff


def get_handoff_by_session(session: Session, *, session_id: int) -> Handoff | None:
    return session.scalar(select(Handoff).where(Handoff.session_id == session_id))


def list_pending_handoffs(session: Session) -> list[Handoff]:
    statement = (
        select(Handoff).where(Handoff.status == "pending").order_by(Handoff.created_at, Handoff.id)
    )
    return list(session.scalars(statement))
