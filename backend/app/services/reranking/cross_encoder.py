from functools import lru_cache
import logging
import math
from typing import Optional

from app.core.config import get_settings
from app.services.retrieval.types import RetrievedChunk

logger = logging.getLogger("helpdesk_ai.reranking")


class CrossEncoderReranker:
    """Cross-encoder reranker scoring (query, chunk_text) pairs."""

    def __init__(self, model_name: str, enabled: bool = True) -> None:
        self.model_name = model_name
        self.enabled = enabled
        self._model = None
        self._load_error: Optional[str] = None

    def _ensure_loaded(self) -> bool:
        if not self.enabled:
            return False
        if self._model is not None:
            return True
        if self._load_error is not None:
            return False
        try:
            from sentence_transformers import CrossEncoder

            logger.info("Loading CrossEncoder reranker model: %s", self.model_name)
            try:
                self._model = CrossEncoder(self.model_name, local_files_only=True)
            except Exception:
                self._model = CrossEncoder(self.model_name)
            return True
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning(
                "CrossEncoder model '%s' unavailable (%s). Falling back to RRF ranking.",
                self.model_name,
                exc,
            )
            return False

    @property
    def is_available(self) -> bool:
        return self._ensure_loaded()

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_n: int = 5,
    ) -> tuple[list[RetrievedChunk], str]:
        """
        Rerank candidate chunks. Returns (ranked_chunks, status)
        where status is 'cross_encoder' or 'fallback_rrf'.
        """
        if not candidates:
            return [], "empty"

        if not self._ensure_loaded():
            logger.info("Reranking fallback active: returning top %d RRF-ordered chunks.", top_n)
            return candidates[:top_n], "fallback_rrf"

        pairs = [(query, f"{c.document_title}\n{c.cleaned_content}") for c in candidates]
        raw_scores = self._model.predict(pairs)

        for chunk, logit in zip(candidates, raw_scores):
            prob = 1.0 / (1.0 + math.exp(-float(logit)))
            chunk.rerank_score = round(prob, 6)
            # Combine cross-encoder probability with hybrid retrieval signal
            chunk.final_score = round(0.75 * prob + 0.25 * chunk.final_score, 6)

        reranked = sorted(
            candidates,
            key=lambda c: (c.rerank_score if c.rerank_score is not None else 0.0, c.final_score),
            reverse=True,
        )
        return reranked[:top_n], "cross_encoder"


@lru_cache
def get_reranker() -> CrossEncoderReranker:
    settings = get_settings()
    use_model = settings.enable_reranking and settings.embedding_backend != "mock"
    return CrossEncoderReranker(model_name=settings.reranker_model, enabled=use_model)

