from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppError
from backend.app.models import (
    ChatMessage,
    ChatSession,
    Handoff,
    HandoffSource,
    SessionStatus,
    WorkflowState,
)
from backend.app.repositories.chat import get_session_owned_by_user
from backend.app.repositories.handoffs import (
    claim_handoff_atomic,
    get_handoff_by_session,
    list_agent_handoffs,
    list_pending_handoffs,
)


class HandoffService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def request_for_user(
        self,
        *,
        session_id: int,
        user_id: int,
        reason: str,
    ) -> tuple[Handoff, bool]:
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
        return self.ensure_handoff(
            chat_session=chat_session,
            reason=reason,
            source=HandoffSource.USER,
        )

    def ensure_handoff(
        self,
        *,
        chat_session: ChatSession,
        reason: str,
        source: HandoffSource,
    ) -> tuple[Handoff, bool]:
        existing = get_handoff_by_session(
            self.session,
            session_id=chat_session.id,
        )
        created = existing is None
        if existing is None:
            existing = Handoff(
                session_id=chat_session.id,
                reason=reason.strip()[:500],
                source=source.value,
            )
            self.session.add(existing)

        chat_session.status = SessionStatus.NEED_HUMAN.value
        chat_session.workflow_state = WorkflowState.NEED_HUMAN.value
        self.session.commit()
        self.session.refresh(existing)
        self.session.refresh(chat_session)
        return existing, created

    def list_pending(self) -> list[Handoff]:
        return list_pending_handoffs(self.session)

    def list_mine(self, *, agent_id: int) -> list[Handoff]:
        return list_agent_handoffs(self.session, agent_id=agent_id)

    def claim(self, *, handoff_id: int, agent_id: int) -> Handoff:
        handoff = claim_handoff_atomic(
            self.session,
            handoff_id=handoff_id,
            agent_id=agent_id,
        )
        if handoff is None:
            raise AppError(
                status_code=409,
                code="handoff_already_claimed",
                message="该会话已被其他客服接管或已关闭",
            )
        return handoff

    def get_agent_session(
        self,
        *,
        session_id: int,
        agent_id: int,
    ) -> tuple[ChatSession, Handoff]:
        handoff = get_handoff_by_session(self.session, session_id=session_id)
        if (
            handoff is None
            or handoff.agent_id != agent_id
            or handoff.status not in {"claimed", "closed"}
        ):
            raise AppError(
                status_code=403,
                code="handoff_not_owned",
                message="该会话不属于当前客服",
            )
        chat_session = self.session.get(ChatSession, session_id)
        if chat_session is None:
            raise AppError(
                status_code=404,
                code="chat_session_not_found",
                message="会话不存在",
            )
        return chat_session, handoff

    def reply(
        self,
        *,
        session_id: int,
        agent_id: int,
        content: str,
    ) -> Handoff:
        chat_session, handoff = self.get_agent_session(
            session_id=session_id,
            agent_id=agent_id,
        )
        if handoff.status == "closed" or chat_session.status == "closed":
            raise AppError(
                status_code=409,
                code="handoff_closed",
                message="会话已关闭，无法继续回复",
            )
        self.session.add(
            ChatMessage(
                session_id=session_id,
                sender_type="agent",
                content=content,
                citations_json=[],
            )
        )
        chat_session.status = SessionStatus.HUMAN_ACTIVE.value
        self.session.commit()
        self.session.refresh(handoff)
        return handoff

    def close(self, *, session_id: int, agent_id: int) -> Handoff:
        chat_session, handoff = self.get_agent_session(
            session_id=session_id,
            agent_id=agent_id,
        )
        if handoff.status == "closed" or chat_session.status == "closed":
            raise AppError(
                status_code=409,
                code="handoff_closed",
                message="会话已经关闭",
            )
        now = datetime.now(UTC)
        handoff.status = "closed"
        handoff.closed_at = now
        chat_session.status = SessionStatus.CLOSED.value
        chat_session.workflow_state = WorkflowState.RESOLVED.value
        self.session.commit()
        self.session.refresh(handoff)
        return handoff
