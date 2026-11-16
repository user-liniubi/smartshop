from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from backend.app.models import AfterSalesEligibilityStatus, AfterSalesTicketType, Order
from backend.app.schemas.after_sales import AfterSalesEligibilityResponse

RULE_VERSION = "consumer-electronics-v1"
QUALITY_RETURN_WINDOW_DAYS = 15


@dataclass(frozen=True)
class ProductWarrantyRule:
    product_keyword: str
    display_name: str
    warranty_months: int


PRODUCT_WARRANTY_RULES = (
    ProductWarrantyRule("耳机", "耳机", 12),
    ProductWarrantyRule("键盘", "键盘", 12),
    ProductWarrantyRule("显示器", "显示器", 36),
    ProductWarrantyRule("笔记本", "笔记本", 24),
    ProductWarrantyRule("鼠标", "鼠标", 12),
)

_HUMAN_REVIEW_DAMAGE_KEYWORDS = {
    "进水",
    "液体",
    "摔",
    "私自拆",
    "拆机",
    "人为",
    "烧焦",
    "冒烟",
    "鼓包",
    "发热",
}


@dataclass(frozen=True)
class AfterSalesEligibility:
    result: AfterSalesEligibilityStatus
    reason_code: str
    explanation: str
    refund_amount: Decimal | None
    currency: str
    rule_version: str = RULE_VERSION

    def to_response(self) -> AfterSalesEligibilityResponse:
        return AfterSalesEligibilityResponse(
            result=self.result,
            reason_code=self.reason_code,
            explanation=self.explanation,
            refund_amount=self.refund_amount,
            currency=self.currency,
            rule_version=self.rule_version,
        )


class AfterSalesEligibilityService:
    """Apply deterministic after-sales eligibility and amount rules."""

    def evaluate(
        self,
        *,
        order: Order,
        request_type: str,
        issue_description: str,
        now: datetime | None = None,
    ) -> AfterSalesEligibility:
        currency = order.currency or "CNY"
        if order.status == "cancelled":
            return self._need_human(
                reason_code="ORDER_CANCELLED",
                explanation="订单已取消，需要人工核实历史签收和售后责任。",
                currency=currency,
            )
        if order.status != "delivered":
            return self._need_human(
                reason_code="ORDER_NOT_DELIVERED",
                explanation="订单尚未完成签收，暂时不能自动进入退换货审批。",
                currency=currency,
            )
        if order.delivered_at is None:
            return self._need_human(
                reason_code="DELIVERY_TIME_MISSING",
                explanation="订单缺少签收时间，无法自动计算售后期限。",
                currency=currency,
            )

        product_rule = self._product_rule(order.product.name)
        if product_rule is None:
            return self._need_human(
                reason_code="PRODUCT_RULE_MISSING",
                explanation="当前商品缺少结构化售后规则，需要人工核实。",
                currency=currency,
            )

        delivered_at = _aware_datetime(order.delivered_at)
        current_time = _aware_datetime(now or datetime.now(UTC))
        elapsed_days = (
            current_time.astimezone(ZoneInfo("Asia/Shanghai")).date()
            - delivered_at.astimezone(ZoneInfo("Asia/Shanghai")).date()
        ).days
        if elapsed_days < 0:
            return self._need_human(
                reason_code="INVALID_DELIVERY_TIME",
                explanation="签收时间晚于当前时间，需要人工核实订单数据。",
                currency=currency,
            )

        if any(keyword in issue_description for keyword in _HUMAN_REVIEW_DAMAGE_KEYWORDS):
            return self._need_human(
                reason_code="MANUAL_DAMAGE_REVIEW_REQUIRED",
                explanation="故障描述涉及人为损坏或安全风险，需要人工检测确认。",
                currency=currency,
            )

        warranty_days = product_rule.warranty_months * 30
        if request_type == "warranty":
            if elapsed_days <= warranty_days:
                return AfterSalesEligibility(
                    result=AfterSalesEligibilityStatus.ELIGIBLE,
                    reason_code="WARRANTY_ACTIVE",
                    explanation=(
                        f"{product_rule.display_name}仍在 {product_rule.warranty_months} 个月"
                        "质保期内，是否属于免费保修仍需人工检测确认。"
                    ),
                    refund_amount=None,
                    currency=currency,
                )
            return AfterSalesEligibility(
                result=AfterSalesEligibilityStatus.NOT_ELIGIBLE,
                reason_code="WARRANTY_EXPIRED",
                explanation=(
                    f"签收后已超过 {product_rule.warranty_months} 个月质保期，"
                    "系统不能自动认定免费保修资格。"
                ),
                refund_amount=None,
                currency=currency,
            )

        if request_type not in {
            AfterSalesTicketType.RETURN.value,
            AfterSalesTicketType.EXCHANGE.value,
        }:
            return self._need_human(
                reason_code="UNSUPPORTED_EVALUATION_TYPE",
                explanation="当前售后类型缺少自动资格规则，需要人工核实。",
                currency=currency,
            )

        if elapsed_days <= QUALITY_RETURN_WINDOW_DAYS:
            if request_type == AfterSalesTicketType.RETURN.value:
                if order.paid_amount <= Decimal("0.00"):
                    return self._need_human(
                        reason_code="REFUND_AMOUNT_MISSING",
                        explanation="订单实付金额缺失，无法生成可核验的退款金额快照。",
                        currency=currency,
                    )
                refund_amount = order.paid_amount.quantize(Decimal("0.01"))
            else:
                refund_amount = Decimal("0.00")
            return AfterSalesEligibility(
                result=AfterSalesEligibilityStatus.ELIGIBLE,
                reason_code="QUALITY_RETURN_WINDOW_ACTIVE",
                explanation=(
                    f"商品在签收后 {QUALITY_RETURN_WINDOW_DAYS} 天质量问题窗口内，"
                    "可以进入人工审批，不代表退款已经完成。"
                ),
                refund_amount=refund_amount,
                currency=currency,
            )

        if elapsed_days <= warranty_days:
            return self._need_human(
                reason_code="WARRANTY_REVIEW_REQUIRED",
                explanation=("已超过自动退换货窗口但仍在质保期内，需要人工判断维修或换货方案。"),
                currency=currency,
            )
        return AfterSalesEligibility(
            result=AfterSalesEligibilityStatus.NOT_ELIGIBLE,
            reason_code="WARRANTY_EXPIRED",
            explanation="签收后已超过商品质保期，系统不能自动受理本次退换货申请。",
            refund_amount=None,
            currency=currency,
        )

    @staticmethod
    def _product_rule(product_name: str) -> ProductWarrantyRule | None:
        return next(
            (rule for rule in PRODUCT_WARRANTY_RULES if rule.product_keyword in product_name),
            None,
        )

    @staticmethod
    def _need_human(
        *,
        reason_code: str,
        explanation: str,
        currency: str,
    ) -> AfterSalesEligibility:
        return AfterSalesEligibility(
            result=AfterSalesEligibilityStatus.NEED_HUMAN_REVIEW,
            reason_code=reason_code,
            explanation=explanation,
            refund_amount=None,
            currency=currency,
        )


def _aware_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
