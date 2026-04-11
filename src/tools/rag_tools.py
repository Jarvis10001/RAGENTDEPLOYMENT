"""RAG tools — vector-search-backed retrieval for customer feedback and marketing content.

Tool 1: ``omnichannel_feedback_search``
    Searches customer feedback, support tickets, product reviews via
    ``match_omnichannel_vectors`` RPC on Supabase pgvector.

Tool 2: ``marketing_content_search``
    Searches marketing campaign content, ad copy, briefs via
    ``match_marketing_vectors`` RPC on Supabase pgvector.

Both tools follow the same pipeline:
    cache check → embed → vector search → cross-encoder rerank → format → cache write.

The retrieve and rerank counts default to ``settings.rag_retrieve_k`` and
``settings.rag_rerank_k`` respectively, keeping configuration centralised.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.tools import tool

from src.cache import response_cache as cache
from src.config import settings
from src.db.supabase_client import get_supabase_client
from src.embeddings.encoder import encode
from src.embeddings.reranker import rerank
from src.models.tool_inputs import MarketingSearchInput, OmnichannelSearchInput
from src.utils.retry import exponential_backoff

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# TOOL 1: omnichannel_feedback_search
# ═══════════════════════════════════════════════════════════════════════


@tool("omnichannel_feedback_search", args_schema=OmnichannelSearchInput)
def omnichannel_feedback_search(
    query: str,
    filter_order_id: str | None = None,
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
) -> str:
    """Search customer feedback, support tickets, product reviews, and
    omnichannel communication logs stored as vector embeddings in
    Supabase. Use this for ANY question about what customers are
    saying, feeling, complaining about, or praising. ALWAYS use this
    alongside SQL tools when diagnosing root causes of revenue drops,
    margin compression, or operational issues. Returns semantically
    reranked text passages with relevance scores.

    Args:
        query: Natural-language search query about customer feedback.
        filter_order_id: Optional UUID to restrict results to a specific order.
        top_k_retrieve: Candidates to retrieve from pgvector (default 20).
        top_k_rerank: Results to keep after cross-encoder reranking (default 5).

    Returns:
        Formatted string with reranked customer feedback passages and
        relevance scores, or an error message if the search fails.
    """
    logger.info(
        "omnichannel_feedback_search called — query=%r filter_order_id=%s",
        query[:80],
        filter_order_id,
    )
    return _run_rag_pipeline(
        tool_name="omnichannel_feedback_search",
        rpc_function="match_omnichannel_vectors",
        title="OMNICHANNEL FEEDBACK SEARCH RESULTS",
        cache_namespace="omnichannel",
        no_results_message="No relevant customer feedback found for this query.",
        query=query,
        filter_value=filter_order_id,
        filter_key="filter_order_id",
        top_k_retrieve=top_k_retrieve,
        top_k_rerank=top_k_rerank,
    )


# ═══════════════════════════════════════════════════════════════════════
# TOOL 2: marketing_content_search
# ═══════════════════════════════════════════════════════════════════════


@tool("marketing_content_search", args_schema=MarketingSearchInput)
def marketing_content_search(
    query: str,
    filter_campaign_id: str | None = None,
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
) -> str:
    """Search marketing campaign content including ad copy, campaign
    briefs, and promotional materials stored as vector embeddings
    in Supabase. Use this when the analyst asks about campaign
    messaging quality, ad creative alignment, what a specific
    campaign promised to customers, or to cross-reference marketing
    claims against actual customer feedback.

    Args:
        query: Natural-language search query about marketing content.
        filter_campaign_id: Optional campaign ID to filter results.
        top_k_retrieve: Candidates to retrieve from pgvector (default 20).
        top_k_rerank: Results to keep after cross-encoder reranking (default 5).

    Returns:
        Formatted string with reranked marketing content passages and
        relevance scores, or an error message if the search fails.
    """
    logger.info(
        "marketing_content_search called — query=%r filter_campaign_id=%s",
        query[:80],
        filter_campaign_id,
    )
    return _run_rag_pipeline(
        tool_name="marketing_content_search",
        rpc_function="match_marketing_vectors",
        title="MARKETING CONTENT SEARCH RESULTS",
        cache_namespace="marketing",
        no_results_message="No relevant marketing content found for this query.",
        query=query,
        filter_value=filter_campaign_id,
        filter_key="filter_campaign_id",
        top_k_retrieve=top_k_retrieve,
        top_k_rerank=top_k_rerank,
    )


# ═══════════════════════════════════════════════════════════════════════
# Shared private helpers
# ═══════════════════════════════════════════════════════════════════════


def _run_rag_pipeline(
    *,
    tool_name: str,
    rpc_function: str,
    title: str,
    cache_namespace: str,
    no_results_message: str,
    query: str,
    filter_value: str | None,
    filter_key: str,
    top_k_retrieve: int,
    top_k_rerank: int,
) -> str:
    """Execute the shared RAG pipeline used by both retrieval tools.

    Centralising the pipeline eliminates code duplication and ensures
    identical caching, error-handling, and formatting behaviour.

    Args:
        tool_name: Name for error messages and logging.
        rpc_function: Supabase RPC function to call for similarity search.
        title: Header title for the formatted output block.
        cache_namespace: Prefix used in the cache key.
        no_results_message: User-facing message when no chunks are found.
        query: The analyst's natural-language query.
        filter_value: Optional filter value (order_id or campaign_id).
        filter_key: The RPC parameter name for the filter value.
        top_k_retrieve: Number of candidates to retrieve from pgvector.
        top_k_rerank: Number of results to keep after reranking.

    Returns:
        Formatted output string with passages and relevance scores.
    """
    try:
        # Step 1: Cache check
        cache_key = cache.make_key(cache_namespace, query, filter_value, top_k_retrieve, top_k_rerank)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit for %s.", tool_name)
            return cached

        # Step 2: Embed the query into a vector
        embedding = encode([query])

        # Step 3: Similarity search via Supabase pgvector RPC
        rpc_params: dict[str, Any] = {
            "query_embedding": embedding[0],
            "match_count": top_k_retrieve,
        }
        if filter_value:
            rpc_params[filter_key] = filter_value

        results = _execute_vector_rpc(rpc_function, rpc_params)

        if not results:
            return no_results_message

        # Step 4: Cross-encoder reranking for precision
        texts = [row.get("text_content", "") for row in results]
        reranked = rerank(query, texts, top_k_rerank)

        # Step 5: Format ranked passages for the agent
        output = _format_rag_output(
            title=title,
            query=query,
            total_retrieved=len(results),
            reranked_results=reranked,
            texts=texts,
        )

        # Step 6: Cache the formatted result
        cache.set(cache_key, output, ttl=settings.cache_ttl_seconds)

        return output

    except Exception as e:
        logger.error("%s failed: %s: %s", tool_name, type(e).__name__, e)
        return f"{tool_name} failed: {type(e).__name__}: {e}"


@exponential_backoff(max_retries=3, base_delay_seconds=2.0)
def _execute_vector_rpc(
    function_name: str,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute a Supabase RPC call for pgvector similarity search.

    Args:
        function_name: Name of the Supabase RPC function to call.
        params: Parameter dictionary for the RPC call.

    Returns:
        List of matching row dictionaries from the RPC response.

    Raises:
        Exception: Propagated after all retry attempts are exhausted.
    """
    client = get_supabase_client()
    response = client.rpc(function_name, params).execute()
    data: list[dict[str, Any]] = response.data or []
    logger.info("RPC %s returned %d results.", function_name, len(data))
    return data


def _format_rag_output(
    title: str,
    query: str,
    total_retrieved: int,
    reranked_results: list[tuple[int, float]],
    texts: list[str],
    max_chars_per_passage: int = 350,
) -> str:
    """Format reranked RAG results into a structured string for the agent.

    Args:
        title: Section header for the output block.
        query: The original search query.
        total_retrieved: Total chunks retrieved before reranking.
        reranked_results: ``(original_index, score)`` pairs from the reranker.
        texts: Original text passages, aligned by index.
        max_chars_per_passage: Maximum characters to include per passage.

    Returns:
        Formatted multi-line string with numbered, scored passages.
    """
    reranked_count = len(reranked_results)
    lines: list[str] = [
        title,
        f"Query     : {query}",
        f"Retrieved : {total_retrieved} chunks → Reranked to {reranked_count}",
        "─────────────────────────────────────",
    ]

    for rank, (orig_idx, score) in enumerate(reranked_results, start=1):
        text = texts[orig_idx][:max_chars_per_passage]
        if len(texts[orig_idx]) > max_chars_per_passage:
            text += "…"
        lines.append(f"[{rank}] Relevance: {score:.3f}")
        lines.append(text)
        lines.append("─────────────────────────────────────")

    return "\n".join(lines)
