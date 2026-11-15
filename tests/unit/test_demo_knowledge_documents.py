from pathlib import Path

from backend.app.rag.chunking import chunk_sections
from backend.app.rag.parsing import parse_document
from sample_data.knowledge_documents import DEMO_KNOWLEDGE_DOCUMENTS
from sample_data.seed import DEMO_PRODUCTS


def test_demo_knowledge_documents_exist_and_parse():
    docs_dir = Path("data/docs")
    filenames = [document.filename for document in DEMO_KNOWLEDGE_DOCUMENTS]

    assert len(filenames) == len(set(filenames))

    for document in DEMO_KNOWLEDGE_DOCUMENTS:
        path = docs_dir / document.filename
        assert path.is_file(), f"Missing knowledge document: {document.filename}"

        parsed = parse_document(path)
        chunks = chunk_sections(
            parsed.sections,
            chunk_size=500,
            overlap=80,
        )
        assert chunks, f"No chunks generated for: {document.filename}"


def test_demo_knowledge_document_product_mappings_are_valid():
    product_names = {name for name, _ in DEMO_PRODUCTS}

    for document in DEMO_KNOWLEDGE_DOCUMENTS:
        if document.product_name is not None:
            assert document.product_name in product_names
