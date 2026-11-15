from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.dependencies import CurrentUser
from backend.app.core.exceptions import AppError
from backend.app.db.session import get_db
from backend.app.schemas.after_sales import AfterSalesTicketResponse
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
