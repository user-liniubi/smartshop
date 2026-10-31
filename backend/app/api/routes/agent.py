from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AgentUser
from backend.app.db.session import get_db
from backend.app.schemas.handoff import HandoffResponse
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
