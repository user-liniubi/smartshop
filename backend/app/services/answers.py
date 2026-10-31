from typing import Any

from backend.app.services.llm import DeepSeekClient
from backend.app.services.rag import RAGContext


class AnswerService:
    def __init__(self, llm: DeepSeekClient) -> None:
        self.llm = llm

    async def generate(
        self,
        *,
        question: str,
        intent: str,
        order_facts: dict[str, Any] | None,
        rag_context: RAGContext,
        history: list[dict[str, str]],
    ) -> str:
        return await self.llm.generate_agent_answer(
            question=question,
            intent=intent,
            order_facts=order_facts,
            evidence=rag_context.evidence,
            history=history,
        )
