from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AgentUser
from backend.app.db.session import get_db
from backend.app.schemas.after_sales import (
    AfterSalesTicketResponse,
    AfterSalesTicketReviewRequest,
)
from backend.app.services.after_sales_tickets import AfterSalesTicketService

router = APIRouter(prefix="/agent/after-sales", tags=["agent"])


@router.get("/tickets", response_model=list[AfterSalesTicketResponse])
def list_pending_after_sales_tickets(
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[AfterSalesTicketResponse]:
    tickets = AfterSalesTicketService(session).list_pending()
    return [AfterSalesTicketResponse.model_validate(ticket) for ticket in tickets]


@router.post(
    "/tickets/{ticket_id}/review",
    response_model=AfterSalesTicketResponse,
)
def review_after_sales_ticket(
    ticket_id: Annotated[int, Path(gt=0)],
    request: AfterSalesTicketReviewRequest,
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> AfterSalesTicketResponse:
    ticket = AfterSalesTicketService(session).review(
        ticket_id=ticket_id,
        reviewer_id=current_agent.id,
        decision=request.decision,
        review_note=request.review_note,
    )
    return AfterSalesTicketResponse.model_validate(ticket)
