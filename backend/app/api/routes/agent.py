from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AgentUser
from backend.app.db.session import get_db
from backend.app.repositories.chat import list_messages
from backend.app.repositories.orders import get_order_owned_by_user_and_no
from backend.app.schemas.agent import AgentSessionContextResponse
from backend.app.schemas.chat import ChatMessageResponse, ChatSessionResponse
from backend.app.schemas.handoff import AgentReplyRequest, HandoffResponse
from backend.app.schemas.order import OrderResponse
from backend.app.services.handoffs import HandoffService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/handoffs", response_model=list[HandoffResponse])
def list_pending_handoffs(
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[HandoffResponse]:
    return [
        HandoffResponse.model_validate(handoff)
        for handoff in HandoffService(session).list_pending()
    ]


@router.get("/handoffs/mine", response_model=list[HandoffResponse])
def list_my_handoffs(
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[HandoffResponse]:
    return [
        HandoffResponse.model_validate(handoff)
        for handoff in HandoffService(session).list_mine(agent_id=current_agent.id)
    ]


@router.post(
    "/handoffs/{handoff_id}/claim",
    response_model=HandoffResponse,
)
def claim_handoff(
    handoff_id: Annotated[int, Path(gt=0)],
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> HandoffResponse:
    handoff = HandoffService(session).claim(
        handoff_id=handoff_id,
        agent_id=current_agent.id,
    )
    return HandoffResponse.model_validate(handoff)


@router.get(
    "/sessions/{session_id}",
    response_model=AgentSessionContextResponse,
)
def get_agent_session(
    session_id: Annotated[int, Path(gt=0)],
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> AgentSessionContextResponse:
    chat_session, handoff = HandoffService(session).get_agent_session(
        session_id=session_id,
        agent_id=current_agent.id,
    )
    order_no = (chat_session.slots_json or {}).get("order_no")
    order = (
        get_order_owned_by_user_and_no(
            session,
            order_no=order_no,
            user_id=chat_session.user_id,
        )
        if isinstance(order_no, str)
        else None
    )
    return AgentSessionContextResponse(
        session=ChatSessionResponse.model_validate(chat_session),
        messages=[
            ChatMessageResponse.model_validate(message)
            for message in list_messages(session, session_id=session_id)
        ],
        handoff=HandoffResponse.model_validate(handoff),
        order=OrderResponse.model_validate(order) if order else None,
    )


@router.post(
    "/sessions/{session_id}/reply",
    response_model=HandoffResponse,
)
def reply_to_consumer(
    session_id: Annotated[int, Path(gt=0)],
    request: AgentReplyRequest,
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> HandoffResponse:
    handoff = HandoffService(session).reply(
        session_id=session_id,
        agent_id=current_agent.id,
        content=request.content,
    )
    return HandoffResponse.model_validate(handoff)


@router.post(
    "/sessions/{session_id}/close",
    response_model=HandoffResponse,
)
def close_session(
    session_id: Annotated[int, Path(gt=0)],
    current_agent: AgentUser,
    session: Annotated[Session, Depends(get_db)],
) -> HandoffResponse:
    handoff = HandoffService(session).close(
        session_id=session_id,
        agent_id=current_agent.id,
    )
    return HandoffResponse.model_validate(handoff)
