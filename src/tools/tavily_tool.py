"""Tavily web search tool — live internet search for external market data.

Tool 5: ``web_market_search``
    Searches the live web via Tavily for industry benchmarks, competitor
    intelligence, current market conditions, and any information not
    available in the internal Supabase database.

Pipeline: cache check → Gemini Flash rewrites query → Tavily search →
format with URLs → cache write.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.tools import tool

from src.cache import response_cache as cache
from src.config import settings
from src.llm import get_sub_llm
from src.models.tool_inputs import TavilySearchInput
from src.utils.retry import exponential_backoff

logger = logging.getLogger(__name__)


@tool("web_market_search", args_schema=TavilySearchInput)
def web_market_search(
    query: str,
    search_depth: str = "advanced",
    max_results: int = 5,
) -> str:
    """Search the live internet for current market data, industry
    benchmarks, competitor intelligence, e-commerce trends, and any
    information that is NOT in the internal Supabase database. Use
    this when the analyst asks about industry averages, what
    competitors are doing, current market conditions, or for any
    question that requires information beyond internal data. Always
    returns source URLs for citation.

    Args:
        query: Natural-language question requiring current web data.
        search_depth: Tavily search depth — ``basic`` (fast) or ``advanced`` (thorough).
        max_results: Maximum number of web results to return (default 5).

    Returns:
        Formatted string with numbered web search results and source URLs, or
        an error message if the search fails.
    """
    logger.info("web_market_search called — query=%r depth=%s", query[:80], search_depth)
    try:
        # Step 1: Check cache (shorter TTL — web data changes frequently)
        cache_key = cache.make_key("tavily", query, search_depth, max_results)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit for web search.")
            return cached

        # Step 2: Check domain safety and rewrite question
        search_query = _rewrite_query(query)
        if search_query.strip() == "REJECTED_DOMAIN":
            logger.warning("Query rejected by domain filter: %s", query)
            return "Error: Question is not related to e-commerce, retail, or business intelligence. Web search declined."

        # Step 3: Execute Tavily search
        raw_results = _execute_tavily_search(search_query, search_depth, max_results)

        # Step 4: Format output for the agent
        output = _format_web_output(
            original_query=query,
            search_query=search_query,
            results=raw_results,
        )

        # Step 5: Cache with shorter TTL (30 min default)
        cache.set(cache_key, output, ttl=settings.tavily_cache_ttl_seconds)

        return output

    except Exception as e:
        logger.error("web_market_search failed: %s: %s", type(e).__name__, e)
        return f"web_market_search failed: {type(e).__name__}: {e}"


@exponential_backoff(max_retries=0, base_delay_seconds=2.0)
def _rewrite_query(query: str) -> str:
    """Use Gemini Flash to rewrite an analyst question into an optimal web search query.

    Args:
        query: The analyst's raw natural-language question.

    Returns:
        A concise, optimised web search query string (max ~12 words).
    """
    prompt = (
        "You are an E-Commerce Business Intelligence agent. You must ONLY process queries strictly related "
        "to e-commerce, retail, market competitors, supply chain, or financial metrics. "
        "If the following question is UNRELATED to business domains, return EXACTLY: 'REJECTED_DOMAIN'. "
        "Otherwise, rewrite the analyst question as a concise, effective web search query of at most 12 words. "
        "Return ONLY the rewritten query or 'REJECTED_DOMAIN'.\n\n"
        f"Question: {query}"
    )
    search_query: str = get_sub_llm().invoke(prompt).content.strip()
    logger.info("Rewritten search query: %r", search_query)
    return search_query or query  # fall back to original if rewriter returns empty


@exponential_backoff(max_retries=0, base_delay_seconds=2.0)
def _execute_tavily_search(
    search_query: str,
    search_depth: str,
    max_results: int,
) -> list[dict[str, Any]]:
    """Execute a Tavily web search and return raw results.

    Args:
        search_query: The optimised search query string.
        search_depth: ``basic`` or ``advanced``.
        max_results: Maximum number of results to return.

    Returns:
        List of result dictionaries containing ``url``, ``content``,
        ``title``, and ``score`` keys.

    Raises:
        Exception: Propagated after all retry attempts are exhausted.
    """
    from tavily import TavilyClient  # local import keeps startup fast

    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(
        query=search_query,
        search_depth=search_depth,
        max_results=max_results,
        include_answer=False,
    )
    results: list[dict[str, Any]] = response.get("results", [])
    logger.info("Tavily search returned %d results.", len(results))
    return results


def _format_web_output(
    original_query: str,
    search_query: str,
    results: list[dict[str, Any]],
) -> str:
    """Format Tavily search results into a structured string for the agent.

    Args:
        original_query: The analyst's original question.
        search_query: The optimised search query that was used.
        results: List of Tavily result dictionaries.

    Returns:
        Formatted multi-line string with numbered results and source URLs.
    """
    lines: list[str] = [
        "WEB SEARCH RESULTS",
        "─────────────────────────────────────",
        f"Original question : {original_query}",
        f"Search query used : {search_query}",
        f"Results found     : {len(results)}",
        "─────────────────────────────────────",
    ]

    for idx, result in enumerate(results, start=1):
        title = result.get("title", "No title")
        url = result.get("url", "No URL")
        content = result.get("content", "No content")[:300]
        score = result.get("score", 0.0)
        lines.append(f"[{idx}] {title}  (relevance: {score:.2f})")
        lines.append(f"    URL: {url}")
        lines.append(f"    {content}")
        lines.append("─────────────────────────────────────")

    return "\n".join(lines)
