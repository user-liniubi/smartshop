from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class BgeEmbeddingProvider:
    """Lazy local BGE embedding provider."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        *,
        local_files_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.local_files_only = local_files_only
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                local_files_only=self.local_files_only,
            )
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._get_model().encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        embeddings = self._get_model().encode(
            [f"{QUERY_INSTRUCTION}{query}"],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings[0].tolist()
