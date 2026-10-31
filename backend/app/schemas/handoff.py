from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import HandoffSource, HandoffStatus


class HandoffRequest(BaseModel):
    reason: str = Field(default="用户主动申请人工客服", max_length=500)


class HandoffResponse(BaseModel):
    id: int
    session_id: int
    status: HandoffStatus
    source: HandoffSource
    reason: str
    agent_id: int | None
    claimed_at: datetime | None
    closed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
