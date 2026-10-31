from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.agent.schemas import ConversationAction, ToolResultSummary
from backend.app.models.enums import SenderType, SessionStatus, WorkflowState
from backend.app.schemas.handoff import HandoffResponse


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
    assistant_message: ChatMessageResponse | None
    action: ConversationAction = ConversationAction.ANSWER
    workflow_state: WorkflowState = WorkflowState.COLLECTING_INFO
    missing_slots: list[str] = Field(default_factory=list)
    tool_results: list[ToolResultSummary] = Field(default_factory=list)
    handoff: HandoffResponse | None = None
