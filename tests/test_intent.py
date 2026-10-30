import asyncio

from backend.app.agent.intent import IntentService, extract_order_no, merge_slots
from backend.app.agent.schemas import AfterSalesIntent, IssueType, SlotUpdate


class FakeIntentClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.request: dict | None = None

    async def extract_intent(
        self,
        *,
        message: str,
        existing_slots: dict,
    ) -> str:
        self.request = {
            "message": message,
            "existing_slots": existing_slots,
        }
        return self.response


def test_intent_service_extracts_return_intent_and_slots():
    client = FakeIntentClient(
        '{"intent":"return_request","slots":{"order_no":"A10086",'
        '"issue_type":"return","issue_description":"左耳没有声音"},'
        '"confidence":0.93}'
    )

    result = asyncio.run(
        IntentService(client).extract(
            content="订单 A10086 的耳机坏了，我想退货，左耳没有声音",
        )
    )

    assert result.intent == AfterSalesIntent.RETURN_REQUEST
    assert result.slots.order_no == "A10086"
    assert result.slots.issue_type == IssueType.RETURN
    assert result.slots.issue_description == "左耳没有声音"
    assert result.confidence == 0.93
    assert client.request is not None
    assert "A10086" in client.request["message"]


def test_intent_service_preserves_existing_slots_on_empty_updates():
    client = FakeIntentClient(
        '{"intent":"warranty_question","slots":{"order_no":"",'
        '"issue_type":null,"issue_description":""},"confidence":0.8}'
    )

    result = asyncio.run(
        IntentService(client).extract(
            content="它还在保修期内吗",
            existing_slots={
                "order_no": "A10086",
                "issue_type": "return",
                "issue_description": "左耳没有声音",
            },
        )
    )

    assert result.intent == AfterSalesIntent.WARRANTY_QUESTION
    assert result.slots == SlotUpdate(
        order_no="A10086",
        issue_type=IssueType.RETURN,
        issue_description="左耳没有声音",
    )


def test_intent_service_uses_deterministic_order_number_when_model_omits_it():
    client = FakeIntentClient('{"intent":"order_query","slots":{},"confidence":0.88}')

    result = asyncio.run(
        IntentService(client).extract(
            content="帮我看看订单号：A10087 到哪了",
        )
    )

    assert result.intent == AfterSalesIntent.ORDER_QUERY
    assert result.slots.order_no == "A10087"


def test_invalid_model_json_becomes_unknown_without_crashing():
    client = FakeIntentClient("这不是 JSON")

    result = asyncio.run(
        IntentService(client).extract(
            content="订单 A10086 的耳机有问题",
        )
    )

    assert result.intent == AfterSalesIntent.UNKNOWN
    assert result.confidence == 0
    assert result.slots.order_no == "A10086"


def test_intent_service_accepts_json_inside_markdown_fence():
    client = FakeIntentClient('```json\n{"intent":"human_request","slots":{},"confidence":1}\n```')

    result = asyncio.run(IntentService(client).extract(content="我要人工"))

    assert result.intent == AfterSalesIntent.HUMAN_REQUEST


def test_order_number_extraction_supports_labeled_and_bare_values():
    assert extract_order_no("订单号：a10086") == "A10086"
    assert extract_order_no("查一下 A10087 的状态") == "A10087"
    assert extract_order_no("耳机保修多久") is None


def test_merge_slots_ignores_invalid_existing_values():
    result = merge_slots(
        existing={
            "order_no": "A10086",
            "issue_type": "not-a-valid-type",
            "issue_description": "左耳没有声音",
        },
        updates=SlotUpdate(),
        fallback_order_no=None,
    )

    assert result.order_no == "A10086"
    assert result.issue_type is None
    assert result.issue_description == "左耳没有声音"
