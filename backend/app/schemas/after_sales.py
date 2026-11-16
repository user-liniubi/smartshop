from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import (
    AfterSalesActorType,
    AfterSalesEligibilityStatus,
    AfterSalesTicketEventType,
    AfterSalesTicketStatus,
    AfterSalesTicketType,
)


class AfterSalesEligibilityResponse(BaseModel):
    result: AfterSalesEligibilityStatus
    reason_code: str
    explanation: str
    refund_amount: Decimal | None = None
    currency: str
    rule_version: str


class AfterSalesTicketResponse(BaseModel):
    id: int
    ticket_no: str
    session_id: int
    user_id: int
    order_id: int
    request_type: AfterSalesTicketType
    issue_description: str
    policy_citations: list[dict] = Field(default_factory=list)
    eligibility_result: AfterSalesEligibilityStatus | None
    eligibility_reason: str | None
    refund_amount: Decimal | None
    currency: str
    rule_version: str | None
    status: AfterSalesTicketStatus
    reviewer_id: int | None
    review_note: str | None
    reviewed_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AfterSalesTicketReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_note: str = Field(default="", max_length=500)


class AfterSalesTicketEventResponse(BaseModel):
    id: int
    ticket_id: int
    event_type: AfterSalesTicketEventType
    from_status: AfterSalesTicketStatus | None
    to_status: AfterSalesTicketStatus | None
    actor_type: AfterSalesActorType
    actor_id: int | None
    note: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
