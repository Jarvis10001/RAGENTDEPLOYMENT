"""Unit tests for the Query Router Agent output parsing and intent classification."""

from __future__ import annotations

import json

import pytest

from src.agents.query_router_agent import parse_router_output
from src.models.query_intent import QueryIntent, QueryType


class TestParseRouterOutput:
    """Tests for :func:`parse_router_output`."""

    def test_valid_json_sql_only(self) -> None:
        """Test parsing a valid JSON response for SQL-only routing."""
        raw: str = json.dumps(
            {
                "original_query": "Which campaigns have CAC above $80?",
                "needs_sql": True,
                "needs_rag": False,
                "needs_synthesis": False,
                "query_type": "campaign_performance",
                "campaign_id": None,
                "product_sku": None,
                "date_from": None,
                "date_to": None,
                "focus_metric": "cac",
                "reasoning": "Pure quantitative question.",
            }
        )

        intent: QueryIntent = parse_router_output(raw)

        assert intent.needs_sql is True
        assert intent.needs_rag is False
        assert intent.needs_synthesis is False
        assert intent.query_type == QueryType.CAMPAIGN_PERFORMANCE
        assert intent.focus_metric == "cac"

    def test_valid_json_rag_only(self) -> None:
        """Test parsing a valid JSON response for RAG-only routing."""
        raw: str = json.dumps(
            {
                "original_query": "What are customers saying about packaging?",
                "needs_sql": False,
                "needs_rag": True,
                "needs_synthesis": False,
                "query_type": "customer_sentiment",
                "reasoning": "Qualitative feedback question.",
            }
        )

        intent: QueryIntent = parse_router_output(raw)

        assert intent.needs_sql is False
        assert intent.needs_rag is True
        assert intent.query_type == QueryType.CUSTOMER_SENTIMENT

    def test_valid_json_full_pipeline(self) -> None:
        """Test parsing a valid JSON response that triggers all agents."""
        raw: str = json.dumps(
            {
                "original_query": "Why did margin drop despite more orders?",
                "needs_sql": True,
                "needs_rag": True,
                "needs_synthesis": True,
                "query_type": "profitability",
                "focus_metric": "net_profit_margin",
                "reasoning": "Needs both quantitative and qualitative analysis.",
            }
        )

        intent: QueryIntent = parse_router_output(raw)

        assert intent.needs_sql is True
        assert intent.needs_rag is True
        assert intent.needs_synthesis is True
        assert intent.query_type == QueryType.PROFITABILITY

    def test_json_with_markdown_fences(self) -> None:
        """Test that markdown code fences are stripped before parsing."""
        raw: str = '```json\n{"original_query": "test", "needs_sql": true, "query_type": "general"}\n```'

        intent: QueryIntent = parse_router_output(raw)

        assert intent.original_query == "test"
        assert intent.needs_sql is True

    def test_invalid_json_fallback(self) -> None:
        """Test that malformed output triggers the all-agents fallback."""
        raw: str = "This is not JSON at all, just natural language."

        intent: QueryIntent = parse_router_output(raw)

        assert intent.needs_sql is True
        assert intent.needs_rag is True
        assert intent.needs_synthesis is True
        assert intent.query_type == QueryType.GENERAL
        assert "fallback" in intent.reasoning.lower()

    def test_unknown_query_type_defaults_to_general(self) -> None:
        """Test that an unrecognised query_type falls back to GENERAL."""
        raw: str = json.dumps(
            {
                "original_query": "Something novel",
                "needs_sql": True,
                "query_type": "unknown_category",
                "reasoning": "Test.",
            }
        )

        intent: QueryIntent = parse_router_output(raw)

        assert intent.query_type == QueryType.GENERAL

    def test_extracted_filters(self) -> None:
        """Test that campaign_id, product_sku, and date filters are extracted."""
        raw: str = json.dumps(
            {
                "original_query": "Show campaign CAMP-001 results for SKU-4421 in March",
                "needs_sql": True,
                "needs_rag": False,
                "needs_synthesis": False,
                "query_type": "campaign_performance",
                "campaign_id": "CAMP-001",
                "product_sku": "SKU-4421",
                "date_from": "2025-03-01",
                "date_to": "2025-03-31",
                "reasoning": "Specific campaign and product query.",
            }
        )

        intent: QueryIntent = parse_router_output(raw)

        assert intent.campaign_id == "CAMP-001"
        assert intent.product_sku == "SKU-4421"
        assert intent.date_from == "2025-03-01"
        assert intent.date_to == "2025-03-31"

    def test_empty_original_query_in_fallback(self) -> None:
        """Test that the fallback preserves the raw output as original_query."""
        raw: str = "Not parseable"

        intent: QueryIntent = parse_router_output(raw)

        assert intent.original_query == raw
