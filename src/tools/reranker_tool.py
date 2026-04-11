"""Cross-encoder reranking tool.

Takes candidate text chunks from vector search and reranks them using
``cross-encoder/ms-marco-MiniLM-L-6-v2`` to improve precision before
the RAG agent consumes them.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from crewai.tools import BaseTool
from pydantic import Field
from sentence_transformers import CrossEncoder

from src.config import get_settings

logger = logging.getLogger(__name__)

# Lazy-loaded cross-encoder model
_reranker_model: Optional[CrossEncoder] = None


def _get_reranker_model() -> CrossEncoder:
    """Return a lazily-initialised CrossEncoder model.

    Returns:
        A :class:`CrossEncoder` instance loaded with the configured
        reranker model name.
    """
    global _reranker_model
    if _reranker_model is None:
        settings = get_settings()
        logger.info("Loading reranker model: %s", settings.reranker_model_name)
        _reranker_model = CrossEncoder(settings.reranker_model_name)
    return _reranker_model


def rerank_documents(
    query: str,
    documents: list[dict[str, Any]],
    text_key: str = "text_content",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rerank a list of document dicts using the cross-encoder.

    Args:
        query: The original query string.
        documents: List of document dicts, each containing at least a
            ``text_content`` field.
        text_key: Key in each dict that holds the text to score.
        top_k: Number of top results to keep after reranking.

    Returns:
        The top-k documents sorted by cross-encoder score (descending),
        each augmented with a ``rerank_score`` field.
    """
    if not documents:
        return []

    model = _get_reranker_model()

    pairs: list[list[str]] = [
        [query, doc.get(text_key, "")] for doc in documents
    ]

    scores: list[float] = model.predict(pairs).tolist()

    for doc, score in zip(documents, scores):
        doc["rerank_score"] = float(score)

    ranked: list[dict[str, Any]] = sorted(
        documents, key=lambda d: d.get("rerank_score", 0.0), reverse=True
    )

    logger.info(
        "Reranked %d documents → kept top %d (best score=%.4f).",
        len(documents),
        min(top_k, len(ranked)),
        ranked[0].get("rerank_score", 0.0) if ranked else 0.0,
    )

    return ranked[:top_k]


class RerankerTool(BaseTool):
    """Rerank retrieved text chunks with a cross-encoder for higher precision.

    Input: JSON string with keys:

    * ``query`` (str): The original analyst question.
    * ``documents`` (list[dict]): Candidate chunks, each having ``text_content``.
    * ``top_k`` (int): How many to keep (default: 5).

    Attributes:
        name: Tool name visible to the agent.
        description: Human-readable purpose.
    """

    name: str = "rerank_documents"
    description: str = (
        "Rerank a list of text chunks against a query using a cross-encoder. "
        "Input: JSON with keys 'query' (str), 'documents' (list of dicts with "
        "'text_content'), 'top_k' (int, default 5). "
        "Returns the top_k most relevant documents with rerank_score."
    )

    def _run(self, query_json: str) -> str:
        """Execute cross-encoder reranking.

        Args:
            query_json: JSON string with query, documents, and top_k.

        Returns:
            JSON string of reranked documents.
        """
        try:
            params: dict[str, Any] = json.loads(query_json)
        except json.JSONDecodeError as exc:
            error_msg = f"Invalid JSON input: {exc}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

        query: str = params.get("query", "")
        documents: list[dict[str, Any]] = params.get("documents", [])
        settings = get_settings()
        top_k: int = params.get("top_k", settings.reranker_top_k)

        if not query.strip():
            return json.dumps({"error": "query must be non-empty."})

        if not documents:
            return json.dumps({"reranked": [], "count": 0})

        reranked: list[dict[str, Any]] = rerank_documents(
            query=query,
            documents=documents,
            top_k=top_k,
        )

        return json.dumps(
            {"reranked": reranked, "count": len(reranked)},
            default=str,
        )
