import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from backend.app.core.exceptions import AppError

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ParsedSection:
    text: str
    heading: str | None = None
    page: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    source_type: str
    sections: tuple[ParsedSection, ...]


def _normalize_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _parse_markdown(text: str, fallback_title: str) -> ParsedDocument:
    matches = list(_HEADING_PATTERN.finditer(text))
    title = fallback_title
    sections: list[ParsedSection] = []

    if matches:
        first_heading = matches[0].group(2).strip()
        if len(matches[0].group(1)) == 1:
            title = first_heading

        preface = _normalize_text(text[: matches[0].start()])
        if preface:
            sections.append(ParsedSection(text=preface))

        for index, match in enumerate(matches):
            content_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = _normalize_text(text[match.end() : content_end])
            heading = match.group(2).strip()
            if content:
                sections.append(ParsedSection(text=content, heading=heading))
    else:
        content = _normalize_text(text)
        if content:
            sections.append(ParsedSection(text=content))

    return ParsedDocument(
        title=title,
        source_type="markdown",
        sections=tuple(sections),
    )


def _parse_pdf(path: Path, fallback_title: str) -> ParsedDocument:
    sections: list[ParsedSection] = []
    title = fallback_title

    try:
        with pymupdf.open(path) as document:
            metadata_title = (document.metadata or {}).get("title", "").strip()
            if metadata_title:
                title = metadata_title
            for page_index, page in enumerate(document, start=1):
                page_text = _normalize_text(page.get_text("text"))
                if page_text:
                    sections.append(
                        ParsedSection(
                            text=page_text,
                            heading=f"第 {page_index} 页",
                            page=page_index,
                        )
                    )
    except (OSError, RuntimeError, ValueError):
        raise AppError(
            status_code=400,
            code="invalid_pdf",
            message="PDF 文件无法解析",
        ) from None

    if not sections:
        raise AppError(
            status_code=400,
            code="scanned_pdf_unsupported",
            message="PDF 没有可提取文本，当前版本不支持扫描件 OCR",
        )

    return ParsedDocument(
        title=title,
        source_type="pdf",
        sections=tuple(sections),
    )


def parse_document(path: Path) -> ParsedDocument:
    """Parse a supported knowledge document into source-aware sections."""

    if not path.is_file():
        raise AppError(
            status_code=404,
            code="document_file_not_found",
            message="知识文件不存在",
        )

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise AppError(
            status_code=400,
            code="unsupported_document_type",
            message="仅支持 Markdown、TXT 和 PDF 文件",
        )

    fallback_title = path.stem
    if suffix == ".pdf":
        return _parse_pdf(path, fallback_title)

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise AppError(
            status_code=400,
            code="invalid_text_encoding",
            message="文本文件必须使用 UTF-8 编码",
        ) from None

    if suffix == ".md":
        parsed = _parse_markdown(text, fallback_title)
    else:
        normalized = _normalize_text(text)
        sections = (ParsedSection(text=normalized),) if normalized else ()
        parsed = ParsedDocument(
            title=fallback_title,
            source_type="text",
            sections=sections,
        )

    if not parsed.sections:
        raise AppError(
            status_code=400,
            code="empty_document",
            message="知识文件没有可用文本",
        )
    return parsed
