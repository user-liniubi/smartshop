from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.models import ChatSession, Handoff, SessionStatus


def get_handoff_by_session(session: Session, *, session_id: int) -> Handoff | None:
    return session.scalar(select(Handoff).where(Handoff.session_id == session_id))


def list_pending_handoffs(session: Session) -> list[Handoff]:
    statement = (
        select(Handoff).where(Handoff.status == "pending").order_by(Handoff.created_at, Handoff.id)
    )
    return list(session.scalars(statement))


def list_agent_handoffs(session: Session, *, agent_id: int) -> list[Handoff]:
    statement = (
        select(Handoff)
        .where(
            Handoff.agent_id == agent_id,
            Handoff.status == "claimed",
        )
        .order_by(Handoff.claimed_at.desc(), Handoff.id.desc())
    )
    return list(session.scalars(statement))


def claim_handoff_atomic(
    session: Session,
    *,
    handoff_id: int,
    agent_id: int,
) -> Handoff | None:
    """Claim one pending handoff using a compare-and-set update."""

    now = datetime.now(UTC)
    result = session.execute(
        update(Handoff)
        .where(
            Handoff.id == handoff_id,
            Handoff.status == "pending",
        )
        .values(
            status="claimed",
            agent_id=agent_id,
            claimed_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.rollback()
        return None

    handoff = session.get(Handoff, handoff_id)
    if handoff is None:
        session.rollback()
        return None
    session.execute(
        update(ChatSession)
        .where(ChatSession.id == handoff.session_id)
        .values(status=SessionStatus.HUMAN_ACTIVE.value)
        .execution_options(synchronize_session=False)
    )
    session.commit()
    session.refresh(handoff)
    return handoff
