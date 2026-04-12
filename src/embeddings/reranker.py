"""Online Reranker API wrapper.

Replaces the local memory-heavy CrossEncoder with an external Reranking API.
Free tier suggestions:
1. Cohere Rerank (Very generous free trial key for developers: 1K calls/min)
   - Model: 'rerank-english-v3.0'
2. Jina AI Reranker (1 million free tokens/month)
   - Model: 'jina-reranker-v2-base-multilingual'
3. HuggingFace Inference API (Free but rate-limited/cold starts)
   - Model: 'cross-encoder/ms-marco-MiniLM-L-6-v2' (your original model)

This module implements the Cohere API by default as it is fast, highly reliable, 
and offers a permanent free developer key.
"""

from __future__ import annotations

import logging
import httpx

from src.config import settings

logger = logging.getLogger(__name__)


def rerank(
    query: str,
    passages: list[str],
    top_k: int,
) -> list[tuple[int, float]]:
    """Score query-passage pairs using Cohere's API and return the top-k.

    Args:
        query: The search query string.
        passages: List of candidate text passages to rank.
        top_k: Number of top-ranked passages to return.

    Returns:
        List of ``(original_index, score)`` tuples sorted by score
        descending.
    """
    if not passages:
        return []

    # Get API key from settings
    api_key = getattr(settings, "cohere_api_key", None)
    if not api_key:
        logger.warning("COHERE_API_KEY not found in settings! Returning unranked results.")
        return [(i, 0.0) for i in range(min(top_k, len(passages)))]

    url = "https://api.cohere.com/v1/rerank"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    payload = {
        "model": settings.reranker_model,  # defaults to "rerank-english-v3.0"
        "query": query,
        "documents": passages,
        "top_n": top_k,
        "return_documents": False
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            # Cohere format: [{"index": original_idx, "relevance_score": float}, ...]
            results = data.get("results", [])
            
            indexed = [(item["index"], item["relevance_score"]) for item in results]
            indexed.sort(key=lambda x: x[1], reverse=True)
            return indexed
            
    except Exception as e:
        logger.error(f"Reranking API error: {e}")
        # Fallback gracefully
        return [(i, 0.0) for i in range(min(top_k, len(passages)))]
