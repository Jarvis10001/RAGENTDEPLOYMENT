"""Google Gemini embedding API encoder.

Uses the Google Generative AI API to generate text embeddings.
No local model loading required — all embeddings are computed server-side.

Thread-safety
-------------
The google-generativeai client is thread-safe and reused for all requests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.config import settings

if TYPE_CHECKING:
    import google.generativeai as genai

logger = logging.getLogger(__name__)

_client: genai.generativeai.GenerativeAI | None = None


def get_client():
    """Return the shared Google Generative AI client, initializing on first call.

    Returns:
        google.generativeai.GenerativeAI: Configured API client.
    """
    global _client
    if _client is None:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_api_key)
        _client = genai
        logger.info("Initialized Google Generative AI client for embeddings")
    return _client


def encode(texts: list[str]) -> list[list[float]]:
    """Encode a batch of texts using Google's embedding API.

    Args:
        texts: List of strings to embed.

    Returns:
        List of embedding vectors (dimension varies by model, typically 768).

    Raises:
        ValueError: If texts list is empty or API call fails.
    """
    if not texts:
        raise ValueError("Cannot encode empty list of texts")

    try:
        client = get_client()
        embeddings = []
        
        # Batch encode texts using Google's API
        for text in texts:
            response = client.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                output_dimensionality=768,
            )
            embeddings.append(response["embedding"])
        
        logger.debug(f"Successfully encoded {len(texts)} texts using Google Embedding API")
        return embeddings
        
    except Exception as e:
        logger.error(f"Error encoding texts with Google API: {e}")
        raise
