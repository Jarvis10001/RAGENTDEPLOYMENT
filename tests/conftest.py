"""Shared pytest fixtures for the test suite.

Provides mock environment variables, mock Supabase client, mock LLMs,
sample data fixtures, and other test utilities used across unit and
integration tests.

NOTE: Environment variables are set at module level (before any src
imports) to ensure pydantic-settings can construct the ``Settings``
singleton without validation errors.
"""

from __future__ import annotations

import os

# ── Set env vars BEFORE any src imports (module-level) ───────────────
# This is necessary because src.config creates a module-level
# ``settings = Settings()`` that validates env vars on import.
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key-placeholder")
os.environ.setdefault("GOOGLE_API_KEY", "test-gemini-key-placeholder")
os.environ.setdefault("TAVILY_API_KEY", "tvly-test-key-placeholder")
os.environ.setdefault("PRIMARY_MODEL", "gemini-1.5-pro")
os.environ.setdefault("SUB_AGENT_MODEL", "gemini-1.5-flash")
os.environ.setdefault("MAX_SQL_ROWS", "10")
os.environ.setdefault("PHOENIX_ENABLED", "false")
os.environ.setdefault("CACHE_ENABLED", "false")
os.environ.setdefault("DEBUG", "false")

from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest


# ── Also set via monkeypatch for test isolation ─────────────────────
@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject minimal environment variables for all tests.

    This provides per-test isolation on top of the module-level
    defaults set above.

    Args:
        monkeypatch: pytest monkeypatch fixture for setting env vars.
    """
    monkeypatch.setenv("SUPABASE_URL", "https://test-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key-placeholder")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-gemini-key-placeholder")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key-placeholder")
    monkeypatch.setenv("PRIMARY_MODEL", "gemini-1.5-pro")
    monkeypatch.setenv("SUB_AGENT_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("MAX_SQL_ROWS", "10")
    monkeypatch.setenv("PHOENIX_ENABLED", "false")
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("DEBUG", "false")


# ── Mock Supabase client fixture ─────────────────────────────────────
@pytest.fixture()
def mock_supabase_client() -> Generator[MagicMock, None, None]:
    """Provide a mocked Supabase client with chainable method support.

    Yields:
        A :class:`MagicMock` replacing the real Supabase client.
    """
    mock_client = MagicMock()
    with patch(
        "src.db.supabase_client.get_supabase_client",
        return_value=mock_client,
    ):
        yield mock_client


# ── Mock encoder fixture ─────────────────────────────────────────────
@pytest.fixture()
def mock_encoder() -> Generator[MagicMock, None, None]:
    """Provide a mocked embedding encoder that returns deterministic vectors.

    Yields:
        A :class:`MagicMock` replacing the encode function.
    """
    mock_fn = MagicMock(return_value=[[0.1] * 384])
    with patch("src.tools.rag_tools.encode", mock_fn):
        yield mock_fn


# ── Mock reranker fixture ────────────────────────────────────────────
@pytest.fixture()
def mock_reranker() -> Generator[MagicMock, None, None]:
    """Provide a mocked reranker that returns deterministic scores.

    Yields:
        A :class:`MagicMock` replacing the rerank function.
    """
    mock_fn = MagicMock(return_value=[(0, 0.95), (2, 0.82), (1, 0.71)])
    with patch("src.tools.rag_tools.rerank", mock_fn):
        yield mock_fn


# ── Sample vector search results ────────────────────────────────────
@pytest.fixture()
def sample_vector_results() -> list[dict[str, Any]]:
    """Return sample results from a pgvector RPC call.

    Returns:
        List of mock vector search result dictionaries.
    """
    return [
        {
            "id": 1,
            "text_content": "Package was damaged on arrival. Product broken inside.",
            "order_id": "550e8400-e29b-41d4-a716-446655440001",
            "similarity": 0.92,
        },
        {
            "id": 2,
            "text_content": "Great product quality but shipping took 2 weeks.",
            "order_id": "550e8400-e29b-41d4-a716-446655440002",
            "similarity": 0.85,
        },
        {
            "id": 3,
            "text_content": "Wrong item received. Filed for return immediately.",
            "order_id": "550e8400-e29b-41d4-a716-446655440003",
            "similarity": 0.80,
        },
    ]


# ── Sample SQL rows ─────────────────────────────────────────────────
@pytest.fixture()
def sample_sql_rows() -> list[dict[str, Any]]:
    """Return sample rows from a SQL query.

    Returns:
        List of mock SQL result row dictionaries.
    """
    return [
        {
            "campaign_id": "SUMMER_SALE",
            "campaign_name": "Summer Sale 2024",
            "channel": "instagram",
            "daily_spend": 150.00,
            "cac": 45.00,
        },
        {
            "campaign_id": "WINTER_PROMO",
            "campaign_name": "Winter Promo 2024",
            "channel": "google",
            "daily_spend": 200.00,
            "cac": 82.00,
        },
    ]
