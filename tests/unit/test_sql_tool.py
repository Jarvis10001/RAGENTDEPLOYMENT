"""Unit tests for the Supabase SQL tool."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.tools.supabase_sql_tool import ALLOWED_TABLES, SupabaseSQLTool, _apply_filters


class TestSupabaseSQLTool:
    """Tests for :class:`SupabaseSQLTool`."""

    @pytest.fixture()
    def tool(self) -> SupabaseSQLTool:
        """Return a SupabaseSQLTool instance.

        Returns:
            A fresh tool instance.
        """
        return SupabaseSQLTool()

    def test_disallowed_table_returns_error(self, tool: SupabaseSQLTool) -> None:
        """Test that querying a non-allowed table returns an error."""
        query_json: str = json.dumps({"table": "users_private", "select": "*"})

        result: str = tool._run(query_json)
        parsed: dict[str, Any] = json.loads(result)

        assert "error" in parsed
        assert "not allowed" in parsed["error"]

    def test_invalid_json_returns_error(self, tool: SupabaseSQLTool) -> None:
        """Test that invalid JSON input returns an error."""
        result: str = tool._run("this is not json")
        parsed: dict[str, Any] = json.loads(result)

        assert "error" in parsed
        assert "Invalid JSON" in parsed["error"]

    def test_allowed_tables_are_correct(self) -> None:
        """Verify the set of allowed tables matches the schema."""
        expected: set[str] = {
            "customers",
            "orders",
            "shipments",
            "marketing_campaigns",
            "campaign_products",
            "events_log",
        }
        assert ALLOWED_TABLES == expected

    @patch("src.tools.supabase_sql_tool.get_supabase_client")
    def test_successful_query(
        self,
        mock_get_client: MagicMock,
        tool: SupabaseSQLTool,
    ) -> None:
        """Test a successful parameterised query execution."""
        # Set up mock chain
        mock_response = MagicMock()
        mock_response.data = [
            {"campaign_id": "CAMP-001", "cac": 85.0},
            {"campaign_id": "CAMP-002", "cac": 92.0},
        ]

        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.gt.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_response

        mock_client = MagicMock()
        mock_client.table.return_value = mock_query
        mock_get_client.return_value = mock_client

        query_json: str = json.dumps(
            {
                "table": "marketing_campaigns",
                "select": "campaign_id,cac",
                "filters": [{"column": "cac", "operator": "gt", "value": 80}],
                "order_by": "cac",
                "ascending": False,
                "limit": 10,
            }
        )

        result: str = tool._run(query_json)
        parsed: dict[str, Any] = json.loads(result)

        assert parsed["table"] == "marketing_campaigns"
        assert parsed["row_count"] == 2
        assert len(parsed["rows"]) == 2

    @patch("src.tools.supabase_sql_tool.get_supabase_client")
    def test_limit_capped_at_max(
        self,
        mock_get_client: MagicMock,
        tool: SupabaseSQLTool,
    ) -> None:
        """Test that the limit is capped at MAX_ROWS (50)."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_response

        mock_client = MagicMock()
        mock_client.table.return_value = mock_query
        mock_get_client.return_value = mock_client

        query_json: str = json.dumps(
            {"table": "orders", "select": "*", "limit": 1000}
        )
        tool._run(query_json)

        # Verify limit was called with 50 (capped)
        mock_query.limit.assert_called_once_with(50)

    def test_empty_table_name_returns_error(self, tool: SupabaseSQLTool) -> None:
        """Test that an empty table name returns an error."""
        query_json: str = json.dumps({"table": "", "select": "*"})

        result: str = tool._run(query_json)
        parsed: dict[str, Any] = json.loads(result)

        assert "error" in parsed


class TestApplyFilters:
    """Tests for the :func:`_apply_filters` helper."""

    def test_eq_filter_applied(self) -> None:
        """Test that an 'eq' filter calls the correct method."""
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query

        filters: list[dict[str, Any]] = [
            {"column": "status", "operator": "eq", "value": "active"}
        ]

        result = _apply_filters(mock_query, filters)

        mock_query.eq.assert_called_once_with("status", "active")

    def test_multiple_filters_applied(self) -> None:
        """Test that multiple filters are chained correctly."""
        mock_query = MagicMock()
        mock_query.gte.return_value = mock_query
        mock_query.lt.return_value = mock_query

        filters: list[dict[str, Any]] = [
            {"column": "cac", "operator": "gte", "value": 50},
            {"column": "cac", "operator": "lt", "value": 100},
        ]

        _apply_filters(mock_query, filters)

        mock_query.gte.assert_called_once_with("cac", 50)
        mock_query.lt.assert_called_once_with("cac", 100)

    def test_unsupported_operator_skipped(self) -> None:
        """Test that an unsupported operator is silently skipped."""
        mock_query = MagicMock()

        filters: list[dict[str, Any]] = [
            {"column": "name", "operator": "regex", "value": ".*test.*"}
        ]

        result = _apply_filters(mock_query, filters)

        # No method should have been called on the query
        assert result == mock_query

    def test_empty_filters_no_op(self) -> None:
        """Test that an empty filter list is a no-op."""
        mock_query = MagicMock()

        result = _apply_filters(mock_query, [])

        assert result == mock_query
