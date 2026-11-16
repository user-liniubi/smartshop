import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.app.agent.intent import IntentService
from backend.app.agent.schemas import AfterSalesIntent, IntentResult, IssueType, SlotUpdate
from backend.app.core.exceptions import AppError
from backend.app.models import (
    ChatSession,
    Order,
    OrderSelectionState,
    User,
    WorkflowState,
)
from backend.app.services.order_context import OrderContextService
from sample_data.seed import DEMO_PASSWORD


class FollowUpIntentClient:
    def __init__(self, *, issue_type: str = "return") -> None:
        self.issue_type = issue_type

    async def extract_intent(self, *, message: str, existing_slots: dict) -> str:
        return (
            '{"intent":"return_request","slots":{"order_no":null,'
            f'"issue_type":"{self.issue_type}","issue_description":"左耳没有声音"}},'
            '"confidence":0.9}'
        )


def _login_headers(client, username: str = "consumer_demo") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_second_headphone_order(test_database, *, created_at: datetime) -> int:
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        headphones = session.scalar(select(Order).where(Order.order_no == "A10086"))
        assert user is not None
        assert headphones is not None
        order = Order(
            order_no="A20001",
            user_id=user.id,
            product_id=headphones.product_id,
            status="delivered",
            created_at=created_at,
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        return order.id


def _create_session(test_database) -> tuple[int, int]:
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        assert user is not None
        chat_session = ChatSession(user_id=user.id)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return user.id, chat_session.id


def test_order_list_is_latest_first_and_scoped_to_current_user(seeded_client):
    response = seeded_client.get("/orders/mine", headers=_login_headers(seeded_client))

    assert response.status_code == 200
    order_numbers = [order["order_no"] for order in response.json()]
    assert order_numbers[:3] == ["A10089", "A10087", "A10086"]
    assert "A10088" not in order_numbers
    assert "A10090" not in order_numbers


def test_product_hint_selects_unique_owned_order(
    seeded_client,
    test_database,
):
    user_id, session_id = _create_session(test_database)
    with test_database.session_factory() as session:
        chat_session = session.get(ChatSession, session_id)
        assert chat_session is not None
        result = IntentResult(
            intent=AfterSalesIntent.RETURN_REQUEST,
            slots=SlotUpdate(
                issue_type=IssueType.RETURN,
                issue_description="左耳没有声音",
                submit_requested=True,
            ),
            confidence=0.9,
        )

        resolution = OrderContextService(session).resolve_for_turn(
            chat_session=chat_session,
            intent_result=result,
            content="耳机左耳没有声音，想退货",
        )

    assert resolution.awaiting_selection is False
    assert resolution.selected_order is not None
    assert resolution.selected_order.order_no == "A10086"
    assert result.slots.order_no == "A10086"


def test_ambiguous_orders_are_not_guessed_and_can_be_selected(
    seeded_client,
    test_database,
):
    second_order_id = _create_second_headphone_order(
        test_database,
        created_at=datetime.now(UTC) - timedelta(days=1),
    )
    user_id, session_id = _create_session(test_database)

    with test_database.session_factory() as session:
        chat_session = session.get(ChatSession, session_id)
        assert chat_session is not None
        result = IntentResult(
            intent=AfterSalesIntent.RETURN_REQUEST,
            slots=SlotUpdate(
                issue_type=IssueType.RETURN,
                issue_description="左耳没有声音",
                submit_requested=True,
            ),
            confidence=0.9,
        )
        resolution = OrderContextService(session).resolve_for_turn(
            chat_session=chat_session,
            intent_result=result,
            content="耳机左耳没有声音，想退货",
        )

        assert resolution.awaiting_selection is True
        assert len(resolution.candidates) == 2
        assert result.slots.order_no is None
        assert chat_session.order_selection_state == (OrderSelectionState.AWAITING_SELECTION.value)
        assert "A10086" in (resolution.prompt or "")
        assert "A20001" in (resolution.prompt or "")

        selected = OrderContextService(session).select_candidate(
            session_id=session_id,
            user_id=user_id,
            order_id=second_order_id,
        )

    assert selected.order_selection_state == OrderSelectionState.SELECTED.value
    assert selected.selected_order_id == second_order_id
    assert selected.slots_json["order_no"] == "A20001"


def test_selection_rejects_an_order_outside_candidate_list(
    seeded_client,
    test_database,
):
    user_id, session_id = _create_session(test_database)
    with test_database.session_factory() as session:
        chat_session = session.get(ChatSession, session_id)
        assert chat_session is not None
        chat_session.candidate_order_ids_json = [1, 2]
        chat_session.order_selection_state = OrderSelectionState.AWAITING_SELECTION.value
        session.commit()

        with pytest.raises(AppError) as error:
            OrderContextService(session).select_candidate(
                session_id=session_id,
                user_id=user_id,
                order_id=3,
            )

    assert error.value.code == "order_candidate_invalid"


def test_model_cannot_bypass_order_selection_without_owned_candidate(
    seeded_client,
    test_database,
):
    user_id, _ = _create_session(test_database)
    with test_database.session_factory() as session:
        other_order = session.scalar(select(Order).where(Order.order_no == "A10088"))
        assert other_order is not None
        context = OrderContextService(session)
        chat_session = ChatSession(
            user_id=user_id,
            candidate_order_ids_json=[other_order.id],
            order_selection_state=OrderSelectionState.AWAITING_SELECTION.value,
            workflow_state=WorkflowState.AWAITING_ORDER_SELECTION.value,
        )
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)

        with pytest.raises(AppError) as error:
            context.select_candidate(
                session_id=chat_session.id,
                user_id=user_id,
                order_id=other_order.id,
            )

    assert error.value.code == "order_not_found"


def test_switch_reference_clears_inherited_order_and_reevaluates_candidates():
    first = type("OrderStub", (), {"id": 1, "order_no": "A10086"})()
    second = type("OrderStub", (), {"id": 2, "order_no": "A20001"})()

    selected = OrderContextService._resolve_candidate(
        candidates=[first, second],
        reference="不是这个，是另一笔",
        current_order_id=1,
    )

    assert selected is second


def test_follow_up_switch_clears_previous_order_number(
    seeded_client,
    test_database,
):
    client = FollowUpIntentClient()

    result = asyncio.run(
        IntentService(client).extract(
            content="不是这个，是另一笔",
            existing_slots={
                "order_no": "A10086",
                "product_id": 1,
                "issue_type": "return",
                "issue_description": "左耳没有声音",
            },
        )
    )

    assert result.slots.order_no is None
    assert result.slots.order_reference == "不是这个，是另一笔"
    assert result.slots.issue_description == "左耳没有声音"
