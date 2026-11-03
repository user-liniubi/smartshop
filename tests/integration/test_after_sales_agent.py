import asyncio
import json

from sqlalchemy import select

from backend.app.agent.intent import extract_order_no
from backend.app.agent.schemas import ConversationAction
from backend.app.agent.service import AfterSalesAgentService
from backend.app.core.config import Settings
from backend.app.core.exceptions import AppError
from backend.app.models import ChatSession, ToolInvocation, User, WorkflowState
from backend.app.repositories.chat import list_messages
from backend.app.schemas.rag import CitationResponse
from backend.app.services.handoffs import HandoffService
from backend.app.services.rag import RAGContext


class FakeAgentLLM:
    def __init__(
        self,
        *,
        fail_answer: bool = False,
        fail_intent: bool = False,
    ) -> None:
        self.fail_answer = fail_answer
        self.fail_intent = fail_intent
        self.answer_requests: list[dict] = []

    async def extract_intent(self, *, message: str, existing_slots: dict) -> str:
        if self.fail_intent:
            raise AppError(
                status_code=503,
                code="model_timeout",
                message="Intent model timeout",
            )
        order_no = extract_order_no(message)
        if "左耳" in message:
            payload = {
                "intent": "return_request",
                "slots": {
                    "order_no": order_no,
                    "issue_type": "return",
                    "issue_description": "左耳没有声音",
                },
                "confidence": 0.96,
            }
        elif order_no:
            payload = {
                "intent": "after_sales_policy",
                "slots": {
                    "order_no": order_no,
                    "issue_type": "order_query",
                },
                "confidence": 0.95,
            }
        elif "想退货" in message:
            payload = {
                "intent": "return_request",
                "slots": {"issue_type": "return", "issue_description": "耳机坏了"},
                "confidence": 0.92,
            }
        elif "人工" in message:
            payload = {
                "intent": "human_request",
                "slots": {},
                "confidence": 0.99,
            }
        else:
            payload = {
                "intent": "after_sales_policy",
                "slots": {},
                "confidence": 0.8,
            }
        return json.dumps(payload, ensure_ascii=False)

    async def plan_tool_call(self, *, message: str, tools: list[dict]):
        order_no = extract_order_no(message) or "A10086"
        return {
            "name": "get_my_order",
            "arguments": {"order_no": order_no},
        }

    async def generate_agent_answer(
        self,
        *,
        question: str,
        intent: str,
        order_facts: dict | None,
        evidence: str,
        history: list[dict[str, str]],
    ) -> str:
        self.answer_requests.append(
            {
                "question": question,
                "intent": intent,
                "order_facts": order_facts,
                "evidence": evidence,
                "history": history,
            }
        )
        if self.fail_answer:
            raise AppError(
                status_code=503,
                code="model_unavailable",
                message="AI unavailable",
            )
        return "订单 A10086 当前状态为 delivered。根据政策可先判断是否属于质量问题。[1]"


class FakeRagService:
    def __init__(self, *, grounded: bool = True) -> None:
        self.grounded = grounded
        self.requests: list[dict] = []

    async def retrieve(
        self,
        *,
        question: str,
        product_id: int | None = None,
        top_k: int | None = None,
    ) -> RAGContext:
        self.requests.append(
            {
                "question": question,
                "product_id": product_id,
                "top_k": top_k,
            }
        )
        if not self.grounded:
            return RAGContext(
                evidence="",
                citations=[],
                chunks=(),
                grounded=False,
            )
        citation = CitationResponse(
            document_id=2,
            chunk_id="[1] 2:1",
            filename="warranty_policy.md",
            title="质保规则",
            heading="各品类期限",
            excerpt="降噪耳机提供十二个月质保。",
            similarity=0.91,
        )
        return RAGContext(
            evidence="[1] 降噪耳机提供十二个月质保。",
            citations=[citation],
            chunks=(),
            grounded=True,
        )


def create_agent_session(test_database) -> tuple[int, int]:
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "consumer_demo"))
        assert user is not None
        chat_session = ChatSession(user_id=user.id)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return user.id, chat_session.id


def run_message(service, *, user_id: int, session_id: int, content: str):
    return asyncio.run(
        service.handle_message(
            session_id=session_id,
            user_id=user_id,
            content=content,
        )
    )


def test_three_turn_return_flow_combines_order_facts_and_policy(
    seeded_client,
    test_database,
):
    user_id, session_id = create_agent_session(test_database)
    llm = FakeAgentLLM()
    rag = FakeRagService()
    settings = Settings(_env_file=None)

    with test_database.session_factory() as session:
        service = AfterSalesAgentService(
            session=session,
            settings=settings,
            llm=llm,
            rag_service=rag,
        )
        first = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="耳机坏了，想退货",
        )
        second = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="订单号 A10086",
        )
        third = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="左耳没有声音",
        )
        invocation = session.scalar(select(ToolInvocation))
        task = session.get(ChatSession, session_id)

    assert first.action == ConversationAction.ASK_MORE_INFO
    assert set(first.missing_slots) == {"order_no", "issue_description"}
    assert second.action == ConversationAction.ASK_MORE_INFO
    assert second.missing_slots == ["issue_description"]
    assert third.action == ConversationAction.ANSWER
    assert third.assistant_message is not None
    assert "delivered" in third.assistant_message.content
    assert third.assistant_message.citations_json[0]["filename"] == ("warranty_policy.md")
    assert third.tool_results[0].result["order_no"] == "A10086"
    assert invocation is not None
    assert invocation.status == "success"
    assert task is not None
    assert task.intent == "return_request"
    assert task.workflow_state == WorkflowState.RESOLVED.value
    assert task.slots_json["product_id"] == 1
    assert rag.requests[0]["product_id"] == 1


def test_other_users_order_is_not_exposed_and_can_be_retried(
    seeded_client,
    test_database,
):
    user_id, session_id = create_agent_session(test_database)
    llm = FakeAgentLLM()
    rag = FakeRagService()

    with test_database.session_factory() as session:
        service = AfterSalesAgentService(
            session=session,
            settings=Settings(_env_file=None),
            llm=llm,
            rag_service=rag,
        )
        response = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="订单 A10088 左耳没有声音，想退货",
        )

    assert response.action == ConversationAction.ASK_MORE_INFO
    assert response.assistant_message is not None
    assert "未找到" in response.assistant_message.content
    assert response.tool_results[0].error_code == "order_not_found"


def test_cancelled_order_and_missing_policy_require_handoff(
    seeded_client,
    test_database,
):
    user_id, session_id = create_agent_session(test_database)
    llm = FakeAgentLLM()
    rag = FakeRagService(grounded=False)

    with test_database.session_factory() as session:
        service = AfterSalesAgentService(
            session=session,
            settings=Settings(_env_file=None),
            llm=llm,
            rag_service=rag,
        )
        response = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="订单 A10089 左耳没有声音，想退货",
        )

    assert response.action == ConversationAction.HANDOFF_CREATED
    assert response.handoff is not None
    assert response.handoff.source == "rule"
    assert response.handoff.status == "pending"
    assert response.workflow_state == WorkflowState.NEED_HUMAN
    assert llm.answer_requests == []


def test_model_failure_saves_message_and_creates_handoff(
    seeded_client,
    test_database,
):
    user_id, session_id = create_agent_session(test_database)
    llm = FakeAgentLLM(fail_answer=True)
    rag = FakeRagService()

    with test_database.session_factory() as session:
        service = AfterSalesAgentService(
            session=session,
            settings=Settings(_env_file=None),
            llm=llm,
            rag_service=rag,
        )
        response = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="订单 A10086 左耳没有声音，想退货",
        )

    assert response.action == ConversationAction.HANDOFF_CREATED
    assert response.handoff is not None
    assert response.handoff.source == "ai"
    assert response.assistant_message is not None
    assert "消息已保存" in response.assistant_message.content


def test_message_after_handoff_waits_without_ai_reply(
    seeded_client,
    test_database,
):
    user_id, session_id = create_agent_session(test_database)
    llm = FakeAgentLLM()

    with test_database.session_factory() as session:
        HandoffService(session).request_for_user(
            session_id=session_id,
            user_id=user_id,
            reason="用户主动申请",
        )
        service = AfterSalesAgentService(
            session=session,
            settings=Settings(_env_file=None),
            llm=llm,
            rag_service=FakeRagService(),
        )
        response = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="我还想补充一下",
        )
        messages = list_messages(session, session_id=session_id)

    assert response.action == ConversationAction.WAITING_FOR_AGENT
    assert response.assistant_message is None
    assert llm.answer_requests == []
    assert [(message.sender_type, message.content) for message in messages] == [
        ("consumer", "我还想补充一下")
    ]


def test_intent_model_failure_falls_back_to_handoff(
    seeded_client,
    test_database,
):
    user_id, session_id = create_agent_session(test_database)
    llm = FakeAgentLLM(fail_intent=True)

    with test_database.session_factory() as session:
        service = AfterSalesAgentService(
            session=session,
            settings=Settings(_env_file=None),
            llm=llm,
            rag_service=FakeRagService(),
        )
        response = run_message(
            service,
            user_id=user_id,
            session_id=session_id,
            content="我的耳机有问题",
        )

    assert response.action == ConversationAction.HANDOFF_CREATED
    assert response.handoff is not None
    assert response.handoff.source == "ai"
    assert response.assistant_message is not None
    assert "消息已保存" in response.assistant_message.content
