from sqlalchemy import select

from backend.app.models import AfterSalesTicket, ChatSession, Order, User
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

    assert created is True
    assert duplicate_created is False
    assert duplicate.id == first.id

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
        f"/agent/after-sales/tickets/{first.id}/review",
        headers=agent_headers,
        json={"decision": "approved", "review_note": "订单和政策核验通过"},
    )
    reviewed_again = seeded_client.post(
        f"/agent/after-sales/tickets/{first.id}/review",
        headers=agent_headers,
        json={"decision": "rejected", "review_note": "重复审批"},
    )
    mine_after_review = seeded_client.get(
        "/after-sales/tickets/mine",
        headers=consumer_headers,
    )

    assert mine.status_code == 200
    assert mine.json()[0]["ticket_no"] == first.ticket_no
    assert pending.status_code == 200
    assert pending.json()[0]["id"] == first.id
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewer_id"] is not None
    assert reviewed_again.status_code == 409
    assert reviewed_again.json()["error"]["code"] == ("after_sales_ticket_already_reviewed")
    assert mine_after_review.json()[0]["status"] == "approved"


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
