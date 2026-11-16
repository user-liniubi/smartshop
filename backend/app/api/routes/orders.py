from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies import CurrentUser
from backend.app.core.exceptions import AppError
from backend.app.db.session import get_db
from backend.app.schemas.order import OrderResponse
from backend.app.services.orders import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/mine", response_model=list[OrderResponse])
def list_my_orders(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[OrderResponse]:
    """Return only the authenticated consumer's recent orders."""

    if current_user.role != "consumer":
        raise AppError(
            status_code=403,
            code="consumer_role_required",
            message="该操作仅限消费者账号",
        )
    return [
        OrderResponse.model_validate(order)
        for order in OrderService(session).list_recent_for_user(
            user_id=current_user.id,
            limit=limit,
        )
    ]


@router.get("/by-number/{order_no}", response_model=OrderResponse)
def get_order_by_number(
    order_no: Annotated[
        str,
        Path(min_length=4, max_length=32, pattern=r"^[A-Za-z0-9_-]+$"),
    ],
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    """Return a user's order using the business-facing order number."""

    order = OrderService(session).get_order_for_user_by_no(
        order_no=order_no,
        user_id=current_user.id,
    )
    return OrderResponse.model_validate(order)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: Annotated[int, Path(gt=0)],
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    """Return an order only when it belongs to the authenticated user."""

    order = OrderService(session).get_order_for_user(
        order_id=order_id,
        user_id=current_user.id,
    )
    return OrderResponse.model_validate(order)
