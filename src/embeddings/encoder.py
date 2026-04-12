"""SentenceTransformer embedding encoder singleton.

Lazily loads the ``all-MiniLM-L6-v2`` model (384-dim, ~22 MB) on first
call and reuses it for all subsequent encode requests.  Embeddings are
L2-normalised so cosine similarity reduces to a dot product.

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
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def get_encoder() -> SentenceTransformer:
    """Return the shared SentenceTransformer instance, loading on first call.

    Thread-safe via double-checked locking.

    Returns:
        SentenceTransformer: Loaded and ready-to-encode model.
    """
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer as ST

            logger.info("Loading embedding model: %s", settings.embedding_model)
            _model = ST(settings.embedding_model)
    return _model


def encode(texts: list[str]) -> list[list[float]]:
    """Encode a batch of texts into normalised 384-dim embeddings.

    Args:
        texts: List of strings to embed.

    Returns:
        List of embedding vectors, each a list of 384 floats.
    """
    return get_encoder().encode(texts, normalize_embeddings=True).tolist()
