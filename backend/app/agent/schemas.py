from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.enums import WorkflowState


class AfterSalesIntent(StrEnum):
    AFTER_SALES_POLICY = "after_sales_policy"
    ORDER_QUERY = "order_query"
    RETURN_REQUEST = "return_request"
    EXCHANGE_REQUEST = "exchange_request"
    WARRANTY_QUESTION = "warranty_question"
    HUMAN_REQUEST = "human_request"
    UNKNOWN = "unknown"


class IssueType(StrEnum):
    RETURN = "return"
    EXCHANGE = "exchange"
    WARRANTY = "warranty"
    DELIVERY = "delivery"
    PRODUCT_USAGE = "product_usage"
    ORDER_QUERY = "order_query"
    UNKNOWN = "unknown"


class SlotUpdate(BaseModel):
    """Validated after-sales slots extracted from one conversation turn."""

    model_config = ConfigDict(extra="forbid")

    order_no: str | None = Field(
        default=None,
        min_length=4,
        max_length=32,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    issue_type: IssueType | None = None
    issue_description: str | None = Field(default=None, max_length=1000)

    @field_validator("order_no", "issue_description", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("order_no")
    @classmethod
    def normalize_order_no(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class IntentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: AfterSalesIntent
    slots: SlotUpdate = Field(default_factory=SlotUpdate)
    confidence: float = Field(ge=0, le=1)


class WorkflowAction(StrEnum):
    ASK_MORE_INFO = "ask_more_info"
    QUERY_ORDER = "query_order"
    RETRIEVE_POLICY = "retrieve_policy"
    HANDOFF = "handoff"


class OrchestrationDecision(BaseModel):
    action: WorkflowAction
    workflow_state: WorkflowState
    missing_slots: list[str] = Field(default_factory=list)
    reply_text: str | None = None


class GetMyOrderArguments(BaseModel):
    """Arguments visible to the model for the owned-order query tool."""

    model_config = ConfigDict(extra="forbid")

    order_no: str = Field(
        min_length=4,
        max_length=32,
        pattern=r"^[A-Za-z0-9_-]+$",
    )


class ToolExecutionResult(BaseModel):
    tool_name: str
    result: dict[str, Any]
