from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Order


def get_order_owned_by_user(
    session: Session,
    *,
    order_id: int,
    user_id: int,
) -> Order | None:
    statement = (
        select(Order)
        .options(selectinload(Order.product))
        .where(
            Order.id == order_id,
            Order.user_id == user_id,
        )
    )
    return session.scalar(statement)


def get_order_owned_by_user_and_no(
    session: Session,
    *,
    order_no: str,
    user_id: int,
) -> Order | None:
    """Return an order by business number only when the user owns it."""

    statement = (
        select(Order)
        .options(selectinload(Order.product))
        .where(
            Order.order_no == order_no,
            Order.user_id == user_id,
        )
    )
    return session.scalar(statement)
