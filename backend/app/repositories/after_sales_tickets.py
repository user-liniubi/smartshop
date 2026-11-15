from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.models import AfterSalesTicket
from backend.app.models.enums import AfterSalesTicketStatus


def get_ticket_by_session(
    session: Session,
    *,
    session_id: int,
) -> AfterSalesTicket | None:
    return session.scalar(select(AfterSalesTicket).where(AfterSalesTicket.session_id == session_id))


def list_user_tickets(
    session: Session,
    *,
    user_id: int,
) -> list[AfterSalesTicket]:
    statement = (
        select(AfterSalesTicket)
        .where(AfterSalesTicket.user_id == user_id)
        .order_by(AfterSalesTicket.created_at.desc(), AfterSalesTicket.id.desc())
    )
    return list(session.scalars(statement))


def list_pending_tickets(session: Session) -> list[AfterSalesTicket]:
    statement = (
        select(AfterSalesTicket)
        .where(AfterSalesTicket.status == AfterSalesTicketStatus.PENDING_APPROVAL.value)
        .order_by(AfterSalesTicket.created_at, AfterSalesTicket.id)
    )
    return list(session.scalars(statement))


def review_ticket_atomic(
    session: Session,
    *,
    ticket_id: int,
    reviewer_id: int,
    decision: AfterSalesTicketStatus,
    review_note: str,
) -> AfterSalesTicket | None:
    result = session.execute(
        update(AfterSalesTicket)
        .where(
            AfterSalesTicket.id == ticket_id,
            AfterSalesTicket.status == AfterSalesTicketStatus.PENDING_APPROVAL.value,
        )
        .values(
            status=decision.value,
            reviewer_id=reviewer_id,
            review_note=review_note,
            reviewed_at=datetime.now(UTC),
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.rollback()
        return None
    session.commit()
    return session.get(AfterSalesTicket, ticket_id)
