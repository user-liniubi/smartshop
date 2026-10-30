from typing import Any

from sqlalchemy.orm import Session

from backend.app.models import ToolInvocation


def add_tool_invocation(
    session: Session,
    *,
    session_id: int,
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
    status: str,
    error_code: str | None,
    latency_ms: int,
) -> ToolInvocation:
    invocation = ToolInvocation(
        session_id=session_id,
        tool_name=tool_name,
        arguments_json=arguments,
        result_json=result,
        status=status,
        error_code=error_code,
        latency_ms=latency_ms,
    )
    session.add(invocation)
    session.commit()
    session.refresh(invocation)
    return invocation
