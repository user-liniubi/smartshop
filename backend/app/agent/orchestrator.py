from sqlalchemy.orm import Session

from backend.app.agent.schemas import (
    AfterSalesIntent,
    IntentResult,
    OrchestrationDecision,
    SlotUpdate,
    WorkflowAction,
)
from backend.app.core.exceptions import AppError
from backend.app.models import ChatSession, WorkflowState
from backend.app.repositories.chat import get_session_owned_by_user

_REQUIRED_SLOTS: dict[AfterSalesIntent, tuple[str, ...]] = {
    AfterSalesIntent.ORDER_QUERY: ("order_no",),
    AfterSalesIntent.RETURN_REQUEST: ("order_no", "issue_description"),
    AfterSalesIntent.EXCHANGE_REQUEST: ("order_no", "issue_description"),
}

_ALLOWED_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.COLLECTING_INFO: frozenset(
        {
            WorkflowState.COLLECTING_INFO,
            WorkflowState.CHECKING_ORDER,
            WorkflowState.CHECKING_POLICY,
            WorkflowState.NEED_HUMAN,
        }
    ),
    WorkflowState.CHECKING_ORDER: frozenset(
        {
            WorkflowState.COLLECTING_INFO,
            WorkflowState.CHECKING_POLICY,
            WorkflowState.NEED_HUMAN,
        }
    ),
    WorkflowState.CHECKING_POLICY: frozenset(
        {
            WorkflowState.ANSWER_READY,
            WorkflowState.NEED_HUMAN,
        }
    ),
    WorkflowState.ANSWER_READY: frozenset(
        {
            WorkflowState.RESOLVED,
            WorkflowState.NEED_HUMAN,
        }
    ),
    WorkflowState.NEED_HUMAN: frozenset({WorkflowState.NEED_HUMAN}),
    WorkflowState.RESOLVED: frozenset({WorkflowState.RESOLVED}),
}

_SLOT_LABELS = {
    "order_no": "订单号",
    "issue_description": "具体问题",
}


class AfterSalesOrchestrator:
    """Apply backend-controlled workflow decisions to an owned chat session."""

    def decide(self, result: IntentResult) -> OrchestrationDecision:
        if result.intent == AfterSalesIntent.HUMAN_REQUEST:
            return OrchestrationDecision(
                action=WorkflowAction.HANDOFF,
                workflow_state=WorkflowState.NEED_HUMAN,
            )

        required_slots = _REQUIRED_SLOTS.get(result.intent, ())
        missing_slots = [slot for slot in required_slots if not _slot_value(result.slots, slot)]
        if missing_slots:
            labels = "、".join(_SLOT_LABELS[slot] for slot in missing_slots)
            return OrchestrationDecision(
                action=WorkflowAction.ASK_MORE_INFO,
                workflow_state=WorkflowState.COLLECTING_INFO,
                missing_slots=missing_slots,
                reply_text=f"请补充{labels}。",
            )

        if result.intent in {
            AfterSalesIntent.ORDER_QUERY,
            AfterSalesIntent.RETURN_REQUEST,
            AfterSalesIntent.EXCHANGE_REQUEST,
        } or (result.intent == AfterSalesIntent.WARRANTY_QUESTION and result.slots.order_no):
            return OrchestrationDecision(
                action=WorkflowAction.QUERY_ORDER,
                workflow_state=WorkflowState.CHECKING_ORDER,
            )

        if result.intent == AfterSalesIntent.UNKNOWN:
            return OrchestrationDecision(
                action=WorkflowAction.ASK_MORE_INFO,
                workflow_state=WorkflowState.COLLECTING_INFO,
                reply_text="请进一步说明订单或售后问题。",
            )

        return OrchestrationDecision(
            action=WorkflowAction.RETRIEVE_POLICY,
            workflow_state=WorkflowState.CHECKING_POLICY,
        )

    def apply(
        self,
        *,
        session: Session,
        session_id: int,
        user_id: int,
        result: IntentResult,
    ) -> tuple[ChatSession, OrchestrationDecision]:
        chat_session = get_session_owned_by_user(
            session,
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise AppError(
                status_code=404,
                code="chat_session_not_found",
                message="会话不存在",
            )

        current_state = WorkflowState(chat_session.workflow_state)
        decision = self.decide(result)
        if decision.workflow_state not in _ALLOWED_TRANSITIONS[current_state]:
            raise AppError(
                status_code=409,
                code="invalid_workflow_transition",
                message="当前售后状态不允许此操作",
            )

        chat_session.intent = result.intent.value
        chat_session.slots_json = result.slots.model_dump(
            mode="json",
            exclude_none=True,
        )
        chat_session.workflow_state = decision.workflow_state.value
        session.commit()
        session.refresh(chat_session)
        return chat_session, decision


def _slot_value(slots: SlotUpdate, name: str) -> object:
    return getattr(slots, name)
