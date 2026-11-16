from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppError
from backend.app.models import (
    AfterSalesActorType,
    AfterSalesTicket,
    AfterSalesTicketEvent,
    AfterSalesTicketEventType,
    AfterSalesTicketStatus,
    AfterSalesTicketType,
    ChatMessage,
    ChatSession,
    Order,
    SenderType,
)
from backend.app.repositories.after_sales_tickets import (
    cancel_ticket_atomic,
    get_active_ticket_for_request,
    get_ticket_by_session,
    get_ticket_owned_by_user,
    list_pending_tickets,
    list_ticket_events,
    list_user_tickets,
    review_ticket_atomic,
)
from backend.app.schemas.rag import CitationResponse
from backend.app.services.after_sales_eligibility import (
    AfterSalesEligibility,
    AfterSalesEligibilityService,
)


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
        eligibility: AfterSalesEligibility | None = None,
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

        active_ticket = get_active_ticket_for_request(
            self.session,
            user_id=chat_session.user_id,
            order_id=order.id,
            request_type=request_type.value,
        )
        if active_ticket is not None:
            raise self._duplicate_request_error(active_ticket)

        eligibility = eligibility or AfterSalesEligibilityService().evaluate(
            order=order,
            request_type=request_type.value,
            issue_description=issue_description,
        )
        if eligibility.result.value == "need_human_review":
            raise AppError(
                status_code=409,
                code="after_sales_requires_manual_review",
                message=eligibility.explanation,
            )
        if eligibility.result.value == "not_eligible":
            raise AppError(
                status_code=409,
                code="after_sales_not_eligible",
                message=eligibility.explanation,
            )

        ticket = AfterSalesTicket(
            ticket_no=f"AS-{uuid4().hex[:12].upper()}",
            session_id=chat_session.id,
            user_id=chat_session.user_id,
            order_id=order.id,
            request_type=request_type.value,
            issue_description=issue_description,
            policy_citations_json=[citation.model_dump(mode="json") for citation in citations],
            eligibility_result=eligibility.result.value,
            eligibility_reason=eligibility.reason_code,
            refund_amount=eligibility.refund_amount,
            currency=eligibility.currency,
            rule_version=eligibility.rule_version,
            active_dedup_key=self._active_dedup_key(
                user_id=chat_session.user_id,
                order_id=order.id,
                request_type=request_type.value,
            ),
        )
        self.session.add(ticket)
        self.session.flush()
        self.session.add(
            AfterSalesTicketEvent(
                ticket_id=ticket.id,
                event_type=AfterSalesTicketEventType.CREATED.value,
                from_status=None,
                to_status=AfterSalesTicketStatus.PENDING_APPROVAL.value,
                actor_type=AfterSalesActorType.CONSUMER.value,
                actor_id=chat_session.user_id,
                note="消费者提交售后申请，系统完成订单和政策核验",
            )
        )
        self.session.add(
            ChatMessage(
                session_id=chat_session.id,
                sender_type=SenderType.SYSTEM.value,
                content=f"售后工单 {ticket.ticket_no} 已创建，当前等待人工审批。",
                citations_json=[],
            )
        )
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = get_ticket_by_session(
                self.session,
                session_id=chat_session.id,
            )
            if existing is not None:
                return existing, False
            active_ticket = get_active_ticket_for_request(
                self.session,
                user_id=chat_session.user_id,
                order_id=order.id,
                request_type=request_type.value,
            )
            if active_ticket is not None:
                raise self._duplicate_request_error(active_ticket) from None
            raise
        self.session.refresh(ticket)
        return ticket, True

    def list_for_user(self, *, user_id: int) -> list[AfterSalesTicket]:
        return list_user_tickets(self.session, user_id=user_id)

    def list_pending(self) -> list[AfterSalesTicket]:
        return list_pending_tickets(self.session)

    def get_for_user(self, *, ticket_id: int, user_id: int) -> AfterSalesTicket:
        ticket = get_ticket_owned_by_user(
            self.session,
            ticket_id=ticket_id,
            user_id=user_id,
        )
        if ticket is None:
            raise AppError(
                status_code=404,
                code="after_sales_ticket_not_found",
                message="售后工单不存在",
            )
        return ticket

    def list_events(
        self,
        *,
        ticket_id: int,
        user_id: int,
    ) -> list[AfterSalesTicketEvent]:
        self.get_for_user(ticket_id=ticket_id, user_id=user_id)
        return list_ticket_events(self.session, ticket_id=ticket_id)

    def cancel(self, *, ticket_id: int, user_id: int) -> AfterSalesTicket:
        ticket = self.get_for_user(ticket_id=ticket_id, user_id=user_id)
        if ticket.status != AfterSalesTicketStatus.PENDING_APPROVAL.value:
            raise AppError(
                status_code=409,
                code="after_sales_ticket_not_cancellable",
                message="只有待审批工单可以由消费者取消",
            )
        cancelled = cancel_ticket_atomic(
            self.session,
            ticket_id=ticket_id,
            user_id=user_id,
        )
        if cancelled is None:
            raise AppError(
                status_code=409,
                code="after_sales_ticket_cancel_conflict",
                message="工单状态已发生变化，请刷新后重试",
            )
        self.session.add(
            AfterSalesTicketEvent(
                ticket_id=ticket_id,
                event_type=AfterSalesTicketEventType.CANCELLED.value,
                from_status=AfterSalesTicketStatus.PENDING_APPROVAL.value,
                to_status=AfterSalesTicketStatus.CANCELLED.value,
                actor_type=AfterSalesActorType.CONSUMER.value,
                actor_id=user_id,
                note="消费者取消待审批售后申请",
            )
        )
        self.session.add(
            ChatMessage(
                session_id=ticket.session_id,
                sender_type=SenderType.SYSTEM.value,
                content=f"售后工单 {ticket.ticket_no} 已由消费者取消。",
                citations_json=[],
            )
        )
        self.session.commit()
        self.session.refresh(cancelled)
        return cancelled

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
            self.session.rollback()
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

        event_type = (
            AfterSalesTicketEventType.APPROVED
            if ticket.status == AfterSalesTicketStatus.APPROVED.value
            else AfterSalesTicketEventType.REJECTED
        )
        self.session.add(
            AfterSalesTicketEvent(
                ticket_id=ticket.id,
                event_type=event_type.value,
                from_status=AfterSalesTicketStatus.PENDING_APPROVAL.value,
                to_status=ticket.status,
                actor_type=AfterSalesActorType.AGENT.value,
                actor_id=reviewer_id,
                note=review_note.strip(),
            )
        )
        decision_label = (
            "通过审批" if event_type == AfterSalesTicketEventType.APPROVED else "被驳回"
        )
        note_suffix = f"审批意见：{review_note.strip()}" if review_note.strip() else ""
        self.session.add(
            ChatMessage(
                session_id=ticket.session_id,
                sender_type=SenderType.SYSTEM.value,
                content=(f"售后工单 {ticket.ticket_no} 已{decision_label}。{note_suffix}"),
                citations_json=[],
            )
        )
        self.session.commit()
        self.session.refresh(ticket)
        return ticket

    @staticmethod
    def _active_dedup_key(
        *,
        user_id: int,
        order_id: int,
        request_type: str,
    ) -> str:
        return f"{user_id}:{order_id}:{request_type}"

    @staticmethod
    def _duplicate_request_error(ticket: AfterSalesTicket) -> AppError:
        return AppError(
            status_code=409,
            code="duplicate_active_after_sales_request",
            message=(f"该订单已存在处理中或已审批的售后工单 {ticket.ticket_no}，请勿重复提交"),
        )
