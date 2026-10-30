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
    CHECKING_ORDER = "checking_order"
    CHECKING_POLICY = "checking_policy"
    ANSWER_READY = "answer_ready"
    NEED_HUMAN = "need_human"
    RESOLVED = "resolved"


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


class ToolInvocationStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"
