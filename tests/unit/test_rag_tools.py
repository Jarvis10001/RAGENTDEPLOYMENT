"""Unit tests for RAG tools (omnichannel_feedback_search and marketing_content_search).

All external calls (Supabase RPC, encoder, reranker, cache) are mocked.
No test makes a real API call.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestOmnichannelFeedbackSearch:
    """Tests for the omnichannel_feedback_search tool."""

    @patch("src.tools.rag_tools.cache")
    @patch("src.tools.rag_tools.rerank")
    @patch("src.tools.rag_tools.encode")
    @patch("src.tools.rag_tools._execute_vector_rpc")
    def test_successful_search_and_rerank(
        self,
        mock_rpc: MagicMock,
        mock_encode: MagicMock,
        mock_rerank: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify the full pipeline: encode → RPC → rerank → format.

        Args:
            mock_rpc: Mocked Supabase RPC call.
            mock_encode: Mocked embedding encoder.
            mock_rerank: Mocked cross-encoder reranker.
            mock_cache: Mocked cache module.
        """
        from src.tools.rag_tools import omnichannel_feedback_search

        mock_cache.get.return_value = None
        mock_encode.return_value = [[0.1] * 384]
        mock_rpc.return_value = [
            {"text_content": "Package was damaged.", "order_id": "uuid-1", "similarity": 0.9},
            {"text_content": "Great product quality.", "order_id": "uuid-2", "similarity": 0.8},
            {"text_content": "Wrong item received.", "order_id": "uuid-3", "similarity": 0.7},
        ]
        mock_rerank.return_value = [(0, 0.95), (2, 0.82), (1, 0.71)]

        result = omnichannel_feedback_search.invoke(
            {"query": "packaging complaints"}
        )

        assert "OMNICHANNEL FEEDBACK SEARCH RESULTS" in result
        assert "Package was damaged." in result
        assert "Relevance: 0.950" in result
        mock_encode.assert_called_once()
        mock_rpc.assert_called_once()
        mock_rerank.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("src.tools.rag_tools.cache")
    def test_cache_hit_returns_cached_value(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that a cache hit returns the cached string without calling RPC.

        Args:
            mock_cache: Mocked cache module.
        """
        from src.tools.rag_tools import omnichannel_feedback_search

        mock_cache.get.return_value = "cached result string"

        result = omnichannel_feedback_search.invoke(
            {"query": "packaging complaints"}
        )

        assert result == "cached result string"

    @patch("src.tools.rag_tools.cache")
    @patch("src.tools.rag_tools.encode")
    @patch("src.tools.rag_tools._execute_vector_rpc")
    def test_empty_results_returns_no_feedback_message(
        self,
        mock_rpc: MagicMock,
        mock_encode: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that empty RPC results return a clear 'no feedback' message.

        Args:
            mock_rpc: Mocked Supabase RPC call returning empty list.
            mock_encode: Mocked embedding encoder.
            mock_cache: Mocked cache module.
        """
        from src.tools.rag_tools import omnichannel_feedback_search

        mock_cache.get.return_value = None
        mock_encode.return_value = [[0.1] * 384]
        mock_rpc.return_value = []

        result = omnichannel_feedback_search.invoke(
            {"query": "nonexistent topic"}
        )

        assert "No relevant customer feedback found" in result

    @patch("src.tools.rag_tools.cache")
    @patch("src.tools.rag_tools.encode")
    def test_error_handling_returns_formatted_error(
        self,
        mock_encode: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that exceptions are caught and returned as formatted error strings.

        Args:
            mock_encode: Mocked encoder that raises an exception.
            mock_cache: Mocked cache module.
        """
        from src.tools.rag_tools import omnichannel_feedback_search

        mock_cache.get.return_value = None
        mock_encode.side_effect = RuntimeError("Encoder model failed to load")

        result = omnichannel_feedback_search.invoke(
            {"query": "test error handling"}
        )

        assert "omnichannel_feedback_search failed" in result
        assert "RuntimeError" in result


class TestMarketingContentSearch:
    """Tests for the marketing_content_search tool."""

    @patch("src.tools.rag_tools.cache")
    @patch("src.tools.rag_tools.rerank")
    @patch("src.tools.rag_tools.encode")
    @patch("src.tools.rag_tools._execute_vector_rpc")
    def test_successful_marketing_search(
        self,
        mock_rpc: MagicMock,
        mock_encode: MagicMock,
        mock_rerank: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify the marketing search pipeline works end to end.

        Args:
            mock_rpc: Mocked Supabase RPC call.
            mock_encode: Mocked embedding encoder.
            mock_rerank: Mocked cross-encoder reranker.
            mock_cache: Mocked cache module.
        """
        from src.tools.rag_tools import marketing_content_search

        mock_cache.get.return_value = None
        mock_encode.return_value = [[0.1] * 384]
        mock_rpc.return_value = [
            {"text_content": "Summer sale: 50% off all items!", "campaign_id": "SUMMER_SALE", "similarity": 0.88},
            {"text_content": "Free shipping on orders over $50.", "campaign_id": "SUMMER_SALE", "similarity": 0.75},
        ]
        mock_rerank.return_value = [(0, 0.90), (1, 0.72)]

        result = marketing_content_search.invoke(
            {"query": "summer sale messaging", "filter_campaign_id": "SUMMER_SALE"}
        )

        assert "MARKETING CONTENT SEARCH RESULTS" in result
        assert "Summer sale" in result

    @patch("src.tools.rag_tools.cache")
    def test_marketing_cache_hit(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """Verify cache hit for marketing search.

        Args:
            mock_cache: Mocked cache module.
        """
        from src.tools.rag_tools import marketing_content_search

        mock_cache.get.return_value = "cached marketing result"

        result = marketing_content_search.invoke(
            {"query": "ad copy quality"}
        )

        assert result == "cached marketing result"

    @patch("src.tools.rag_tools.cache")
    @patch("src.tools.rag_tools.encode")
    @patch("src.tools.rag_tools._execute_vector_rpc")
    def test_marketing_empty_results(
        self,
        mock_rpc: MagicMock,
        mock_encode: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify empty results message for marketing search.

        Args:
            mock_rpc: Mocked RPC returning empty list.
            mock_encode: Mocked encoder.
            mock_cache: Mocked cache module.
        """
        from src.tools.rag_tools import marketing_content_search

        mock_cache.get.return_value = None
        mock_encode.return_value = [[0.1] * 384]
        mock_rpc.return_value = []

        result = marketing_content_search.invoke(
            {"query": "nonexistent campaign"}
        )

        assert "No relevant marketing content found" in result
