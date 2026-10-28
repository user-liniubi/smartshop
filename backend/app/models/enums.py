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


class SenderType(StrEnum):
    CONSUMER = "consumer"
    AGENT = "agent"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class HandoffStatus(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    CLOSED = "closed"
