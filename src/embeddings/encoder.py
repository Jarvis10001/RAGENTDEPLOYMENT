"""Google Gemini embedding API encoder.

Uses the new ``google.genai`` SDK (google-genai) to generate text embeddings.
This replaces the legacy ``google.generativeai`` package which is incompatible
with ``langchain-google-genai`` 3.1.0.

Thread-safety
-------------
The google.genai Client is thread-safe and reused for all requests.
"""

from __future__ import annotations

import logging

from src.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Return the shared Google GenAI client, initializing on first call.

    Returns:
        google.genai.Client: Configured API client.
    """
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.google_api_key)
        logger.info("Initialized google.genai Client for embeddings")
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

        # Batch encode texts using the new google.genai SDK
        for text in texts:
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config={"output_dimensionality": 768},
            )
            embeddings.append(response.embeddings[0].values)

        logger.debug(f"Successfully encoded {len(texts)} texts using Google GenAI SDK")
        return embeddings

    except Exception as e:
        logger.error(f"Error encoding texts with Google GenAI SDK: {e}")
        raise
