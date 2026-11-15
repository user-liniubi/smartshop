from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import AfterSalesTicketStatus, AfterSalesTicketType


class AfterSalesTicketResponse(BaseModel):
    id: int
    ticket_no: str
    session_id: int
    user_id: int
    order_id: int
    request_type: AfterSalesTicketType
    issue_description: str
    policy_citations: list[dict] = Field(default_factory=list)
    status: AfterSalesTicketStatus
    reviewer_id: int | None
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AfterSalesTicketReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_note: str = Field(default="", max_length=500)
