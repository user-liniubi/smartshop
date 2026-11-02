from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.agent.service import AfterSalesAgentService
from backend.app.api.agent_dependencies import get_after_sales_agent_service
from backend.app.api.dependencies import CurrentUser
from backend.app.core.exceptions import AppError
from backend.app.db.session import get_db
from backend.app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    ChatTurnResponse,
)
from backend.app.schemas.handoff import HandoffRequest, HandoffResponse
from backend.app.services.chat import ChatService
from backend.app.services.handoffs import HandoffService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> ChatSessionResponse:
    chat_session = ChatService(session).create_session(user_id=current_user.id)
    return ChatSessionResponse.model_validate(chat_session)


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_sessions(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[ChatSessionResponse]:
    return [
        ChatSessionResponse.model_validate(chat_session)
        for chat_session in ChatService(session).list_sessions(user_id=current_user.id)
    ]


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageResponse],
)
def get_messages(
    session_id: Annotated[int, Path(gt=0)],
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[ChatMessageResponse]:
    return ChatService(session).get_messages(
        session_id=session_id,
        user_id=current_user.id,
    )


@router.post(
    "/sessions/{session_id}/handoff",
    response_model=HandoffResponse,
)
def request_handoff(
    session_id: Annotated[int, Path(gt=0)],
    request: HandoffRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> HandoffResponse:
    if current_user.role != "consumer":
        raise AppError(
            status_code=403,
            code="consumer_role_required",
            message="只有消费者可以申请人工客服",
        )
    handoff, _ = HandoffService(session).request_for_user(
        session_id=session_id,
        user_id=current_user.id,
        reason=request.reason,
    )
    return HandoffResponse.model_validate(handoff)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatTurnResponse,
)
async def send_message(
    session_id: Annotated[int, Path(gt=0)],
    request: ChatMessageRequest,
    current_user: CurrentUser,
    agent_service: Annotated[
        AfterSalesAgentService,
        Depends(get_after_sales_agent_service),
    ],
) -> ChatTurnResponse:
    return await agent_service.handle_message(
        session_id=session_id,
        user_id=current_user.id,
        content=request.content,
    )
