"""CrossEncoder reranker singleton.

Lazily loads the ``cross-encoder/ms-marco-MiniLM-L-6-v2`` model on first
call and exposes a ``rerank()`` helper that scores query–passage pairs
and returns the top-k indices with their relevance scores.

Thread-safety
-------------
Uses double-checked locking so the model is loaded exactly once even
under Streamlit's concurrent callback model.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from src.config import settings

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_reranker: CrossEncoder | None = None
_reranker_lock = threading.Lock()


def get_reranker() -> CrossEncoder:
    """Return the shared CrossEncoder instance, loading on first call.

    Thread-safe via double-checked locking.

    Returns:
        CrossEncoder: Loaded and ready-to-predict reranker model.
    """
    global _reranker
    if _reranker is not None:
        return _reranker
    with _reranker_lock:
        if _reranker is None:
            from sentence_transformers import CrossEncoder as CE

            logger.info("Loading reranker: %s", settings.reranker_model)
            _reranker = CE(settings.reranker_model)
    return _reranker


def rerank(
    query: str,
    passages: list[str],
    top_k: int,
) -> list[tuple[int, float]]:
    """Score query–passage pairs and return the top-k by relevance.

    Args:
        query: The search query string.
        passages: List of candidate text passages to rank.
        top_k: Number of top-ranked passages to return.

    Returns:
        List of ``(original_index, score)`` tuples sorted by score
        descending, truncated to *top_k* entries.
    """
    if not passages:
        return []

    pairs = [[query, p] for p in passages]
    scores = get_reranker().predict(pairs).tolist()
    indexed: list[tuple[int, float]] = list(enumerate(scores))
    indexed.sort(key=lambda x: x[1], reverse=True)
    return indexed[:top_k]
