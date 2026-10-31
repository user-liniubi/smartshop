from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppError
from backend.app.models import (
    ChatSession,
    Handoff,
    HandoffSource,
    SessionStatus,
    WorkflowState,
)
from backend.app.repositories.chat import get_session_owned_by_user
from backend.app.repositories.handoffs import (
    get_handoff_by_session,
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
