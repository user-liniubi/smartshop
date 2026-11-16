from collections.abc import Sequence

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


def list_recent_orders_owned_by_user(
    session: Session,
    *,
    user_id: int,
    limit: int = 10,
) -> list[Order]:
    """Return recent orders only from the authenticated user's account."""

    statement = (
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
    )
    return list(session.scalars(statement))


def list_orders_owned_by_user_ids(
    session: Session,
    *,
    user_id: int,
    order_ids: Sequence[int],
) -> list[Order]:
    """Load candidate orders without trusting previously stored ownership."""

    if not order_ids:
        return []
    statement = (
        select(Order)
        .options(selectinload(Order.product))
        .where(
            Order.user_id == user_id,
            Order.id.in_(order_ids),
        )
    )
    orders = list(session.scalars(statement))
    order_by_id = {order.id: order for order in orders}
    return [order_by_id[order_id] for order_id in order_ids if order_id in order_by_id]
