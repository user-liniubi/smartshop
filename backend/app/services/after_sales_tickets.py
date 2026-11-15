from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppError
from backend.app.models import (
    AfterSalesTicket,
    AfterSalesTicketStatus,
    AfterSalesTicketType,
    ChatSession,
    Order,
)
from backend.app.repositories.after_sales_tickets import (
    get_ticket_by_session,
    list_pending_tickets,
    list_user_tickets,
    review_ticket_atomic,
)
from backend.app.schemas.rag import CitationResponse


class AfterSalesTicketService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_for_session(
        self,
        *,
        chat_session: ChatSession,
        order: Order,
        request_type: AfterSalesTicketType,
        issue_description: str,
        citations: list[CitationResponse],
    ) -> tuple[AfterSalesTicket, bool]:
        existing = get_ticket_by_session(
            self.session,
            session_id=chat_session.id,
        )
        if existing is not None:
            if existing.order_id != order.id or existing.request_type != request_type.value:
                raise AppError(
                    status_code=409,
                    code="after_sales_ticket_conflict",
                    message="当前会话已经提交了不同的售后工单",
                )
            return existing, False

        ticket = AfterSalesTicket(
            ticket_no=f"AS-{uuid4().hex[:12].upper()}",
            session_id=chat_session.id,
            user_id=chat_session.user_id,
            order_id=order.id,
            request_type=request_type.value,
            issue_description=issue_description,
            policy_citations_json=[citation.model_dump(mode="json") for citation in citations],
        )
        self.session.add(ticket)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = get_ticket_by_session(
                self.session,
                session_id=chat_session.id,
            )
            if existing is None:
                raise
            return existing, False
        self.session.refresh(ticket)
        return ticket, True

    def list_for_user(self, *, user_id: int) -> list[AfterSalesTicket]:
        return list_user_tickets(self.session, user_id=user_id)

    def list_pending(self) -> list[AfterSalesTicket]:
        return list_pending_tickets(self.session)

    def review(
        self,
        *,
        ticket_id: int,
        reviewer_id: int,
        decision: str,
        review_note: str,
    ) -> AfterSalesTicket:
        if decision == AfterSalesTicketStatus.REJECTED.value and not review_note.strip():
            raise AppError(
                status_code=422,
                code="review_note_required",
                message="拒绝工单时必须填写审批意见",
            )
        ticket = review_ticket_atomic(
            self.session,
            ticket_id=ticket_id,
            reviewer_id=reviewer_id,
            decision=AfterSalesTicketStatus(decision),
            review_note=review_note.strip(),
        )
        if ticket is None:
            existing = self.session.get(AfterSalesTicket, ticket_id)
            if existing is None:
                raise AppError(
                    status_code=404,
                    code="after_sales_ticket_not_found",
                    message="售后工单不存在",
                )
            raise AppError(
                status_code=409,
                code="after_sales_ticket_already_reviewed",
                message="该售后工单已被处理",
            )
        return ticket
