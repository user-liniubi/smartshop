import pytest
from sqlalchemy import select

from backend.app.agent.intent import merge_slots
from backend.app.agent.orchestrator import AfterSalesOrchestrator
from backend.app.agent.schemas import (
    AfterSalesIntent,
    IntentResult,
    IssueType,
    SlotUpdate,
    WorkflowAction,
)
from backend.app.core.exceptions import AppError
from backend.app.models import ChatSession, User, WorkflowState


def create_chat_session(test_database, username: str) -> tuple[int, int]:
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == username))
        assert user is not None
        chat_session = ChatSession(user_id=user.id)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return user.id, chat_session.id


def test_return_request_asks_for_all_missing_slots(seeded_client, test_database):
    user_id, session_id = create_chat_session(test_database, "consumer_demo")
    result = IntentResult(
        intent=AfterSalesIntent.RETURN_REQUEST,
        slots=SlotUpdate(),
        confidence=0.9,
    )

    with test_database.session_factory() as session:
        chat_session, decision = AfterSalesOrchestrator().apply(
            session=session,
            session_id=session_id,
            user_id=user_id,
            result=result,
        )

    assert decision.action == WorkflowAction.ASK_MORE_INFO
    assert decision.workflow_state == WorkflowState.COLLECTING_INFO
    assert decision.missing_slots == ["order_no", "issue_description"]
    assert decision.reply_text == "请补充订单号、具体问题。"
    assert chat_session.intent == "return_request"
    assert chat_session.workflow_state == "collecting_info"


def test_second_turn_only_asks_for_remaining_slot(seeded_client, test_database):
    user_id, session_id = create_chat_session(test_database, "consumer_demo")
    existing = {"order_no": "A10086"}
    merged = merge_slots(
        existing=existing,
        updates=SlotUpdate(),
        fallback_order_no=None,
    )
    result = IntentResult(
        intent=AfterSalesIntent.RETURN_REQUEST,
        slots=merged,
        confidence=0.9,
    )

    with test_database.session_factory() as session:
        _, decision = AfterSalesOrchestrator().apply(
            session=session,
            session_id=session_id,
            user_id=user_id,
            result=result,
        )

    assert decision.missing_slots == ["issue_description"]
    assert decision.reply_text == "请补充具体问题。"


def test_complete_return_request_enters_order_checking(seeded_client, test_database):
    user_id, session_id = create_chat_session(test_database, "consumer_demo")
    result = IntentResult(
        intent=AfterSalesIntent.RETURN_REQUEST,
        slots=SlotUpdate(
            order_no="A10086",
            issue_type=IssueType.RETURN,
            issue_description="左耳没有声音",
        ),
        confidence=0.95,
    )

    with test_database.session_factory() as session:
        _, decision = AfterSalesOrchestrator().apply(
            session=session,
            session_id=session_id,
            user_id=user_id,
            result=result,
        )

    assert decision.action == WorkflowAction.QUERY_ORDER
    assert decision.workflow_state == WorkflowState.CHECKING_ORDER


def test_policy_question_enters_policy_retrieval(seeded_client, test_database):
    user_id, session_id = create_chat_session(test_database, "consumer_demo")
    result = IntentResult(
        intent=AfterSalesIntent.WARRANTY_QUESTION,
        slots=SlotUpdate(),
        confidence=0.9,
    )

    with test_database.session_factory() as session:
        _, decision = AfterSalesOrchestrator().apply(
            session=session,
            session_id=session_id,
            user_id=user_id,
            result=result,
        )

    assert decision.action == WorkflowAction.RETRIEVE_POLICY
    assert decision.workflow_state == WorkflowState.CHECKING_POLICY


def test_human_request_enters_need_human(seeded_client, test_database):
    user_id, session_id = create_chat_session(test_database, "consumer_demo")
    result = IntentResult(
        intent=AfterSalesIntent.HUMAN_REQUEST,
        slots=SlotUpdate(),
        confidence=1,
    )

    with test_database.session_factory() as session:
        _, decision = AfterSalesOrchestrator().apply(
            session=session,
            session_id=session_id,
            user_id=user_id,
            result=result,
        )

    assert decision.action == WorkflowAction.HANDOFF
    assert decision.workflow_state == WorkflowState.NEED_HUMAN


def test_invalid_workflow_transition_is_rejected(seeded_client, test_database):
    user_id, session_id = create_chat_session(test_database, "consumer_demo")
    with test_database.session_factory() as session:
        chat_session = session.get(ChatSession, session_id)
        assert chat_session is not None
        chat_session.workflow_state = WorkflowState.NEED_HUMAN.value
        session.commit()

    result = IntentResult(
        intent=AfterSalesIntent.RETURN_REQUEST,
        slots=SlotUpdate(),
        confidence=0.9,
    )
    with test_database.session_factory() as session:
        with pytest.raises(AppError) as error:
            AfterSalesOrchestrator().apply(
                session=session,
                session_id=session_id,
                user_id=user_id,
                result=result,
            )

    assert error.value.code == "invalid_workflow_transition"


def test_workflow_state_and_slots_persist(seeded_client, test_database):
    user_id, session_id = create_chat_session(test_database, "consumer_demo")
    result = IntentResult(
        intent=AfterSalesIntent.RETURN_REQUEST,
        slots=SlotUpdate(order_no="A10086"),
        confidence=0.9,
    )

    with test_database.session_factory() as session:
        AfterSalesOrchestrator().apply(
            session=session,
            session_id=session_id,
            user_id=user_id,
            result=result,
        )

    with test_database.session_factory() as fresh_session:
        persisted = fresh_session.get(ChatSession, session_id)
        assert persisted is not None
        assert persisted.intent == "return_request"
        assert persisted.slots_json == {"order_no": "A10086"}
        assert persisted.workflow_state == "collecting_info"
