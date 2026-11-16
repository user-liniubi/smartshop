from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from backend.app.models.enums import OrderStatus


class OrderProductResponse(BaseModel):
    id: int
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    order_no: str
    status: OrderStatus
    product: OrderProductResponse
    delivered_at: datetime | None
    paid_amount: Decimal
    shipping_amount: Decimal
    currency: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
