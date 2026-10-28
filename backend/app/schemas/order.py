from datetime import datetime

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
