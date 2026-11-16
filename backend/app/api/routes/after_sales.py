from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.api.dependencies import CurrentUser
from backend.app.core.exceptions import AppError
from backend.app.db.session import get_db
from backend.app.schemas.after_sales import (
    AfterSalesTicketEventResponse,
    AfterSalesTicketResponse,
)
from backend.app.services.after_sales_tickets import AfterSalesTicketService

router = APIRouter(prefix="/after-sales", tags=["after-sales"])


@router.get("/tickets/mine", response_model=list[AfterSalesTicketResponse])
def list_my_after_sales_tickets(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[AfterSalesTicketResponse]:
    if current_user.role != "consumer":
        raise AppError(
            status_code=403,
            code="consumer_role_required",
            message="该操作仅限消费者账号",
        )
    tickets = AfterSalesTicketService(session).list_for_user(user_id=current_user.id)
    return [AfterSalesTicketResponse.model_validate(ticket) for ticket in tickets]


@router.get(
    "/tickets/{ticket_id}",
    response_model=AfterSalesTicketResponse,
)
def get_my_after_sales_ticket(
    ticket_id: Annotated[int, Path(gt=0)],
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> AfterSalesTicketResponse:
    if current_user.role != "consumer":
        raise AppError(
            status_code=403,
            code="consumer_role_required",
            message="该操作仅限消费者账号",
        )
    ticket = AfterSalesTicketService(session).get_for_user(
        ticket_id=ticket_id,
        user_id=current_user.id,
    )
    return AfterSalesTicketResponse.model_validate(ticket)


@router.get(
    "/tickets/{ticket_id}/events",
    response_model=list[AfterSalesTicketEventResponse],
)
def list_my_after_sales_ticket_events(
    ticket_id: Annotated[int, Path(gt=0)],
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[AfterSalesTicketEventResponse]:
    if current_user.role != "consumer":
        raise AppError(
            status_code=403,
            code="consumer_role_required",
            message="该操作仅限消费者账号",
        )
    events = AfterSalesTicketService(session).list_events(
        ticket_id=ticket_id,
        user_id=current_user.id,
    )
    return [AfterSalesTicketEventResponse.model_validate(event) for event in events]


@router.post(
    "/tickets/{ticket_id}/cancel",
    response_model=AfterSalesTicketResponse,
)
def cancel_my_after_sales_ticket(
    ticket_id: Annotated[int, Path(gt=0)],
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> AfterSalesTicketResponse:
    if current_user.role != "consumer":
        raise AppError(
            status_code=403,
            code="consumer_role_required",
            message="该操作仅限消费者账号",
        )
    ticket = AfterSalesTicketService(session).cancel(
        ticket_id=ticket_id,
        user_id=current_user.id,
    )
    return AfterSalesTicketResponse.model_validate(ticket)
