import asyncio
import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.agent.intent import IntentService
from backend.app.agent.orchestrator import AfterSalesOrchestrator
from backend.app.agent.schemas import (
    AfterSalesIntent,
    ConversationAction,
    GetMyOrderArguments,
    IntentResult,
    IssueType,
    ToolCallPlan,
    ToolResultSummary,
)
from backend.app.agent.tools import (
    GET_MY_ORDER,
    ToolContext,
    ToolRegistry,
)
from backend.app.core.config import Settings
from backend.app.core.exceptions import AppError
from backend.app.models import (
    ChatSession,
    HandoffSource,
    SenderType,
    SessionStatus,
    WorkflowState,
)
from backend.app.repositories.chat import (
    add_message,
    get_session_owned_by_user,
    list_messages,
)
from backend.app.repositories.handoffs import get_handoff_by_session
from backend.app.schemas.chat import ChatMessageResponse, ChatTurnResponse
from backend.app.schemas.handoff import HandoffResponse
from backend.app.services.answers import AnswerService
from backend.app.services.handoffs import HandoffService
from backend.app.services.llm import DeepSeekClient
from backend.app.services.rag import NO_EVIDENCE_ANSWER, RAGContext, RAGService
from backend.app.services.rules import AfterSalesRuleService

logger = logging.getLogger(__name__)

_POLICY_INTENTS = {
    AfterSalesIntent.AFTER_SALES_POLICY,
    AfterSalesIntent.RETURN_REQUEST,
    AfterSalesIntent.EXCHANGE_REQUEST,
    AfterSalesIntent.WARRANTY_QUESTION,
}


class AfterSalesAgentService:
    """Coordinate intent, tools, RAG, deterministic rules and persistence."""

    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        llm: DeepSeekClient,
        rag_service: RAGService,
        intent_service: IntentService | None = None,
        orchestrator: AfterSalesOrchestrator | None = None,
        tools: ToolRegistry | None = None,
        rules: AfterSalesRuleService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.llm = llm
        self.rag_service = rag_service
        self.intent_service = intent_service or IntentService(llm)
        self.orchestrator = orchestrator or AfterSalesOrchestrator()
        self.tools = tools or ToolRegistry()
        self.rules = rules or AfterSalesRuleService()
        self.answer_service = AnswerService(llm)

    async def handle_message(
        self,
        *,
        session_id: int,
        user_id: int,
        content: str,
    ) -> ChatTurnResponse:
        chat_session = self._require_owned_session(
            session_id=session_id,
            user_id=user_id,
        )
        user_message = add_message(
            self.session,
            session_id=chat_session.id,
            sender_type=SenderType.CONSUMER.value,
            content=content,
        )

        if chat_session.status in {
            SessionStatus.NEED_HUMAN.value,
            SessionStatus.HUMAN_ACTIVE.value,
            SessionStatus.CLOSED.value,
        }:
            return self._waiting_for_agent_response(
                chat_session=chat_session,
                user_message=user_message,
            )

        existing_slots = dict(chat_session.slots_json or {})
        try:
            async with asyncio.timeout(self.settings.agent_total_timeout_seconds):
                intent_result = await self.intent_service.extract(
                    content=content,
                    existing_slots=existing_slots,
                )
        except TimeoutError:
            logger.warning("Intent request timeout session_id=%s", session_id)
            return self._fail_to_handoff(
                chat_session=chat_session,
                user_message=user_message,
                reason="意图识别超时，需要人工客服继续处理",
            )
        except AppError as exc:
            logger.warning(
                "Intent dependency failure session_id=%s error=%s",
                session_id,
                exc.code,
            )
            return self._fail_to_handoff(
                chat_session=chat_session,
                user_message=user_message,
                reason=f"意图识别失败（{exc.code}），需要人工客服继续处理",
            )
        intent_result = self._preserve_active_task(intent_result)
        chat_session, decision = self.orchestrator.apply(
            session=self.session,
            session_id=session_id,
            user_id=user_id,
            result=intent_result,
        )

        if decision.reply_text:
            return self._save_turn(
                chat_session=chat_session,
                user_message=user_message,
                answer=decision.reply_text,
                action=ConversationAction.ASK_MORE_INFO,
                missing_slots=decision.missing_slots,
            )

        if decision.action.value == "handoff":
            return self._create_handoff_turn(
                chat_session=chat_session,
                user_message=user_message,
                reason="用户主动申请人工客服",
                source=HandoffSource.USER,
            )

        try:
            async with asyncio.timeout(self.settings.agent_total_timeout_seconds):
                if decision.action.value == "query_order":
                    return await self._handle_order_task(
                        chat_session=chat_session,
                        user_message=user_message,
                        content=content,
                        intent_result=intent_result,
                    )
                return await self._handle_policy_task(
                    chat_session=chat_session,
                    user_message=user_message,
                    content=content,
                    intent_result=intent_result,
                )
        except TimeoutError:
            logger.warning("Agent request timeout session_id=%s", session_id)
            return self._fail_to_handoff(
                chat_session=chat_session,
                user_message=user_message,
                reason="AI 服务超时，需要人工客服继续处理",
            )
        except AppError as exc:
            logger.warning(
                "Agent dependency failure session_id=%s error=%s",
                session_id,
                exc.code,
            )
            return self._fail_to_handoff(
                chat_session=chat_session,
                user_message=user_message,
                reason=f"AI 处理失败（{exc.code}），需要人工客服继续处理",
            )
        except Exception:
            logger.exception("Unexpected agent failure session_id=%s", session_id)
            return self._fail_to_handoff(
                chat_session=chat_session,
                user_message=user_message,
                reason="AI 处理出现异常，需要人工客服继续处理",
            )

    async def _handle_order_task(
        self,
        *,
        chat_session: ChatSession,
        user_message,
        content: str,
        intent_result: IntentResult,
    ) -> ChatTurnResponse:
        order_no = intent_result.slots.order_no
        if order_no is None:
            return self._save_turn(
                chat_session=chat_session,
                user_message=user_message,
                answer="请提供需要查询的订单号。",
                action=ConversationAction.ASK_MORE_INFO,
                missing_slots=["order_no"],
            )

        plan = await self._plan_order_tool(content=content, order_no=order_no)
        context = ToolContext(
            session=self.session,
            session_id=chat_session.id,
            user_id=chat_session.user_id,
            rag_service=self.rag_service,
        )
        try:
            tool_result = self.tools.execute(
                context=context,
                tool_name=plan.name,
                arguments=plan.arguments,
            )
        except AppError as exc:
            self.orchestrator.transition(
                session=self.session,
                chat_session=chat_session,
                target=WorkflowState.COLLECTING_INFO,
            )
            answer = (
                "未找到属于当前账号的有效订单，请检查订单号后重试。"
                if exc.code == "order_not_found"
                else "订单查询暂时失败，请稍后重试或申请人工客服。"
            )
            return self._save_turn(
                chat_session=chat_session,
                user_message=user_message,
                answer=answer,
                action=ConversationAction.ASK_MORE_INFO,
                missing_slots=["order_no"] if exc.code == "order_not_found" else [],
                tool_results=[
                    ToolResultSummary(
                        tool_name=plan.name,
                        status="error",
                        result={"error": exc.code},
                        error_code=exc.code,
                    )
                ],
            )

        order_facts = tool_result.result
        product_id = int(order_facts["product_id"])
        chat_session.slots_json = {
            **chat_session.slots_json,
            "product_id": product_id,
        }
        self.session.commit()
        self.session.refresh(chat_session)
        chat_session = self.orchestrator.transition(
            session=self.session,
            chat_session=chat_session,
            target=WorkflowState.CHECKING_POLICY,
        )

        rag_context = await self._retrieve_policy(
            content=content,
            intent_result=intent_result,
            product_id=product_id,
        )
        decision = self.rules.enforce(
            answer="",
            intent=intent_result.intent,
            order_facts=order_facts,
            policy_grounded=rag_context.grounded,
        )
        if decision.handoff_required:
            return self._create_handoff_turn(
                chat_session=chat_session,
                user_message=user_message,
                reason=decision.handoff_reason or "售后规则要求人工复核",
                source=HandoffSource.RULE,
                answer=decision.answer,
                tool_results=[
                    ToolResultSummary(
                        tool_name=tool_result.tool_name,
                        status="success",
                        result=order_facts,
                    )
                ],
            )

        history = self._history_for_model(chat_session.id)
        answer = await self.answer_service.generate(
            question=content,
            intent=intent_result.intent.value,
            order_facts=order_facts,
            rag_context=rag_context,
            history=history,
        )
        rule_decision = self.rules.enforce(
            answer=answer,
            intent=intent_result.intent,
            order_facts=order_facts,
            policy_grounded=rag_context.grounded,
        )
        if rule_decision.handoff_required:
            return self._create_handoff_turn(
                chat_session=chat_session,
                user_message=user_message,
                reason=rule_decision.handoff_reason or "售后安全规则触发",
                source=HandoffSource.RULE,
                answer=rule_decision.answer,
                tool_results=[
                    ToolResultSummary(
                        tool_name=tool_result.tool_name,
                        status="success",
                        result=order_facts,
                    )
                ],
            )

        return self._finish_with_answer(
            chat_session=chat_session,
            user_message=user_message,
            answer=rule_decision.answer,
            rag_context=rag_context,
            tool_results=[
                ToolResultSummary(
                    tool_name=tool_result.tool_name,
                    status="success",
                    result=order_facts,
                )
            ],
        )

    async def _handle_policy_task(
        self,
        *,
        chat_session: ChatSession,
        user_message,
        content: str,
        intent_result: IntentResult,
    ) -> ChatTurnResponse:
        rag_context = await self._retrieve_policy(
            content=content,
            intent_result=intent_result,
            product_id=self._product_id_from_slots(chat_session),
        )
        rule_decision = self.rules.enforce(
            answer="",
            intent=intent_result.intent,
            order_facts=None,
            policy_grounded=rag_context.grounded,
        )
        if rule_decision.handoff_required:
            return self._create_handoff_turn(
                chat_session=chat_session,
                user_message=user_message,
                reason=rule_decision.handoff_reason or "缺少政策依据",
                source=HandoffSource.RULE,
                answer=rule_decision.answer,
            )

        answer = await self.answer_service.generate(
            question=content,
            intent=intent_result.intent.value,
            order_facts=None,
            rag_context=rag_context,
            history=self._history_for_model(chat_session.id),
        )
        rule_decision = self.rules.enforce(
            answer=answer,
            intent=intent_result.intent,
            order_facts=None,
            policy_grounded=rag_context.grounded,
        )
        if rule_decision.handoff_required:
            return self._create_handoff_turn(
                chat_session=chat_session,
                user_message=user_message,
                reason=rule_decision.handoff_reason or "售后安全规则触发",
                source=HandoffSource.RULE,
                answer=rule_decision.answer,
            )
        return self._finish_with_answer(
            chat_session=chat_session,
            user_message=user_message,
            answer=rule_decision.answer or NO_EVIDENCE_ANSWER,
            rag_context=rag_context,
        )

    async def _plan_order_tool(self, *, content: str, order_no: str) -> ToolCallPlan:
        tools = [
            schema
            for schema in self.tools.model_schemas()
            if schema["function"]["name"] == GET_MY_ORDER
        ]
        try:
            raw_plan = await self.llm.plan_tool_call(message=content, tools=tools)
        except AppError:
            logger.warning("Tool planning degraded to deterministic order lookup")
            raw_plan = None

        if raw_plan is None:
            return ToolCallPlan(
                name=GET_MY_ORDER,
                arguments={"order_no": order_no},
            )

        try:
            plan = ToolCallPlan.model_validate(raw_plan)
        except ValidationError:
            raise AppError(
                status_code=422,
                code="tool_call_invalid",
                message="模型返回的工具参数不合法",
            ) from None
        if plan.name != GET_MY_ORDER:
            raise AppError(
                status_code=400,
                code="tool_not_allowed",
                message="工具调用不被允许",
            )
        arguments = GetMyOrderArguments.model_validate(plan.arguments)
        return ToolCallPlan(
            name=plan.name,
            arguments=arguments.model_dump(mode="json"),
        )

    async def _retrieve_policy(
        self,
        *,
        content: str,
        intent_result: IntentResult,
        product_id: int | None,
    ) -> RAGContext:
        if intent_result.intent not in _POLICY_INTENTS:
            return RAGContext(
                evidence="",
                citations=[],
                chunks=(),
                grounded=False,
            )
        issue_type = intent_result.slots.issue_type
        issue_description = intent_result.slots.issue_description or ""
        query = f"{content} {issue_type or ''} {issue_description} 售后政策"
        return await self.rag_service.retrieve(
            question=query.strip(),
            product_id=product_id,
        )

    def _finish_with_answer(
        self,
        *,
        chat_session: ChatSession,
        user_message,
        answer: str,
        rag_context: RAGContext,
        tool_results: list[ToolResultSummary] | None = None,
    ) -> ChatTurnResponse:
        if not self._ai_reply_allowed(chat_session):
            return self._waiting_for_agent_response(
                chat_session=chat_session,
                user_message=user_message,
            )
        if chat_session.workflow_state == WorkflowState.CHECKING_POLICY.value:
            chat_session = self.orchestrator.transition(
                session=self.session,
                chat_session=chat_session,
                target=WorkflowState.ANSWER_READY,
            )
        assistant_message = add_message(
            self.session,
            session_id=chat_session.id,
            sender_type=SenderType.ASSISTANT.value,
            content=answer,
            citations=[citation.model_dump(mode="json") for citation in rag_context.citations],
        )
        if chat_session.workflow_state == WorkflowState.ANSWER_READY.value:
            chat_session = self.orchestrator.transition(
                session=self.session,
                chat_session=chat_session,
                target=WorkflowState.RESOLVED,
            )
        return ChatTurnResponse(
            user_message=ChatMessageResponse.model_validate(user_message),
            assistant_message=ChatMessageResponse.model_validate(assistant_message),
            action=ConversationAction.ANSWER,
            workflow_state=WorkflowState(chat_session.workflow_state),
            tool_results=tool_results or [],
        )

    def _create_handoff_turn(
        self,
        *,
        chat_session: ChatSession,
        user_message,
        reason: str,
        source: HandoffSource,
        answer: str | None = None,
        tool_results: list[ToolResultSummary] | None = None,
    ) -> ChatTurnResponse:
        handoff, created = HandoffService(self.session).ensure_handoff(
            chat_session=chat_session,
            reason=reason,
            source=source,
        )
        assistant_message = None
        if answer:
            assistant_message = add_message(
                self.session,
                session_id=chat_session.id,
                sender_type=SenderType.ASSISTANT.value,
                content=answer,
            )
        return ChatTurnResponse(
            user_message=ChatMessageResponse.model_validate(user_message),
            assistant_message=(
                ChatMessageResponse.model_validate(assistant_message) if assistant_message else None
            ),
            action=(
                ConversationAction.HANDOFF_CREATED
                if created
                else ConversationAction.WAITING_FOR_AGENT
            ),
            workflow_state=WorkflowState.NEED_HUMAN,
            tool_results=tool_results or [],
            handoff=HandoffResponse.model_validate(handoff),
        )

    def _fail_to_handoff(
        self,
        *,
        chat_session: ChatSession,
        user_message,
        reason: str,
    ) -> ChatTurnResponse:
        return self._create_handoff_turn(
            chat_session=chat_session,
            user_message=user_message,
            reason=reason,
            source=HandoffSource.AI,
            answer=("当前 AI 服务暂时无法稳定处理这个问题。你的消息已保存，并已为你转接人工客服。"),
        )

    def _save_turn(
        self,
        *,
        chat_session: ChatSession,
        user_message,
        answer: str,
        action: ConversationAction,
        missing_slots: list[str],
        tool_results: list[ToolResultSummary] | None = None,
    ) -> ChatTurnResponse:
        if not self._ai_reply_allowed(chat_session):
            return self._waiting_for_agent_response(
                chat_session=chat_session,
                user_message=user_message,
            )
        assistant_message = add_message(
            self.session,
            session_id=chat_session.id,
            sender_type=SenderType.ASSISTANT.value,
            content=answer,
        )
        return ChatTurnResponse(
            user_message=ChatMessageResponse.model_validate(user_message),
            assistant_message=ChatMessageResponse.model_validate(assistant_message),
            action=action,
            workflow_state=WorkflowState(chat_session.workflow_state),
            missing_slots=missing_slots,
            tool_results=tool_results or [],
        )

    def _waiting_for_agent_response(
        self,
        *,
        chat_session: ChatSession,
        user_message,
    ) -> ChatTurnResponse:
        handoff = get_handoff_by_session(
            self.session,
            session_id=chat_session.id,
        )
        if handoff is None:
            handoff = HandoffService(self.session).ensure_handoff(
                chat_session=chat_session,
                reason="等待人工客服处理",
                source=HandoffSource.USER,
            )[0]
        return ChatTurnResponse(
            user_message=ChatMessageResponse.model_validate(user_message),
            assistant_message=None,
            action=ConversationAction.WAITING_FOR_AGENT,
            workflow_state=WorkflowState.NEED_HUMAN,
            handoff=HandoffResponse.model_validate(handoff),
        )

    def _ai_reply_allowed(self, chat_session: ChatSession) -> bool:
        self.session.refresh(chat_session)
        return chat_session.status not in {
            SessionStatus.NEED_HUMAN.value,
            SessionStatus.HUMAN_ACTIVE.value,
            SessionStatus.CLOSED.value,
        }

    def _preserve_active_task(self, result: IntentResult) -> IntentResult:
        issue_type = result.slots.issue_type
        if issue_type == IssueType.RETURN and result.intent != AfterSalesIntent.HUMAN_REQUEST:
            result.intent = AfterSalesIntent.RETURN_REQUEST
        elif issue_type == IssueType.EXCHANGE and result.intent != AfterSalesIntent.HUMAN_REQUEST:
            result.intent = AfterSalesIntent.EXCHANGE_REQUEST
        return result

    def _history_for_model(self, session_id: int) -> list[dict[str, str]]:
        return [
            {
                "role": message.sender_type,
                "content": message.content,
            }
            for message in list_messages(self.session, session_id=session_id)
        ]

    @staticmethod
    def _product_id_from_slots(chat_session: ChatSession) -> int | None:
        product_id = (chat_session.slots_json or {}).get("product_id")
        return product_id if isinstance(product_id, int) else None

    def _require_owned_session(self, *, session_id: int, user_id: int) -> ChatSession:
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
        return chat_session
