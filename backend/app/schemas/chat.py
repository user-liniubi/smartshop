from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import SenderType, SessionStatus, WorkflowState


class ChatSessionResponse(BaseModel):
    id: int
    status: SessionStatus
    intent: str | None
    slots_json: dict
    workflow_state: WorkflowState
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    id: int
    sender_type: SenderType
    content: str
    citations_json: list[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatTurnResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
