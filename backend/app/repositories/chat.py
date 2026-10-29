from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import ChatMessage, ChatSession


def create_chat_session(session: Session, *, user_id: int) -> ChatSession:
    chat_session = ChatSession(user_id=user_id)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def get_session_owned_by_user(
    session: Session,
    *,
    session_id: int,
    user_id: int,
) -> ChatSession | None:
    return session.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )


def list_messages(session: Session, *, session_id: int) -> list[ChatMessage]:
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    return list(session.scalars(statement))


def add_message(
    session: Session,
    *,
    session_id: int,
    sender_type: str,
    content: str,
    citations: list[dict] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        sender_type=sender_type,
        content=content,
        citations_json=citations or [],
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message
