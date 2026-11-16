from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.models import AfterSalesTicket, AfterSalesTicketEvent
from backend.app.models.enums import AfterSalesTicketStatus


def get_ticket_by_session(
    session: Session,
    *,
    session_id: int,
) -> AfterSalesTicket | None:
    return session.scalar(select(AfterSalesTicket).where(AfterSalesTicket.session_id == session_id))


def get_active_ticket_for_request(
    session: Session,
    *,
    user_id: int,
    order_id: int,
    request_type: str,
) -> AfterSalesTicket | None:
    statement = select(AfterSalesTicket).where(
        AfterSalesTicket.user_id == user_id,
        AfterSalesTicket.order_id == order_id,
        AfterSalesTicket.request_type == request_type,
        AfterSalesTicket.active_dedup_key.is_not(None),
    )
    return session.scalar(statement)


def get_ticket_owned_by_user(
    session: Session,
    *,
    ticket_id: int,
    user_id: int,
) -> AfterSalesTicket | None:
    return session.scalar(
        select(AfterSalesTicket).where(
            AfterSalesTicket.id == ticket_id,
            AfterSalesTicket.user_id == user_id,
        )
    )


def list_ticket_events(
    session: Session,
    *,
    ticket_id: int,
) -> list[AfterSalesTicketEvent]:
    statement = (
        select(AfterSalesTicketEvent)
        .where(AfterSalesTicketEvent.ticket_id == ticket_id)
        .order_by(AfterSalesTicketEvent.created_at, AfterSalesTicketEvent.id)
    )
    return list(session.scalars(statement))


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
            active_dedup_key=(
                None
                if decision == AfterSalesTicketStatus.REJECTED
                else AfterSalesTicket.active_dedup_key
            ),
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.flush()
        return None
    session.flush()
    return session.get(AfterSalesTicket, ticket_id)


def cancel_ticket_atomic(
    session: Session,
    *,
    ticket_id: int,
    user_id: int,
) -> AfterSalesTicket | None:
    result = session.execute(
        update(AfterSalesTicket)
        .where(
            AfterSalesTicket.id == ticket_id,
            AfterSalesTicket.user_id == user_id,
            AfterSalesTicket.status == AfterSalesTicketStatus.PENDING_APPROVAL.value,
        )
        .values(
            status=AfterSalesTicketStatus.CANCELLED.value,
            active_dedup_key=None,
            cancelled_at=datetime.now(UTC),
            cancelled_by_id=user_id,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        return None
    session.flush()
    return session.get(AfterSalesTicket, ticket_id)
