from functools import lru_cache
import hashlib
import logging
import re
from typing import Protocol

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger("helpdesk_ai.embeddings")


class EmbeddingBackend(Protocol):
    model_name: str
    dimension: int

    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerBackend:
    """Local Sentence Transformers embedding backend."""

    def __init__(self, model_name: str, expected_dim: int) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        try:
            self._model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            self._model = SentenceTransformer(model_name)
        detected_dim = self._model.get_sentence_embedding_dimension()
        self.dimension = int(detected_dim or expected_dim)

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vec.tolist() for vec in vectors]


class DeterministicHashBackend:
    """
    Deterministic feature-hashing embedding backend strictly for explicit test mode
    (EMBEDDING_BACKEND=mock) when external model downloads are disabled in unit tests.
    """

    def __init__(self, model_name: str, dimension: int) -> None:
        self.model_name = f"mock-hash:{model_name}"
        self.dimension = dimension

    def encode(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            vec = np.zeros(self.dimension, dtype=np.float32)
            tokens = re.findall(r"[a-z0-9_.-]+", text.lower())
            # Unigrams + character trigrams for semantic-like lexical overlap in tests
            features = list(tokens)
            for tok in tokens:
                if len(tok) >= 4:
                    features.extend(tok[i : i + 3] for i in range(len(tok) - 2))
            for feat in features:
                digest = hashlib.sha256(feat.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dimension
                sign = 1.0 if (digest[4] & 1) == 0 else -1.0
                vec[idx] += sign
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec /= norm
            results.append(vec.tolist())
        return results


class EmbeddingService:
    """Unified embedding service ensuring document chunks and queries share one model."""

    def __init__(self, backend: EmbeddingBackend) -> None:
        self._backend = backend

    @property
    def model_name(self) -> str:
        return self._backend.model_name

    @property
    def dimension(self) -> int:
        return self._backend.dimension

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        return self._backend.encode(texts)

    def encode_query(self, query: str) -> list[float]:
        vectors = self._backend.encode([query])
        return vectors[0] if vectors else [0.0] * self.dimension


@lru_cache
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    if settings.embedding_backend == "mock":
        logger.info("Using deterministic mock embedding backend (EMBEDDING_BACKEND=mock).")
        return EmbeddingService(
            DeterministicHashBackend(settings.embedding_model, settings.embedding_dim)
        )
    logger.info("Loading SentenceTransformer embedding model: %s", settings.embedding_model)
    return EmbeddingService(
        SentenceTransformerBackend(settings.embedding_model, settings.embedding_dim)
    )

