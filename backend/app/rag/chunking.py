import hashlib
from dataclasses import dataclass

from backend.app.rag.parsing import ParsedSection


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page: int | None
    heading: str | None
    content: str
    text_hash: str


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_sections(
    sections: tuple[ParsedSection, ...],
    *,
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    """Split parsed sections into overlapping character chunks."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size")

    chunks: list[TextChunk] = []
    chunk_index = 0

    for section in sections:
        heading_prefix = f"{section.heading}\n" if section.heading else ""
        full_text = f"{heading_prefix}{section.text}".strip()
        if not full_text:
            continue

        start = 0
        while start < len(full_text):
            end = min(start + chunk_size, len(full_text))
            content = full_text[start:end].strip()
            if content:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        page=section.page,
                        heading=section.heading,
                        content=content,
                        text_hash=_hash_text(content),
                    )
                )
                chunk_index += 1

            if end == len(full_text):
                break
            start = end - overlap

    return chunks
