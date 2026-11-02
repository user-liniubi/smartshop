import asyncio
import json
import threading

from sqlalchemy import select

from backend.app.agent.schemas import ConversationAction
from backend.app.agent.service import AfterSalesAgentService
from backend.app.core.config import Settings
from backend.app.db.session import Database
from backend.app.models import Base, ChatSession, Handoff, User
from backend.app.repositories.chat import list_messages
from backend.app.schemas.rag import CitationResponse
from backend.app.services.handoffs import HandoffService
from backend.app.services.rag import RAGContext
from sample_data.seed import seed_demo_data


class BlockingAgentLLM:
    def __init__(self, ready: threading.Event, release: threading.Event) -> None:
        self.ready = ready
        self.release = release

    async def extract_intent(self, *, message: str, existing_slots: dict) -> str:
        return json.dumps(
            {
                "intent": "return_request",
                "slots": {
                    "order_no": "A10086",
                    "issue_type": "return",
                    "issue_description": "左耳没有声音",
                },
                "confidence": 0.95,
            }
        )

    async def plan_tool_call(self, *, message: str, tools: list[dict]):
        return {
            "name": "get_my_order",
            "arguments": {"order_no": "A10086"},
        }

    async def generate_agent_answer(self, **kwargs) -> str:
        self.ready.set()
        await asyncio.to_thread(self.release.wait)
        return "迟到的 AI 回复"


class GroundedRagService:
    async def retrieve(self, **kwargs) -> RAGContext:
        citation = CitationResponse(
            document_id=1,
            chunk_id="[1] 1:1",
            filename="warranty_policy.md",
            title="质保规则",
            excerpt="降噪耳机提供十二个月质保。",
            similarity=0.9,
        )
        return RAGContext(
            evidence="[1] 降噪耳机提供十二个月质保。",
            citations=[citation],
            chunks=(),
            grounded=True,
        )


def test_late_ai_response_is_discarded_after_human_claim(tmp_path):
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'late-ai.db'}")
    with database.engine.begin() as connection:
        Base.metadata.create_all(connection)

    with database.session_factory() as session:
        seed_demo_data(session)
        consumer = session.scalar(select(User).where(User.username == "consumer_demo"))
        agent = session.scalar(select(User).where(User.username == "agent_demo"))
        assert consumer is not None
        assert agent is not None
        chat_session = ChatSession(user_id=consumer.id)
        session.add(chat_session)
        session.flush()
        handoff = Handoff(session_id=chat_session.id, reason="并发测试")
        session.add(handoff)
        session.commit()
        session_id = chat_session.id
        handoff_id = handoff.id
        consumer_id = consumer.id
        agent_id = agent.id

    ready = threading.Event()
    release = threading.Event()
    response_holder: dict = {}

    def run_agent() -> None:
        with database.session_factory() as session:
            service = AfterSalesAgentService(
                session=session,
                settings=Settings(_env_file=None),
                llm=BlockingAgentLLM(ready, release),
                rag_service=GroundedRagService(),
            )
            response_holder["response"] = asyncio.run(
                service.handle_message(
                    session_id=session_id,
                    user_id=consumer_id,
                    content="订单 A10086 左耳没有声音，想退货",
                )
            )

    worker = threading.Thread(target=run_agent)
    worker.start()
    try:
        assert ready.wait(timeout=10)
        with database.session_factory() as session:
            claimed = HandoffService(session).claim(
                handoff_id=handoff_id,
                agent_id=agent_id,
            )
            assert claimed.status == "claimed"
    finally:
        release.set()
    worker.join(timeout=10)
    assert not worker.is_alive()

    response = response_holder["response"]
    assert response.action == ConversationAction.WAITING_FOR_AGENT
    assert response.assistant_message is None
    with database.session_factory() as session:
        messages = list_messages(session, session_id=session_id)
        chat_session = session.get(ChatSession, session_id)
    assert chat_session is not None
    assert chat_session.status == "human_active"
    assert [message.sender_type for message in messages] == ["consumer"]
    database.dispose()
