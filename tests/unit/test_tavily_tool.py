"""Unit tests for the web_market_search Tavily tool.

All external calls (Gemini Flash LLM, Tavily API, cache) are mocked.
No test makes a real API call.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestWebMarketSearch:
    """Tests for the web_market_search tool."""

    @patch("src.tools.tavily_tool.cache")
    @patch("src.tools.tavily_tool._execute_tavily_search")
    @patch("src.tools.tavily_tool._rewrite_query")
    def test_successful_web_search(
        self,
        mock_rewrite: MagicMock,
        mock_tavily: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify the full pipeline: rewrite query → Tavily search → format.

        Args:
            mock_rewrite: Mocked Gemini Flash query rewriter.
            mock_tavily: Mocked Tavily search execution.
            mock_cache: Mocked cache module.
        """
        from src.tools.tavily_tool import web_market_search

        mock_cache.get.return_value = None
        mock_rewrite.return_value = "ecommerce return rate benchmarks 2024"
        mock_tavily.return_value = [
            {
                "title": "E-commerce Return Rates 2024",
                "url": "https://example.com/returns-report",
                "content": "The average e-commerce return rate in 2024 is approximately 20-30%.",
                "score": 0.95,
            },
            {
                "title": "Reducing Returns in Online Retail",
                "url": "https://example.com/reduce-returns",
                "content": "Top strategies for reducing return rates include better product photos.",
                "score": 0.82,
            },
        ]

        result = web_market_search.invoke(
            {"query": "What is the industry average return rate for e-commerce in 2024?"}
        )

        assert "WEB SEARCH RESULTS" in result
        assert "ecommerce return rate benchmarks 2024" in result
        assert "https://example.com/returns-report" in result
        assert "20-30%" in result
        mock_rewrite.assert_called_once()
        mock_tavily.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("src.tools.tavily_tool.cache")
    def test_cache_hit_returns_cached_value(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that a cache hit returns the cached string immediately.

        Args:
            mock_cache: Mocked cache module.
        """
        from src.tools.tavily_tool import web_market_search

        mock_cache.get.return_value = "cached web search result"

        result = web_market_search.invoke(
            {"query": "competitor analysis"}
        )

        assert result == "cached web search result"

    @patch("src.tools.tavily_tool.cache")
    @patch("src.tools.tavily_tool._rewrite_query")
    def test_error_handling_returns_formatted_error(
        self,
        mock_rewrite: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that exceptions are caught and returned as formatted error strings.

        Args:
            mock_rewrite: Mocked query rewriter that raises an error.
            mock_cache: Mocked cache module.
        """
        from src.tools.tavily_tool import web_market_search

        mock_cache.get.return_value = None
        mock_rewrite.side_effect = RuntimeError("API key invalid")

        result = web_market_search.invoke(
            {"query": "market trends"}
        )

        assert "web_market_search failed" in result
        assert "RuntimeError" in result

    @patch("src.tools.tavily_tool.cache")
    @patch("src.tools.tavily_tool._execute_tavily_search")
    @patch("src.tools.tavily_tool._rewrite_query")
    def test_empty_tavily_results(
        self,
        mock_rewrite: MagicMock,
        mock_tavily: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify formatting when Tavily returns no results.

        Args:
            mock_rewrite: Mocked query rewriter.
            mock_tavily: Mocked Tavily search returning empty list.
            mock_cache: Mocked cache module.
        """
        from src.tools.tavily_tool import web_market_search

        mock_cache.get.return_value = None
        mock_rewrite.return_value = "obscure niche query"
        mock_tavily.return_value = []

        result = web_market_search.invoke(
            {"query": "very obscure market question"}
        )

        assert "WEB SEARCH RESULTS" in result
        assert "Results found" in result
        assert ": 0" in result
