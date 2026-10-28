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
