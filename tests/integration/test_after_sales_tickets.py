from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select

from backend.app.core.exceptions import AppError
from backend.app.db.session import Database
from backend.app.models import (
    AfterSalesTicket,
    AfterSalesTicketEvent,
    ChatMessage,
    ChatSession,
    Order,
    User,
)
from backend.app.models.enums import AfterSalesTicketType
from backend.app.services.after_sales_tickets import AfterSalesTicketService
from sample_data.seed import AGENT_PASSWORD, DEMO_PASSWORD


def _login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_after_sales_ticket_is_idempotent_and_reviewable(
    seeded_client,
    test_database,
):
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        order = session.scalar(select(Order).where(Order.order_no == "A10086"))
        assert user is not None
        assert order is not None
        chat_session = ChatSession(user_id=user.id, intent="return_request")
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)

        service = AfterSalesTicketService(session)
        first, created = service.create_for_session(
            chat_session=chat_session,
            order=order,
            request_type=AfterSalesTicketType.RETURN,
            issue_description="左耳没有声音",
            citations=[],
        )
        duplicate, duplicate_created = service.create_for_session(
            chat_session=chat_session,
            order=order,
            request_type=AfterSalesTicketType.RETURN,
            issue_description="左耳没有声音",
            citations=[],
        )
        first_id = first.id
        first_ticket_no = first.ticket_no
        first_session_id = first.session_id

    assert created is True
    assert duplicate_created is False
    assert duplicate.id == first_id

    consumer_headers = _login_headers(
        seeded_client,
        "consumer_demo",
        DEMO_PASSWORD,
    )
    agent_headers = _login_headers(
        seeded_client,
        "agent_demo",
        AGENT_PASSWORD,
    )

    mine = seeded_client.get("/after-sales/tickets/mine", headers=consumer_headers)
    pending = seeded_client.get(
        "/agent/after-sales/tickets",
        headers=agent_headers,
    )
    approved = seeded_client.post(
        f"/agent/after-sales/tickets/{first_id}/review",
        headers=agent_headers,
        json={"decision": "approved", "review_note": "订单和政策核验通过"},
    )
    reviewed_again = seeded_client.post(
        f"/agent/after-sales/tickets/{first_id}/review",
        headers=agent_headers,
        json={"decision": "rejected", "review_note": "重复审批"},
    )
    mine_after_review = seeded_client.get(
        "/after-sales/tickets/mine",
        headers=consumer_headers,
    )
    events = seeded_client.get(
        f"/after-sales/tickets/{first_id}/events",
        headers=consumer_headers,
    )

    assert mine.status_code == 200
    assert mine.json()[0]["ticket_no"] == first_ticket_no
    assert pending.status_code == 200
    assert pending.json()[0]["id"] == first_id
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewer_id"] is not None
    assert reviewed_again.status_code == 409
    assert reviewed_again.json()["error"]["code"] == ("after_sales_ticket_already_reviewed")
    assert mine_after_review.json()[0]["status"] == "approved"
    assert [event["event_type"] for event in events.json()] == [
        "created",
        "approved",
    ]
    with test_database.session_factory() as session:
        system_messages = list(
            session.scalars(
                select(ChatMessage).where(
                    ChatMessage.session_id == first_session_id,
                    ChatMessage.sender_type == "system",
                )
            )
        )
    assert len(system_messages) == 2
    assert "已创建" in system_messages[0].content
    assert "已通过审批" in system_messages[1].content


def test_rejecting_after_sales_ticket_requires_note(
    seeded_client,
    test_database,
):
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        order = session.scalar(select(Order).where(Order.order_no == "A10086"))
        assert user is not None
        assert order is not None
        chat_session = ChatSession(user_id=user.id, intent="exchange_request")
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        ticket = AfterSalesTicket(
            ticket_no="AS-TESTREJECT",
            session_id=chat_session.id,
            user_id=user.id,
            order_id=order.id,
            request_type="exchange",
            issue_description="按键失灵",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = ticket.id

    agent_headers = _login_headers(
        seeded_client,
        "agent_demo",
        AGENT_PASSWORD,
    )
    response = seeded_client.post(
        f"/agent/after-sales/tickets/{ticket_id}/review",
        headers=agent_headers,
        json={"decision": "rejected", "review_note": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "review_note_required"


def test_consumer_cancels_pending_ticket_and_cannot_cancel_other_users_ticket(
    seeded_client,
    test_database,
):
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        order = session.scalar(select(Order).where(Order.order_no == "A10086"))
        assert user is not None
        assert order is not None
        chat_session = ChatSession(user_id=user.id, intent="return_request")
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        ticket, _ = AfterSalesTicketService(session).create_for_session(
            chat_session=chat_session,
            order=order,
            request_type=AfterSalesTicketType.RETURN,
            issue_description="左耳没有声音",
            citations=[],
        )
        ticket_id = ticket.id

    owner_headers = _login_headers(seeded_client, "consumer_demo", DEMO_PASSWORD)
    other_headers = _login_headers(seeded_client, "consumer_other", DEMO_PASSWORD)

    denied = seeded_client.post(
        f"/after-sales/tickets/{ticket_id}/cancel",
        headers=other_headers,
    )
    cancelled = seeded_client.post(
        f"/after-sales/tickets/{ticket_id}/cancel",
        headers=owner_headers,
    )
    events = seeded_client.get(
        f"/after-sales/tickets/{ticket_id}/events",
        headers=owner_headers,
    )

    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "after_sales_ticket_not_found"
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None
    assert [event["event_type"] for event in events.json()] == [
        "created",
        "cancelled",
    ]


def test_cross_session_duplicate_active_request_is_blocked(
    seeded_client,
    test_database,
):
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        order = session.scalar(select(Order).where(Order.order_no == "A10086"))
        assert user is not None
        assert order is not None
        first_session = ChatSession(user_id=user.id, intent="return_request")
        second_session = ChatSession(user_id=user.id, intent="return_request")
        session.add_all([first_session, second_session])
        session.commit()
        service = AfterSalesTicketService(session)
        service.create_for_session(
            chat_session=first_session,
            order=order,
            request_type=AfterSalesTicketType.RETURN,
            issue_description="左耳没有声音",
            citations=[],
        )

        with pytest.raises(AppError) as error:
            service.create_for_session(
                chat_session=second_session,
                order=order,
                request_type=AfterSalesTicketType.RETURN,
                issue_description="左耳没有声音",
                citations=[],
            )

    assert error.value.code == "duplicate_active_after_sales_request"


def test_true_concurrent_approval_allows_only_one_success(tmp_path):
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'concurrent-ticket.db'}")
    with database.engine.begin() as connection:
        from backend.app.models import Base

        Base.metadata.create_all(connection)

    from sample_data.seed import seed_demo_data

    with database.session_factory() as session:
        seed_demo_data(session)
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        agent = session.scalar(select(User).where(User.username == "agent_demo"))
        order = session.scalar(select(Order).where(Order.order_no == "A10086"))
        assert user is not None
        assert agent is not None
        assert order is not None
        chat_session = ChatSession(user_id=user.id, intent="return_request")
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        ticket, _ = AfterSalesTicketService(session).create_for_session(
            chat_session=chat_session,
            order=order,
            request_type=AfterSalesTicketType.RETURN,
            issue_description="左耳没有声音",
            citations=[],
        )
        ticket_id = ticket.id
        reviewer_id = agent.id

    barrier = Barrier(2)

    def review_once(decision: str) -> str:
        with database.session_factory() as session:
            barrier.wait(timeout=10)
            try:
                AfterSalesTicketService(session).review(
                    ticket_id=ticket_id,
                    reviewer_id=reviewer_id,
                    decision=decision,
                    review_note="并发审批测试",
                )
                return decision
            except AppError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                review_once,
                ["approved", "rejected"],
            )
        )

    with database.session_factory() as session:
        ticket = session.get(AfterSalesTicket, ticket_id)
        events = list(
            session.scalars(
                select(AfterSalesTicketEvent).where(AfterSalesTicketEvent.ticket_id == ticket_id)
            )
        )
    assert outcomes.count("after_sales_ticket_already_reviewed") == 1
    successful_decision = next(
        outcome for outcome in outcomes if outcome in {"approved", "rejected"}
    )
    assert ticket is not None
    assert ticket.status == successful_decision
    assert [event.event_type for event in events] == [
        "created",
        successful_decision,
    ]
    database.dispose()
