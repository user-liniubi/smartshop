import re
from dataclasses import dataclass
from typing import Any

from backend.app.agent.schemas import AfterSalesIntent

_FORBIDDEN_ACTION_PATTERN = re.compile(
    r"(已经退款|已退款|退款成功|已完成退货|已为您办理退货|已完成换货)"
)


@dataclass(frozen=True)
class RuleDecision:
    answer: str
    handoff_required: bool = False
    handoff_reason: str | None = None


class AfterSalesRuleService:
    """Apply deterministic safety boundaries around model-generated advice."""

    def enforce(
        self,
        *,
        answer: str,
        intent: AfterSalesIntent,
        order_facts: dict[str, Any] | None,
        policy_grounded: bool,
    ) -> RuleDecision:
        if order_facts and order_facts.get("status") == "cancelled":
            return RuleDecision(
                answer=(
                    "该订单已取消，订单状态不适合直接按普通退货流程判断。我已为你转接人工客服复核。"
                ),
                handoff_required=True,
                handoff_reason="订单状态异常，需要人工复核",
            )

        if intent != AfterSalesIntent.ORDER_QUERY and not policy_grounded:
            return RuleDecision(
                answer=(
                    "当前知识库没有足够政策依据给出确定性结论。"
                    "我已记录转人工请求，请等待客服进一步核实。"
                ),
                handoff_required=True,
                handoff_reason="缺少可核验的售后政策证据",
            )

        if _FORBIDDEN_ACTION_PATTERN.search(answer):
            return RuleDecision(
                answer=(
                    "系统不会执行真实退款或退换货操作。"
                    "现有信息只能作为售后建议，具体处理需要人工客服核实。"
                ),
                handoff_required=True,
                handoff_reason="模型输出包含越权业务承诺",
            )

        return RuleDecision(answer=answer)
