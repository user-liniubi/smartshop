import json
import logging
import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from backend.app.agent.schemas import (
    AfterSalesIntent,
    IntentResult,
    IssueType,
    SlotUpdate,
)
from backend.app.services.llm import DeepSeekClient

logger = logging.getLogger(__name__)

_LABELED_ORDER_NO = re.compile(
    r"(?:订单(?:号)?|order(?:\s*(?:no|number))?)\s*[:：]?\s*"
    r"([A-Za-z0-9_-]{4,32})",
    re.IGNORECASE,
)
_BARE_ORDER_NO = re.compile(
    r"(?<![A-Za-z0-9_-])([A-Za-z]\d{5,31})(?![A-Za-z0-9_-])",
)
_GENERIC_ISSUE_DESCRIPTION_PATTERN = re.compile(
    r"^(?:我的)?(?:耳机)?(?:坏了|有问题|不能用了)"
    r"(?:\s*[，,。]?\s*(?:想|要)?(?:退货|换货|退款))?[。！!]?$"
)
_PRODUCT_USAGE_KEYWORDS = {
    "内存",
    "接口",
    "续航",
    "连接",
    "清洁",
    "使用",
}
_EXPLICIT_RETURN_OR_EXCHANGE_KEYWORDS = {
    "退货",
    "退款",
    "换货",
}


def extract_order_no(content: str) -> str | None:
    """Extract an order number deterministically before model validation."""

    match = _LABELED_ORDER_NO.search(content) or _BARE_ORDER_NO.search(content)
    return match.group(1).upper() if match else None


def parse_intent_result(content: str) -> IntentResult:
    """Parse a JSON-only model response, tolerating an accidental code fence."""

    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", maxsplit=1)[1] if "\n" in stripped else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3].rstrip()
    return IntentResult.model_validate(json.loads(stripped))


def merge_slots(
    *,
    existing: Mapping[str, Any] | None,
    updates: SlotUpdate,
    fallback_order_no: str | None,
) -> SlotUpdate:
    """Merge valid non-empty values without erasing previously collected slots."""

    existing_values = existing or {}
    merged: dict[str, Any] = {}
    for field_name in SlotUpdate.model_fields:
        update_value = getattr(updates, field_name)
        candidate = update_value
        if (
            field_name == "issue_type"
            and update_value in {IssueType.ORDER_QUERY, IssueType.UNKNOWN}
            and existing_values.get(field_name)
            not in {None, IssueType.ORDER_QUERY.value, IssueType.UNKNOWN.value}
        ):
            candidate = existing_values.get(field_name)
        if not _has_value(candidate):
            candidate = existing_values.get(field_name)
        if not _has_value(candidate):
            continue
        try:
            validated = SlotUpdate.model_validate({field_name: candidate})
        except ValidationError:
            continue
        merged[field_name] = getattr(validated, field_name)

    if fallback_order_no and fallback_order_no != merged.get("order_no"):
        merged["order_no"] = fallback_order_no
    return SlotUpdate.model_validate(merged)


class IntentService:
    def __init__(self, llm: DeepSeekClient) -> None:
        self.llm = llm

    async def extract(
        self,
        *,
        content: str,
        existing_slots: Mapping[str, Any] | None = None,
    ) -> IntentResult:
        fallback_order_no = extract_order_no(content)
        try:
            raw_result = await self.llm.extract_intent(
                message=content,
                existing_slots=existing_slots or {},
            )
            result = parse_intent_result(raw_result)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            logger.warning("Intent output was invalid and has been downgraded")
            fallback_intent = _fallback_intent(content)
            result = IntentResult(
                intent=fallback_intent,
                slots=SlotUpdate(
                    issue_type=(
                        IssueType.PRODUCT_USAGE
                        if fallback_intent == AfterSalesIntent.AFTER_SALES_POLICY
                        and any(
                            keyword in content
                            for keyword in ("内存", "接口", "续航", "连接", "清洁", "使用")
                        )
                        else None
                    )
                ),
                confidence=0,
            )

        slots = merge_slots(
            existing=existing_slots,
            updates=result.slots,
            fallback_order_no=fallback_order_no,
        )
        if slots.issue_description and _GENERIC_ISSUE_DESCRIPTION_PATTERN.fullmatch(
            slots.issue_description.strip()
        ):
            slots = slots.model_copy(update={"issue_description": None})
        effective_intent = result.intent
        if (
            any(keyword in content for keyword in _PRODUCT_USAGE_KEYWORDS)
            and not any(keyword in content for keyword in _EXPLICIT_RETURN_OR_EXCHANGE_KEYWORDS)
            and result.intent
            in {
                AfterSalesIntent.UNKNOWN,
                AfterSalesIntent.EXCHANGE_REQUEST,
            }
        ):
            effective_intent = AfterSalesIntent.AFTER_SALES_POLICY
            slots = slots.model_copy(update={"issue_type": IssueType.PRODUCT_USAGE})
        return IntentResult(
            intent=effective_intent,
            slots=slots,
            confidence=result.confidence,
        )


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _fallback_intent(content: str) -> AfterSalesIntent:
    normalized = content.lower()
    if any(keyword in content for keyword in ("人工", "客服")):
        return AfterSalesIntent.HUMAN_REQUEST
    if any(keyword in content for keyword in ("换货", "更换")):
        return AfterSalesIntent.EXCHANGE_REQUEST
    if any(keyword in content for keyword in ("退货", "退款")):
        return AfterSalesIntent.RETURN_REQUEST
    if any(keyword in normalized for keyword in ("保修", "质保", "warranty")):
        return AfterSalesIntent.WARRANTY_QUESTION
    if any(
        keyword in content
        for keyword in (
            "内存",
            "接口",
            "续航",
            "连接",
            "清洁",
            "使用",
            "发货",
            "配送",
            "运费",
            "政策",
        )
    ):
        return AfterSalesIntent.AFTER_SALES_POLICY
    return AfterSalesIntent.UNKNOWN
