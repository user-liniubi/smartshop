from backend.app.agent.schemas import AfterSalesIntent
from backend.app.services.rules import AfterSalesRuleService


def test_cancelled_order_requires_handoff():
    decision = AfterSalesRuleService().enforce(
        answer="可以申请退货。",
        intent=AfterSalesIntent.RETURN_REQUEST,
        order_facts={"status": "cancelled"},
        policy_grounded=True,
    )

    assert decision.handoff_required is True
    assert decision.handoff_reason == "订单状态异常，需要人工复核"


def test_missing_policy_evidence_requires_handoff():
    decision = AfterSalesRuleService().enforce(
        answer="",
        intent=AfterSalesIntent.WARRANTY_QUESTION,
        order_facts=None,
        policy_grounded=False,
    )

    assert decision.handoff_required is True
    assert "没有足够政策依据" in decision.answer


def test_model_cannot_claim_real_refund_was_completed():
    decision = AfterSalesRuleService().enforce(
        answer="已经退款，请查收。",
        intent=AfterSalesIntent.RETURN_REQUEST,
        order_facts={"status": "delivered"},
        policy_grounded=True,
    )

    assert decision.handoff_required is True
    assert "不会执行真实退款" in decision.answer


def test_safe_answer_passes_through():
    decision = AfterSalesRuleService().enforce(
        answer="根据政策，建议先联系客服核验质量问题。[1]",
        intent=AfterSalesIntent.RETURN_REQUEST,
        order_facts={"status": "delivered"},
        policy_grounded=True,
    )

    assert decision.handoff_required is False
    assert decision.answer.startswith("根据政策")
