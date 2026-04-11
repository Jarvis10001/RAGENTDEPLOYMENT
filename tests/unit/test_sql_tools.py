"""Unit tests for SQL tools (ecommerce_sql_query and ecommerce_analytics_query).

All external calls (Gemini Flash LLM, Supabase RPC, cache) are mocked.
No test makes a real API call.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestEcommerceSqlQuery:
    """Tests for the ecommerce_sql_query tool."""

    @patch("src.tools.sql_tools.cache")
    @patch("src.tools.sql_tools._execute_sql")
    @patch("src.tools.sql_tools._generate_sql")
    def test_successful_sql_generation_and_execution(
        self,
        mock_gen: MagicMock,
        mock_exec: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify the full pipeline: generate SQL → validate → execute → format.

        Args:
            mock_gen: Mocked SQL generation via Gemini Flash.
            mock_exec: Mocked SQL execution via Supabase RPC.
            mock_cache: Mocked cache module.
        """
        from src.tools.sql_tools import ecommerce_sql_query

        mock_cache.get.return_value = None
        mock_gen.return_value = "SELECT campaign_id, cac FROM marketing_campaigns WHERE cac > 80 LIMIT 10"
        mock_exec.return_value = [
            {"campaign_id": "WINTER_PROMO", "cac": 82.00},
            {"campaign_id": "BRAND_PUSH", "cac": 95.50},
        ]

        result = ecommerce_sql_query.invoke(
            {"question": "Which campaigns have CAC above $80?"}
        )

        assert "SQL QUERY RESULT" in result
        assert "WINTER_PROMO" in result
        assert "Rows     : 2" in result
        mock_gen.assert_called_once()
        mock_exec.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("src.tools.sql_tools.cache")
    def test_cache_hit_returns_cached_value(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that a cache hit returns the cached string immediately.

        Args:
            mock_cache: Mocked cache module.
        """
        from src.tools.sql_tools import ecommerce_sql_query

        mock_cache.get.return_value = "cached SQL result"

        result = ecommerce_sql_query.invoke(
            {"question": "What is total revenue?"}
        )

        assert result == "cached SQL result"

    @patch("src.tools.sql_tools.cache")
    @patch("src.tools.sql_tools._generate_sql")
    def test_dml_rejection_raises_error(
        self,
        mock_gen: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that generated SQL containing DML keywords is rejected.

        Args:
            mock_gen: Mocked SQL generation returning a DELETE statement.
            mock_cache: Mocked cache module.
        """
        from src.tools.sql_tools import ecommerce_sql_query

        mock_cache.get.return_value = None
        mock_gen.return_value = "DELETE FROM orders WHERE order_id = '123'"

        result = ecommerce_sql_query.invoke(
            {"question": "Delete all orders"}
        )

        assert "ecommerce_sql_query failed" in result
        assert "ValueError" in result

    @patch("src.tools.sql_tools.cache")
    @patch("src.tools.sql_tools._generate_sql")
    def test_non_select_rejection(
        self,
        mock_gen: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify that SQL not starting with SELECT is rejected.

        Args:
            mock_gen: Mocked SQL generation returning an UPDATE.
            mock_cache: Mocked cache module.
        """
        from src.tools.sql_tools import ecommerce_sql_query

        mock_cache.get.return_value = None
        mock_gen.return_value = "UPDATE orders SET status = 'cancelled'"

        result = ecommerce_sql_query.invoke(
            {"question": "Cancel all orders"}
        )

        assert "ecommerce_sql_query failed" in result


class TestEcommerceAnalyticsQuery:
    """Tests for the ecommerce_analytics_query tool."""

    @patch("src.tools.sql_tools.cache")
    @patch("src.tools.sql_tools._execute_sql")
    @patch("src.tools.sql_tools._generate_sql")
    def test_successful_analytics_query(
        self,
        mock_gen: MagicMock,
        mock_exec: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify analytics pipeline with GROUP BY produces trend note.

        Args:
            mock_gen: Mocked SQL generation with GROUP BY.
            mock_exec: Mocked SQL execution.
            mock_cache: Mocked cache module.
        """
        from src.tools.sql_tools import ecommerce_analytics_query

        mock_cache.get.return_value = None
        mock_gen.return_value = (
            "SELECT DATE_TRUNC('month', order_date) AS month, "
            "COUNT(*) AS order_count FROM orders GROUP BY 1 LIMIT 20"
        )
        mock_exec.return_value = [
            {"month": "2024-01", "order_count": 1200},
            {"month": "2024-02", "order_count": 1500},
        ]

        result = ecommerce_analytics_query.invoke(
            {"question": "Show monthly order trends"}
        )

        assert "SQL QUERY RESULT" in result
        assert "Trend note" in result
        assert "1200" in result

    @patch("src.tools.sql_tools.cache")
    def test_analytics_cache_hit(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """Verify cache hit for analytics query.

        Args:
            mock_cache: Mocked cache module.
        """
        from src.tools.sql_tools import ecommerce_analytics_query

        mock_cache.get.return_value = "cached analytics result"

        result = ecommerce_analytics_query.invoke(
            {"question": "Monthly revenue breakdown"}
        )

        assert result == "cached analytics result"

    @patch("src.tools.sql_tools.cache")
    @patch("src.tools.sql_tools._generate_sql")
    def test_analytics_error_handling(
        self,
        mock_gen: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Verify error handling when SQL generation fails.

        Args:
            mock_gen: Mocked SQL generation that raises an error.
            mock_cache: Mocked cache module.
        """
        from src.tools.sql_tools import ecommerce_analytics_query

        mock_cache.get.return_value = None
        mock_gen.side_effect = RuntimeError("LLM quota exceeded")

        result = ecommerce_analytics_query.invoke(
            {"question": "Complex analytics query"}
        )

        assert "ecommerce_analytics_query failed" in result
