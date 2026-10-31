from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.agent.service import AfterSalesAgentService
from backend.app.api.rag_dependencies import get_llm_client, get_rag_service
from backend.app.core.config import Settings, get_settings
from backend.app.db.session import get_db
from backend.app.services.llm import DeepSeekClient
from backend.app.services.rag import RAGService


def get_after_sales_agent_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[DeepSeekClient, Depends(get_llm_client)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> AfterSalesAgentService:
    return AfterSalesAgentService(
        session=session,
        settings=settings,
        llm=llm,
        rag_service=rag_service,
    )
