import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.app.agent.schemas import AfterSalesIntent, IntentResult
from backend.app.core.exceptions import AppError
from backend.app.models import (
    ChatSession,
    Order,
    OrderSelectionState,
)
from backend.app.repositories.chat import get_session_owned_by_user
from backend.app.repositories.orders import (
    get_order_owned_by_user,
    list_orders_owned_by_user_ids,
    list_recent_orders_owned_by_user,
)

_ORDER_INTENTS = {
    AfterSalesIntent.ORDER_QUERY,
    AfterSalesIntent.RETURN_REQUEST,
    AfterSalesIntent.EXCHANGE_REQUEST,
}
_ANOTHER_ORDER_PATTERN = re.compile(r"(另一笔|另一个|别的|不是这个|换一笔|下一笔)")
_ORDINAL_PATTERN = re.compile(r"第\s*([一二三四五六七八九十\d]+)\s*(?:笔|个|单|条)")
_CJK_BIGRAM_PATTERN = re.compile(r"[\u4e00-\u9fff]{2}")
_DATE_REFERENCES = {
    "今天": 0,
    "昨天": 1,
    "前天": 2,
}
_ORDINAL_VALUES = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


@dataclass(frozen=True)
class OrderContextResolution:
    awaiting_selection: bool
    candidates: tuple[Order, ...]
    selected_order: Order | None

    @property
    def prompt(self) -> str | None:
        if not self.awaiting_selection:
            return None
        lines = ["查询到您当前账号有多笔相关订单，请选择要处理的订单："]
        for order in self.candidates:
            lines.append(f"- {order.order_no}｜{order.product.name}｜{order.status}")
        lines.append("可以直接回复订单号、序号，或“另一笔”来切换。")
        return "\n".join(lines)


class OrderContextService:
    """Resolve ambiguous order references using only the authenticated user's orders."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def resolve_for_turn(
        self,
        *,
        chat_session: ChatSession,
        intent_result: IntentResult,
        content: str,
    ) -> OrderContextResolution:
        if intent_result.intent not in _ORDER_INTENTS or intent_result.slots.order_no:
            return OrderContextResolution(
                awaiting_selection=False,
                candidates=self._current_candidates(chat_session),
                selected_order=self._selected_order(chat_session),
            )

        reference = intent_result.slots.order_reference or _detect_reference(content)
        candidates = self._current_candidates(chat_session)
        has_switch_reference = bool(reference and _ANOTHER_ORDER_PATTERN.search(reference))
        if not candidates or not has_switch_reference:
            candidates = self._filter_product_candidates(
                list_recent_orders_owned_by_user(
                    self.session,
                    user_id=chat_session.user_id,
                    limit=10,
                ),
                content,
            )

        if reference:
            intent_result.slots = intent_result.slots.model_copy(
                update={"order_reference": reference}
            )

        selected = self._resolve_candidate(
            candidates=candidates,
            reference=reference,
            current_order_id=chat_session.selected_order_id,
        )
        if selected is None and len(candidates) == 1:
            selected = candidates[0]

        if selected is not None:
            self._mark_selected(chat_session, selected)
            intent_result.slots = intent_result.slots.model_copy(
                update={"order_no": selected.order_no, "order_reference": None}
            )
            return OrderContextResolution(
                awaiting_selection=False,
                candidates=tuple(candidates),
                selected_order=selected,
            )

        self._mark_awaiting_selection(chat_session, candidates)
        return OrderContextResolution(
            awaiting_selection=bool(candidates),
            candidates=tuple(candidates),
            selected_order=None,
        )

    def select_candidate(
        self,
        *,
        session_id: int,
        user_id: int,
        order_id: int,
    ) -> ChatSession:
        chat_session = get_session_owned_by_user(
            self.session,
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise AppError(
                status_code=404,
                code="chat_session_not_found",
                message="会话不存在",
            )
        if chat_session.order_selection_state != OrderSelectionState.AWAITING_SELECTION.value:
            raise AppError(
                status_code=409,
                code="order_selection_not_pending",
                message="当前会话没有等待选择的订单",
            )
        if order_id not in (chat_session.candidate_order_ids_json or []):
            raise AppError(
                status_code=409,
                code="order_candidate_invalid",
                message="所选订单不在当前候选列表中",
            )

        order = get_order_owned_by_user(
            self.session,
            order_id=order_id,
            user_id=user_id,
        )
        if order is None:
            raise AppError(
                status_code=404,
                code="order_not_found",
                message="订单不存在",
            )
        self._mark_selected(chat_session, order)
        self.session.commit()
        self.session.refresh(chat_session)
        return chat_session

    def on_order_verified(self, chat_session: ChatSession, order: Order) -> None:
        self._mark_selected(chat_session, order)
        candidate_ids = list(chat_session.candidate_order_ids_json or [])
        if order.id not in candidate_ids:
            candidate_ids.insert(0, order.id)
            chat_session.candidate_order_ids_json = candidate_ids[:10]

    def on_order_lookup_failed(self, chat_session: ChatSession) -> None:
        slots = dict(chat_session.slots_json or {})
        slots.pop("product_id", None)
        slots.pop("order_no", None)
        chat_session.slots_json = slots
        chat_session.selected_order_id = None
        chat_session.order_selection_state = OrderSelectionState.NONE.value

    def _current_candidates(self, chat_session: ChatSession) -> list[Order]:
        order_ids = list(chat_session.candidate_order_ids_json or [])
        return list_orders_owned_by_user_ids(
            self.session,
            user_id=chat_session.user_id,
            order_ids=order_ids,
        )

    def _selected_order(self, chat_session: ChatSession) -> Order | None:
        if chat_session.selected_order_id is None:
            return None
        return get_order_owned_by_user(
            self.session,
            order_id=chat_session.selected_order_id,
            user_id=chat_session.user_id,
        )

    @staticmethod
    def _filter_product_candidates(orders: list[Order], content: str) -> list[Order]:
        content_bigrams = set(_CJK_BIGRAM_PATTERN.findall(content))
        if not content_bigrams:
            return orders
        matched = [
            order
            for order in orders
            if content_bigrams.intersection(set(_CJK_BIGRAM_PATTERN.findall(order.product.name)))
        ]
        return matched or orders

    @staticmethod
    def _resolve_candidate(
        *,
        candidates: list[Order],
        reference: str | None,
        current_order_id: int | None,
    ) -> Order | None:
        if not candidates:
            return None
        normalized = (reference or "").strip()
        if not normalized:
            return candidates[0] if len(candidates) == 1 else None

        if _ANOTHER_ORDER_PATTERN.search(normalized):
            remaining = [order for order in candidates if order.id != current_order_id]
            return remaining[0] if len(remaining) == 1 else None

        ordinal_match = _ORDINAL_PATTERN.search(normalized)
        if ordinal_match:
            raw_index = ordinal_match.group(1)
            index = int(raw_index) if raw_index.isdigit() else _ORDINAL_VALUES.get(raw_index, 0)
            if 1 <= index <= len(candidates):
                return candidates[index - 1]

        for marker, day_offset in _DATE_REFERENCES.items():
            if marker not in normalized:
                continue
            target_date = _business_today() - timedelta(days=day_offset)
            matching = [
                order for order in candidates if _business_date(order.created_at) == target_date
            ]
            return matching[0] if len(matching) == 1 else None

        return None

    @staticmethod
    def _mark_selected(chat_session: ChatSession, order: Order) -> None:
        previous_order_id = chat_session.selected_order_id
        chat_session.selected_order_id = order.id
        chat_session.order_selection_state = OrderSelectionState.SELECTED.value
        slots = dict(chat_session.slots_json or {})
        slots["order_no"] = order.order_no
        if previous_order_id is not None and previous_order_id != order.id:
            slots.pop("product_id", None)
        chat_session.slots_json = slots

    @staticmethod
    def _mark_awaiting_selection(
        chat_session: ChatSession,
        candidates: list[Order],
    ) -> None:
        chat_session.candidate_order_ids_json = [order.id for order in candidates]
        chat_session.selected_order_id = None
        if candidates:
            chat_session.order_selection_state = OrderSelectionState.AWAITING_SELECTION.value
            slots = dict(chat_session.slots_json or {})
            slots.pop("order_no", None)
            slots.pop("product_id", None)
            chat_session.slots_json = slots
        else:
            chat_session.order_selection_state = OrderSelectionState.NONE.value


def _detect_reference(content: str) -> str | None:
    if _ANOTHER_ORDER_PATTERN.search(content):
        return content.strip()[:100]
    if _ORDINAL_PATTERN.search(content):
        return content.strip()[:100]
    for marker in _DATE_REFERENCES:
        if marker in content:
            return content.strip()[:100]
    return None


def _business_today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _business_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZoneInfo("Asia/Shanghai")).date()
