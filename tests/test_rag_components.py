import asyncio

import pymupdf
import pytest

from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError
from backend.app.rag.chunking import chunk_sections
from backend.app.rag.parsing import ParsedSection, parse_document
from backend.app.rag.vector_store import RetrievedChunk
from backend.app.services.rag import NO_EVIDENCE_ANSWER, RAGService


class FakeEmbedder:
    def embed_query(self, query: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class FakeVectorStore:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks

    def query(
        self,
        embedding: list[float],
        *,
        top_k: int,
        product_id: int | None = None,
    ) -> list[RetrievedChunk]:
        return self.chunks[:top_k]


class FakeLLM:
    def __init__(self) -> None:
        self.evidence = ""

    async def generate_answer(self, *, question: str, evidence: str) -> str:
        self.evidence = evidence
        return f"根据资料，耳机质保十二个月。[1]（问题：{question}）"


def _chunk(similarity: float) -> RetrievedChunk:
    return RetrievedChunk(
        vector_id=f"1:{int(similarity * 100)}",
        content="降噪耳机提供十二个月质保。",
        document_id=1,
        chunk_index=1,
        filename="warranty_policy.md",
        title="SmartShop 虚构质保规则",
        page=None,
        heading="各品类期限",
        similarity=similarity,
    )


def test_markdown_and_pdf_parsing_preserve_source_metadata(tmp_path):
    markdown_path = tmp_path / "policy.md"
    markdown_path.write_text(
        "# 退货政策\n\n## 七天无理由\n\n签收后七天内可申请。",
        encoding="utf-8",
    )
    markdown = parse_document(markdown_path)

    pdf_path = tmp_path / "faq.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 50), "Warranty is twelve months.")
    document.set_metadata({"title": "Warranty FAQ"})
    document.save(pdf_path)
    document.close()
    pdf = parse_document(pdf_path)

    assert markdown.title == "退货政策"
    assert markdown.source_type == "markdown"
    assert markdown.sections[0].heading == "七天无理由"
    assert pdf.title == "Warranty FAQ"
    assert pdf.source_type == "pdf"
    assert pdf.sections[0].page == 1


def test_empty_and_unsupported_documents_are_rejected(tmp_path):
    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("   \n", encoding="utf-8")
    unsupported_path = tmp_path / "manual.docx"
    unsupported_path.write_bytes(b"not a real docx")

    with pytest.raises(AppError) as empty_error:
        parse_document(empty_path)
    with pytest.raises(AppError) as unsupported_error:
        parse_document(unsupported_path)

    assert empty_error.value.code == "empty_document"
    assert unsupported_error.value.code == "unsupported_document_type"


def test_chunking_applies_size_and_overlap():
    sections = (
        ParsedSection(
            heading="政策",
            text="甲乙丙丁戊己庚辛壬癸" * 10,
        ),
    )

    chunks = chunk_sections(sections, chunk_size=40, overlap=10)

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 40 for chunk in chunks)
    assert chunks[0].content[-10:] == chunks[1].content[:10]
    assert all(chunk.heading == "政策" for chunk in chunks)


def test_rag_service_returns_answer_and_grounded_citation():
    llm = FakeLLM()
    service = RAGService(
        settings=get_settings(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_chunk(0.91)]),
        llm=llm,
    )

    response = asyncio.run(service.ask(question="耳机保修多久？", product_id=1))

    assert response.grounded is True
    assert "[1]" in response.answer
    assert response.citations[0].filename == "warranty_policy.md"
    assert response.citations[0].heading == "各品类期限"
    assert "降噪耳机提供十二个月质保" in llm.evidence


def test_rag_service_refuses_when_evidence_is_below_threshold():
    class NeverCalledLLM:
        async def generate_answer(self, *, question: str, evidence: str) -> str:
            raise AssertionError("LLM should not run without sufficient evidence")

    service = RAGService(
        settings=get_settings(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore([_chunk(0.01)]),
        llm=NeverCalledLLM(),
    )

    response = asyncio.run(service.ask(question="火星有库存吗？"))

    assert response.grounded is False
    assert response.answer == NO_EVIDENCE_ANSWER
    assert response.citations == []
