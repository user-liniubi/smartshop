from pydantic import BaseModel

from backend.app.schemas.chat import ChatMessageResponse, ChatSessionResponse
from backend.app.schemas.handoff import HandoffResponse
from backend.app.schemas.order import OrderResponse


class AgentSessionContextResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]
    handoff: HandoffResponse
    order: OrderResponse | None = None
