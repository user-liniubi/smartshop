from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.api.dependencies import CurrentUser
from backend.app.db.session import get_db
from backend.app.schemas.order import OrderResponse
from backend.app.services.orders import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


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
