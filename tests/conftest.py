"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import json
import os
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from src.models.diagnostic_report import ActionItem, DiagnosticReport
from src.models.query_intent import QueryIntent, QueryType
from src.models.rag_result import RAGResult
from src.models.sql_result import Severity, SQLAnalysisResult


# ── Ensure test environment variables are set ────────────
@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject minimal environment variables for all tests.

    This prevents pydantic-settings from failing when loading config
    during tests that don't touch external services.
    """
    monkeypatch.setenv("SUPABASE_URL", "https://test-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key-placeholder")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral-key-placeholder")
    monkeypatch.setenv("PHOENIX_ENABLED", "false")
    monkeypatch.setenv("DEBUG", "false")


# ── Sample QueryIntent fixtures ─────────────────────────
@pytest.fixture()
def sample_sql_only_intent() -> QueryIntent:
    """Return a QueryIntent that triggers SQL analysis only.

    Returns:
        A :class:`QueryIntent` with ``needs_sql=True``.
    """
    return QueryIntent(
        original_query="Which campaigns have CAC above $80?",
        needs_sql=True,
        needs_rag=False,
        needs_synthesis=False,
        query_type=QueryType.CAMPAIGN_PERFORMANCE,
        focus_metric="cac",
        reasoning="Pure quantitative question about campaign metrics.",
    )


@pytest.fixture()
def sample_rag_only_intent() -> QueryIntent:
    """Return a QueryIntent that triggers RAG retrieval only.

    Returns:
        A :class:`QueryIntent` with ``needs_rag=True``.
    """
    return QueryIntent(
        original_query="What are customers saying about packaging quality?",
        needs_sql=False,
        needs_rag=True,
        needs_synthesis=False,
        query_type=QueryType.CUSTOMER_SENTIMENT,
        reasoning="Pure qualitative question about customer feedback.",
    )


@pytest.fixture()
def sample_full_intent() -> QueryIntent:
    """Return a QueryIntent that triggers all agents.

    Returns:
        A :class:`QueryIntent` with all needs flags set.
    """
    return QueryIntent(
        original_query="Why did net profit margin drop 12% despite 20% more orders?",
        needs_sql=True,
        needs_rag=True,
        needs_synthesis=True,
        query_type=QueryType.PROFITABILITY,
        focus_metric="net_profit_margin",
        reasoning="Requires both quantitative and qualitative analysis.",
    )


@pytest.fixture()
def sample_sql_result() -> SQLAnalysisResult:
    """Return a sample SQLAnalysisResult for testing.

    Returns:
        A populated :class:`SQLAnalysisResult`.
    """
    return SQLAnalysisResult(
        sql_executed="SELECT avg(net_profit_margin) FROM orders GROUP BY month",
        key_metrics={
            "avg_margin_this_month": 0.08,
            "avg_margin_last_month": 0.20,
            "margin_change": -0.12,
            "total_orders": 1500,
            "split_shipment_rate": 0.35,
        },
        affected_segment="All orders in the last 30 days",
        severity=Severity.HIGH,
        raw_rows=[
            {"month": "2025-03", "avg_margin": 0.20, "order_count": 1200},
            {"month": "2025-04", "avg_margin": 0.08, "order_count": 1500},
        ],
        analysis_summary=(
            "Net profit margin dropped from 20% to 8% month-over-month "
            "despite a 25% increase in order volume.  Split shipment rate "
            "rose to 35%, suggesting logistics costs are eroding margins."
        ),
        query_type="profitability",
    )


@pytest.fixture()
def sample_rag_result() -> RAGResult:
    """Return a sample RAGResult for testing.

    Returns:
        A populated :class:`RAGResult`.
    """
    return RAGResult(
        top_themes=[
            "Damaged packaging on arrival",
            "Slow delivery times",
            "Wrong items received",
        ],
        representative_quotes=[
            "My package arrived completely crushed and the product was broken.",
            "I waited 14 days for a 2-day shipping order.",
            "Received a completely different product than what I ordered.",
        ],
        source_breakdown={"reviews": 12, "support_tickets": 8, "survey_responses": 3},
        sentiment_scores={"negative": 0.72, "neutral": 0.18, "positive": 0.10},
        urgency_signals=[
            "Multiple mentions of chargeback requests",
            "Social media complaints trending",
        ],
        full_narrative=(
            "Customer feedback reveals a significant deterioration in "
            "fulfilment quality.  Packaging damage, delayed shipments, "
            "and order accuracy issues are driving negative sentiment.  "
            "Several customers mentioned filing chargebacks."
        ),
    )


@pytest.fixture()
def sample_diagnostic_report() -> DiagnosticReport:
    """Return a sample DiagnosticReport for testing.

    Returns:
        A populated :class:`DiagnosticReport`.
    """
    return DiagnosticReport(
        executive_summary=(
            "Net profit margin declined 12 percentage points due to a "
            "35% split shipment rate and rising fulfilment complaints."
        ),
        confirmed_root_cause=(
            "Inventory misalignment across warehouses is forcing expensive "
            "split shipments, while packaging quality issues are driving "
            "returns and chargebacks."
        ),
        contributing_factors=[
            "35% split shipment rate increasing freight costs",
            "Packaging damage causing returns",
            "Customer chargeback threats",
        ],
        revenue_impact_estimate="$45,000/month in excess freight + returns",
        urgency_score=8,
        confidence_score=7,
        action_items=[
            ActionItem(
                action="Redistribute inventory to reduce split shipments.",
                owner="Supply Chain",
                priority="immediate",
                expected_impact="Reduce freight costs by ~30%.",
            ),
            ActionItem(
                action="Audit packaging materials and processes.",
                owner="Operations",
                priority="short_term",
                expected_impact="Reduce damage complaints by 50%.",
            ),
        ],
        data_gaps=["Per-warehouse inventory levels not available in schema."],
        supporting_sql_evidence={"split_shipment_rate": 0.35, "margin_change": -0.12},
        supporting_rag_evidence=["Package arrived completely crushed"],
    )


# ── Mock Supabase client fixture ─────────────────────────
@pytest.fixture()
def mock_supabase_client() -> Generator[MagicMock, None, None]:
    """Provide a mocked Supabase client.

    Yields:
        A :class:`MagicMock` replacing the real Supabase client.
    """
    mock_client = MagicMock()
    with patch("src.db.supabase_client.get_supabase_client", return_value=mock_client):
        yield mock_client
