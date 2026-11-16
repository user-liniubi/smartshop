from enum import StrEnum


class UserRole(StrEnum):
    CONSUMER = "consumer"
    AGENT = "agent"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class SessionStatus(StrEnum):
    OPEN = "open"
    NEED_HUMAN = "need_human"
    HUMAN_ACTIVE = "human_active"
    CLOSED = "closed"


class WorkflowState(StrEnum):
    COLLECTING_INFO = "collecting_info"
    AWAITING_ORDER_SELECTION = "awaiting_order_selection"
    CHECKING_ORDER = "checking_order"
    CHECKING_POLICY = "checking_policy"
    ANSWER_READY = "answer_ready"
    NEED_HUMAN = "need_human"
    RESOLVED = "resolved"


class OrderSelectionState(StrEnum):
    NONE = "none"
    AWAITING_SELECTION = "awaiting_selection"
    SELECTED = "selected"


class SenderType(StrEnum):
    CONSUMER = "consumer"
    AGENT = "agent"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class HandoffStatus(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    CLOSED = "closed"


class KnowledgeDocumentStatus(StrEnum):
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class IngestionJobStatus(StrEnum):
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"


class ToolInvocationStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"


class HandoffSource(StrEnum):
    USER = "user"
    AI = "ai"
    RULE = "rule"


class AfterSalesTicketType(StrEnum):
    RETURN = "return"
    EXCHANGE = "exchange"


class AfterSalesEligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    NEED_HUMAN_REVIEW = "need_human_review"
    NOT_ELIGIBLE = "not_eligible"


class AfterSalesTicketEventType(StrEnum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    SYSTEM_NOTE = "system_note"


class AfterSalesActorType(StrEnum):
    CONSUMER = "consumer"
    AGENT = "agent"
    SYSTEM = "system"


class AfterSalesTicketStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
