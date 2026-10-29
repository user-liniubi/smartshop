import asyncio
import logging
import time

from backend.app.core.config import Settings
from backend.app.rag.embeddings import BgeEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore, RetrievedChunk
from backend.app.schemas.rag import CitationResponse, RagAskResponse
from backend.app.services.llm import DeepSeekClient

NO_EVIDENCE_ANSWER = "当前知识库中没有足够依据确认这个问题，建议转人工客服进一步核实。"
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(
        self,
        *,
        settings: Settings,
        embedder: BgeEmbeddingProvider,
        vector_store: ChromaVectorStore,
        llm: DeepSeekClient,
    ) -> None:
        self.settings = settings
        self.embedder = embedder
        self.vector_store = vector_store
        self.llm = llm

    async def ask(
        self,
        *,
        question: str,
        product_id: int | None = None,
        top_k: int | None = None,
    ) -> RagAskResponse:
        started_at = time.perf_counter()
        query_embedding = await asyncio.to_thread(self.embedder.embed_query, question)
        retrieved = await asyncio.to_thread(
            self.vector_store.query,
            query_embedding,
            top_k=top_k or self.settings.rag_top_k,
            product_id=product_id,
        )
        logger.info(
            "RAG retrieval completed results=%d product_id=%s duration=%.3fs",
            len(retrieved),
            product_id,
            time.perf_counter() - started_at,
        )
        relevant = [
            chunk for chunk in retrieved if chunk.similarity >= self.settings.rag_min_similarity
        ]
        citations = [self._to_citation(chunk, index) for index, chunk in enumerate(relevant, 1)]

        if not relevant:
            return RagAskResponse(
                answer=NO_EVIDENCE_ANSWER,
                grounded=False,
                citations=[],
                model=self.settings.deepseek_model,
            )

        evidence = "\n\n".join(
            f"[{index}] 来源：{chunk.title}，{chunk.filename}"
            f"{self._location(chunk)}\n{chunk.content}"
            for index, chunk in enumerate(relevant, start=1)
        )
        answer = await self.llm.generate_answer(question=question, evidence=evidence)
        return RagAskResponse(
            answer=answer,
            grounded=True,
            citations=citations,
            model=self.settings.deepseek_model,
        )

    @staticmethod
    def _location(chunk: RetrievedChunk) -> str:
        location_parts: list[str] = []
        if chunk.heading:
            location_parts.append(chunk.heading)
        if chunk.page:
            location_parts.append(f"第 {chunk.page} 页")
        return f"，{'，'.join(location_parts)}" if location_parts else ""

    @staticmethod
    def _to_citation(chunk: RetrievedChunk, index: int) -> CitationResponse:
        excerpt = chunk.content if len(chunk.content) <= 240 else f"{chunk.content[:240]}..."
        return CitationResponse(
            document_id=chunk.document_id,
            chunk_id=f"[{index}] {chunk.vector_id}",
            filename=chunk.filename,
            title=chunk.title,
            page=chunk.page,
            heading=chunk.heading,
            excerpt=excerpt,
            similarity=round(chunk.similarity, 4),
        )
