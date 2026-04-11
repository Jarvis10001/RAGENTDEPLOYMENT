"""LangChain tool wrapping pgvector cosine-similarity search via Supabase RPC.

Searches ``omnichannel_vectors`` (customer feedback, reviews, support tickets)
and ``marketing_vectors`` (ad copy, campaign briefs) using HNSW-indexed
cosine similarity, then returns ranked results for downstream reranking.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from crewai.tools import BaseTool
from pydantic import Field
from sentence_transformers import SentenceTransformer

from src.config import get_settings
from src.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Lazy-loaded embedding model
_embedding_model: Optional[SentenceTransformer] = None


def _get_embedding_model() -> SentenceTransformer:
    """Return a lazily-initialised SentenceTransformer model.

    Returns:
        A :class:`SentenceTransformer` instance loaded with the
        configured model name.
    """
    global _embedding_model
    if _embedding_model is None:
        settings = get_settings()
        logger.info("Loading embedding model: %s", settings.embedding_model_name)
        _embedding_model = SentenceTransformer(settings.embedding_model_name)
    return _embedding_model


def embed_query(text: str) -> list[float]:
    """Embed a single query string into a dense vector.

    Args:
        text: The query text to embed.

    Returns:
        A list of floats representing the embedding vector.
    """
    model = _get_embedding_model()
    embedding: list[float] = model.encode(text, normalize_embeddings=True).tolist()
    return embedding


class VectorSearchTool(BaseTool):
    """Perform cosine-similarity search on Supabase vector tables via RPC.

    The tool accepts a JSON input string with the following keys:

    * ``query_text`` (str): The natural-language query to embed.
    * ``table`` (str): Either ``"omnichannel"`` or ``"marketing"``.
    * ``filter_order_id`` (str | None): Optional UUID to filter on order_id.
    * ``filter_campaign_id`` (str | None): Optional string to filter on campaign_id.
    * ``match_count`` (int): Number of candidates to retrieve (default: 20).

    Attributes:
        name: Tool name visible to the agent.
        description: Human-readable purpose.
    """

    name: str = "vector_similarity_search"
    description: str = (
        "Search Supabase pgvector tables for semantically similar text chunks. "
        "Input: JSON with keys query_text, table ('omnichannel' or 'marketing'), "
        "filter_order_id (optional UUID), filter_campaign_id (optional), "
        "match_count (optional int, default 20). "
        "Returns ranked results with text_content and similarity scores."
    )

    def _run(self, query_json: str) -> str:
        """Execute vector similarity search against the specified table.

        Args:
            query_json: JSON string describing the search parameters.

        Returns:
            JSON string containing the search results or an error message.

        Raises:
            ValueError: If the table parameter is invalid.
        """
        try:
            params: dict[str, Any] = json.loads(query_json)
        except json.JSONDecodeError as exc:
            error_msg = f"Invalid JSON input: {exc}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

        query_text: str = params.get("query_text", "")
        if not query_text.strip():
            return json.dumps({"error": "query_text must be non-empty."})

        table: str = params.get("table", "omnichannel")
        filter_order_id: Optional[str] = params.get("filter_order_id")
        filter_campaign_id: Optional[str] = params.get("filter_campaign_id")
        settings = get_settings()
        match_count: int = params.get("match_count", settings.vector_search_top_k)

        # Embed the query
        embedding: list[float] = embed_query(query_text)

        client = get_supabase_client()

        if table == "omnichannel":
            result = _search_omnichannel(
                client, embedding, match_count, filter_order_id
            )
        elif table == "marketing":
            result = _search_marketing(
                client, embedding, match_count, filter_campaign_id
            )
        else:
            return json.dumps(
                {"error": f"Unknown table '{table}'. Use 'omnichannel' or 'marketing'."}
            )

        return json.dumps(result, default=str)


def _search_omnichannel(
    client: Any,
    embedding: list[float],
    match_count: int,
    filter_order_id: Optional[str],
) -> dict[str, Any]:
    """Search the ``omnichannel_vectors`` table via the RPC function.

    Args:
        client: Supabase client instance.
        embedding: Query embedding vector.
        match_count: Maximum number of results.
        filter_order_id: Optional order UUID filter.

    Returns:
        Dictionary with ``results`` key containing a list of matches.
    """
    rpc_params: dict[str, Any] = {
        "query_embedding": embedding,
        "match_count": match_count,
    }
    if filter_order_id:
        rpc_params["filter_order_id"] = filter_order_id

    logger.info(
        "RPC match_omnichannel_vectors — match_count=%d filter_order_id=%s",
        match_count,
        filter_order_id,
    )

    try:
        response = client.rpc("match_omnichannel_vectors", rpc_params).execute()
        data: list[dict[str, Any]] = response.data if response.data else []
        logger.info("Omnichannel vector search returned %d results.", len(data))
        return {"source": "omnichannel_vectors", "result_count": len(data), "results": data}
    except Exception as exc:
        error_msg = f"Omnichannel vector search failed: {exc}"
        logger.error(error_msg)
        return {"error": error_msg}


def _search_marketing(
    client: Any,
    embedding: list[float],
    match_count: int,
    filter_campaign_id: Optional[str],
) -> dict[str, Any]:
    """Search the ``marketing_vectors`` table via the RPC function.

    Args:
        client: Supabase client instance.
        embedding: Query embedding vector.
        match_count: Maximum number of results.
        filter_campaign_id: Optional campaign ID filter.

    Returns:
        Dictionary with ``results`` key containing a list of matches.
    """
    rpc_params: dict[str, Any] = {
        "query_embedding": embedding,
        "match_count": match_count,
    }
    if filter_campaign_id:
        rpc_params["filter_campaign_id"] = filter_campaign_id

    logger.info(
        "RPC match_marketing_vectors — match_count=%d filter_campaign_id=%s",
        match_count,
        filter_campaign_id,
    )

    try:
        response = client.rpc("match_marketing_vectors", rpc_params).execute()
        data: list[dict[str, Any]] = response.data if response.data else []
        logger.info("Marketing vector search returned %d results.", len(data))
        return {"source": "marketing_vectors", "result_count": len(data), "results": data}
    except Exception as exc:
        error_msg = f"Marketing vector search failed: {exc}"
        logger.error(error_msg)
        return {"error": error_msg}
