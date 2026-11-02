from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppError
from backend.app.models import ChatSession
from backend.app.repositories.chat import (
    create_chat_session,
    get_session_owned_by_user,
    list_messages,
    list_sessions_for_user,
)
from backend.app.schemas.chat import ChatMessageResponse


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

    def list_sessions(self, *, user_id: int) -> list[ChatSession]:
        return list_sessions_for_user(self.session, user_id=user_id)

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
