from datetime import UTC, datetime, timedelta
from decimal import Decimal

from backend.app.models import Product
from backend.app.models.entities import Order
from backend.app.models.enums import AfterSalesEligibilityStatus
from backend.app.services.after_sales_eligibility import AfterSalesEligibilityService


def _order(
    *,
    product_name: str,
    delivered_days_ago: int | None,
    status: str = "delivered",
) -> Order:
    delivered_at = (
        datetime.now(UTC) - timedelta(days=delivered_days_ago)
        if delivered_days_ago is not None
        else None
    )
    return Order(
        order_no="A10086",
        user_id=1,
        status=status,
        delivered_at=delivered_at,
        paid_amount=Decimal("899.00"),
        shipping_amount=Decimal("0.00"),
        currency="CNY",
        product=Product(name=product_name, description=""),
    )


def test_return_inside_quality_window_is_eligible_with_amount_snapshot():
    result = AfterSalesEligibilityService().evaluate(
        order=_order(product_name="SmartShop 降噪耳机 Pro", delivered_days_ago=3),
        request_type="return",
        issue_description="左耳没有声音",
    )

    assert result.result == AfterSalesEligibilityStatus.ELIGIBLE
    assert result.reason_code == "QUALITY_RETURN_WINDOW_ACTIVE"
    assert result.refund_amount == Decimal("899.00")
    assert result.currency == "CNY"


def test_exchange_has_zero_refund_amount():
    result = AfterSalesEligibilityService().evaluate(
        order=_order(product_name="SmartShop 机械键盘 K87", delivered_days_ago=2),
        request_type="exchange",
        issue_description="按键失灵",
    )

    assert result.result == AfterSalesEligibilityStatus.ELIGIBLE
    assert result.refund_amount == Decimal("0.00")


def test_after_return_window_but_inside_warranty_requires_human_review():
    result = AfterSalesEligibilityService().evaluate(
        order=_order(product_name="SmartShop 降噪耳机 Pro", delivered_days_ago=40),
        request_type="return",
        issue_description="左耳没有声音",
    )

    assert result.result == AfterSalesEligibilityStatus.NEED_HUMAN_REVIEW
    assert result.reason_code == "WARRANTY_REVIEW_REQUIRED"
    assert result.refund_amount is None


def test_expired_warranty_is_not_eligible():
    result = AfterSalesEligibilityService().evaluate(
        order=_order(product_name="SmartShop 27 英寸显示器", delivered_days_ago=1200),
        request_type="warranty",
        issue_description="屏幕亮点",
    )

    assert result.result == AfterSalesEligibilityStatus.NOT_ELIGIBLE
    assert result.reason_code == "WARRANTY_EXPIRED"


def test_missing_delivery_time_requires_human_review():
    result = AfterSalesEligibilityService().evaluate(
        order=_order(
            product_name="SmartShop 降噪耳机 Pro",
            delivered_days_ago=None,
        ),
        request_type="return",
        issue_description="左耳没有声音",
    )

    assert result.result == AfterSalesEligibilityStatus.NEED_HUMAN_REVIEW
    assert result.reason_code == "DELIVERY_TIME_MISSING"


def test_undelivered_order_requires_human_review():
    result = AfterSalesEligibilityService().evaluate(
        order=_order(
            product_name="SmartShop 机械键盘 K87",
            delivered_days_ago=None,
            status="shipped",
        ),
        request_type="return",
        issue_description="按键失灵",
    )

    assert result.result == AfterSalesEligibilityStatus.NEED_HUMAN_REVIEW
    assert result.reason_code == "ORDER_NOT_DELIVERED"


def test_damage_with_safety_or_human_factor_requires_review():
    result = AfterSalesEligibilityService().evaluate(
        order=_order(product_name="SmartShop 降噪耳机 Pro", delivered_days_ago=3),
        request_type="return",
        issue_description="耳机进水后左耳没有声音",
    )

    assert result.result == AfterSalesEligibilityStatus.NEED_HUMAN_REVIEW
    assert result.reason_code == "MANUAL_DAMAGE_REVIEW_REQUIRED"
