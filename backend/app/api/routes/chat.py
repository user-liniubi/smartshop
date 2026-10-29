from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.api.dependencies import CurrentUser
from backend.app.api.rag_dependencies import get_rag_service
from backend.app.db.session import get_db
from backend.app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    ChatTurnResponse,
)
from backend.app.services.chat import ChatService
from backend.app.services.rag import RAGService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> ChatSessionResponse:
    chat_session = ChatService(session).create_session(user_id=current_user.id)
    return ChatSessionResponse.model_validate(chat_session)


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
    "/sessions/{session_id}/messages",
    response_model=ChatTurnResponse,
)
async def send_message(
    session_id: Annotated[int, Path(gt=0)],
    request: ChatMessageRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> ChatTurnResponse:
    return await ChatService(session).send_message(
        session_id=session_id,
        user_id=current_user.id,
        content=request.content,
        rag_service=rag_service,
    )
