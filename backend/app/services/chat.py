from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppError
from backend.app.models import ChatSession, SenderType
from backend.app.repositories.chat import (
    add_message,
    create_chat_session,
    get_session_owned_by_user,
    list_messages,
)
from backend.app.schemas.chat import ChatMessageResponse, ChatTurnResponse
from backend.app.services.rag import RAGService


class ChatService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, *, user_id: int) -> ChatSession:
        return create_chat_session(self.session, user_id=user_id)

    def get_messages(self, *, session_id: int, user_id: int) -> list[ChatMessageResponse]:
        self._require_owned_session(session_id=session_id, user_id=user_id)
        return [
            ChatMessageResponse.model_validate(message)
            for message in list_messages(self.session, session_id=session_id)
        ]

    async def send_message(
        self,
        *,
        session_id: int,
        user_id: int,
        content: str,
        rag_service: RAGService,
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

        product_id = chat_session.slots_json.get("product_id")
        rag_response = await rag_service.ask(
            question=content,
            product_id=product_id if isinstance(product_id, int) else None,
        )
        citations = [citation.model_dump(mode="json") for citation in rag_response.citations]
        assistant_message = add_message(
            self.session,
            session_id=chat_session.id,
            sender_type=SenderType.ASSISTANT.value,
            content=rag_response.answer,
            citations=citations,
        )
        return ChatTurnResponse(
            user_message=ChatMessageResponse.model_validate(user_message),
            assistant_message=ChatMessageResponse.model_validate(assistant_message),
        )

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
