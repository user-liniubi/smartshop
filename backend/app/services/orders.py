from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppError
from backend.app.models import Order
from backend.app.repositories.orders import (
    get_order_owned_by_user,
    get_order_owned_by_user_and_no,
)


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_order_for_user(self, *, order_id: int, user_id: int) -> Order:
        order = get_order_owned_by_user(
            self.session,
            order_id=order_id,
            user_id=user_id,
        )
        if order is None:
            raise AppError(
                status_code=404,
                code="order_not_found",
                message="订单不存在",
            )
        return order

    def get_order_for_user_by_no(self, *, order_no: str, user_id: int) -> Order:
        order = get_order_owned_by_user_and_no(
            self.session,
            order_no=order_no,
            user_id=user_id,
        )
        if order is None:
            raise AppError(
                status_code=404,
                code="order_not_found",
                message="订单不存在",
            )
        return order
