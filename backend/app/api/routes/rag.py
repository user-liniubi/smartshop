from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import CurrentUser
from backend.app.api.rag_dependencies import get_rag_service
from backend.app.schemas.rag import RagAskRequest, RagAskResponse
from backend.app.services.rag import RAGService

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


@router.post("/ask", response_model=RagAskResponse)
async def ask_knowledge(
    request: RagAskRequest,
    current_user: CurrentUser,
    service: Annotated[RAGService, Depends(get_rag_service)],
) -> RagAskResponse:
    return await service.ask(
        question=request.question,
        product_id=request.product_id,
        top_k=request.top_k,
    )
