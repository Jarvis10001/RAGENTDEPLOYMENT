"""Pydantic model for the parsed query intent produced by the Query Router Agent.

The ``QueryIntent`` captures *what* the analyst is asking about and *which*
downstream agents must be activated.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """High-level category of the analyst's question."""

    CAMPAIGN_PERFORMANCE = "campaign_performance"
    PROFITABILITY = "profitability"
    CUSTOMER_SENTIMENT = "customer_sentiment"
    LOGISTICS = "logistics"
    CUSTOMER_LIFECYCLE = "customer_lifecycle"
    TREND_ANALYSIS = "trend_analysis"
    GENERAL = "general"


class QueryIntent(BaseModel):
    """Structured representation of a parsed analyst question.

    Attributes:
        original_query: The raw natural-language question.
        needs_sql: Whether the SQL Analyst Agent should run.
        needs_rag: Whether the RAG Retrieval Agent should run.
        needs_synthesis: Whether the Synthesis Agent should run.
        query_type: Classified category of the question.
        campaign_id: Optional campaign filter extracted from the question.
        product_sku: Optional product SKU filter extracted from the question.
        date_from: Optional start-date filter (ISO 8601 string).
        date_to: Optional end-date filter (ISO 8601 string).
        focus_metric: Optional metric the analyst specifically asked about.
        reasoning: Brief explanation of *why* the router chose this routing.
    """

    original_query: str = Field(
        ...,
        min_length=1,
        description="The raw natural-language question from the analyst.",
    )
    needs_sql: bool = Field(
        default=False,
        description="True if structured / quantitative data is needed.",
    )
    needs_rag: bool = Field(
        default=False,
        description="True if unstructured text retrieval is needed.",
    )
    needs_synthesis: bool = Field(
        default=False,
        description="True if SQL + RAG findings must be merged.",
    )
    query_type: QueryType = Field(
        default=QueryType.GENERAL,
        description="High-level question category.",
    )
    campaign_id: Optional[str] = Field(
        default=None,
        description="Campaign ID extracted from the question.",
    )
    product_sku: Optional[str] = Field(
        default=None,
        description="Product SKU extracted from the question.",
    )
    date_from: Optional[str] = Field(
        default=None,
        description="Start-date filter (ISO 8601).",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="End-date filter (ISO 8601).",
    )
    focus_metric: Optional[str] = Field(
        default=None,
        description="Specific metric the analyst is asking about (e.g. 'net_profit_margin').",
    )
    reasoning: str = Field(
        default="",
        description="Router's rationale for the chosen routing.",
    )
