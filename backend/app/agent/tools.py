import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from backend.app.agent.schemas import GetMyOrderArguments, ToolExecutionResult
from backend.app.core.exceptions import AppError
from backend.app.models import ToolInvocationStatus
from backend.app.repositories.chat import get_session_owned_by_user
from backend.app.repositories.tool_invocations import add_tool_invocation
from backend.app.services.orders import OrderService

GET_MY_ORDER = "get_my_order"


@dataclass(frozen=True)
class ToolContext:
    """Trusted runtime values that are never accepted from the model."""

    session: Session
    session_id: int
    user_id: int


@dataclass(frozen=True)
class ToolDefinition:
    description: str
    arguments_model: type[BaseModel]
    handler: Callable[[ToolContext, BaseModel], dict[str, Any]]


class ToolRegistry:
    """Validate and execute a strict allowlist of read-only tools."""

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {
            GET_MY_ORDER: ToolDefinition(
                description="查询当前登录消费者本人的订单，不接受调用方指定用户身份。",
                arguments_model=GetMyOrderArguments,
                handler=self._get_my_order,
            )
        }

    def execute(
        self,
        *,
        context: ToolContext,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        started_at = time.perf_counter()
        chat_session = get_session_owned_by_user(
            context.session,
            session_id=context.session_id,
            user_id=context.user_id,
        )
        if chat_session is None:
            raise AppError(
                status_code=404,
                code="chat_session_not_found",
                message="会话不存在",
            )

        tool = self._definitions.get(tool_name)
        if tool is None:
            self._record(
                context=context,
                tool_name=tool_name,
                arguments={"redacted": True},
                result={"error": "tool_not_allowed"},
                status=ToolInvocationStatus.BLOCKED,
                error_code="tool_not_allowed",
                started_at=started_at,
            )
            raise AppError(
                status_code=400,
                code="tool_not_allowed",
                message="工具调用不被允许",
            )

        try:
            parsed_arguments = tool.arguments_model.model_validate(arguments)
        except ValidationError:
            self._record(
                context=context,
                tool_name=tool_name,
                arguments={"redacted": True},
                result={"error": "tool_arguments_invalid"},
                status=ToolInvocationStatus.BLOCKED,
                error_code="tool_arguments_invalid",
                started_at=started_at,
            )
            raise AppError(
                status_code=422,
                code="tool_arguments_invalid",
                message="工具参数不合法",
            ) from None

        try:
            result = tool.handler(context, parsed_arguments)
        except AppError as exc:
            self._record(
                context=context,
                tool_name=tool_name,
                arguments=parsed_arguments.model_dump(mode="json"),
                result={"error": exc.code},
                status=ToolInvocationStatus.ERROR,
                error_code=exc.code,
                started_at=started_at,
            )
            raise
        except Exception:
            self._record(
                context=context,
                tool_name=tool_name,
                arguments=parsed_arguments.model_dump(mode="json"),
                result={"error": "tool_execution_failed"},
                status=ToolInvocationStatus.ERROR,
                error_code="tool_execution_failed",
                started_at=started_at,
            )
            raise AppError(
                status_code=500,
                code="tool_execution_failed",
                message="工具执行失败",
            ) from None

        self._record(
            context=context,
            tool_name=tool_name,
            arguments=parsed_arguments.model_dump(mode="json"),
            result=result,
            status=ToolInvocationStatus.SUCCESS,
            error_code=None,
            started_at=started_at,
        )
        return ToolExecutionResult(tool_name=tool_name, result=result)

    def _get_my_order(
        self,
        context: ToolContext,
        raw_arguments: BaseModel,
    ) -> dict[str, Any]:
        if not isinstance(raw_arguments, GetMyOrderArguments):
            raise TypeError("Unexpected arguments model")

        order = OrderService(context.session).get_order_for_user_by_no(
            order_no=raw_arguments.order_no,
            user_id=context.user_id,
        )
        return {
            "order_no": order.order_no,
            "status": order.status,
            "product_id": order.product.id,
            "product_name": order.product.name,
        }

    @staticmethod
    def _record(
        *,
        context: ToolContext,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
        status: ToolInvocationStatus,
        error_code: str | None,
        started_at: float,
    ) -> None:
        add_tool_invocation(
            context.session,
            session_id=context.session_id,
            tool_name=tool_name[:64],
            arguments=arguments,
            result=result,
            status=status.value,
            error_code=error_code,
            latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
        )
