"""Pydantic v2 input schemas for all five agent tools.

Each model is used as the ``args_schema`` parameter on its corresponding
LangChain ``@tool`` function, providing automatic validation and
documentation of expected inputs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OmnichannelSearchInput(BaseModel):
    """Input schema for the ``omnichannel_feedback_search`` tool.

    Attributes:
        query: Natural-language search query about customer feedback.
        filter_order_id: Optional UUID to restrict results to a specific order.
        top_k_retrieve: Number of candidates to retrieve from pgvector.
        top_k_rerank: Number of results to keep after cross-encoder reranking.
    """

    query: str = Field(
        ...,
        description="Natural-language search query about customer feedback, reviews, or support tickets.",
    )
    filter_order_id: str | None = Field(
        default=None,
        description="Optional UUID to filter results to a specific order.",
    )
    top_k_retrieve: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of candidates to retrieve from pgvector similarity search.",
    )
    top_k_rerank: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of results to keep after cross-encoder reranking.",
    )


class MarketingSearchInput(BaseModel):
    """Input schema for the ``marketing_content_search`` tool.

    Attributes:
        query: Natural-language search query about marketing content.
        filter_campaign_id: Optional campaign ID to restrict results.
        top_k_retrieve: Number of candidates to retrieve from pgvector.
        top_k_rerank: Number of results to keep after reranking.
    """

    query: str = Field(
        ...,
        description="Natural-language search query about campaign content, ad copy, or marketing materials.",
    )
    filter_campaign_id: str | None = Field(
        default=None,
        description="Optional campaign ID to filter results to a specific campaign.",
    )
    top_k_retrieve: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of candidates to retrieve from pgvector similarity search.",
    )
    top_k_rerank: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of results to keep after cross-encoder reranking.",
    )


class SQLQueryInput(BaseModel):
    """Input schema for the ``ecommerce_sql_query`` tool.

    Attributes:
        question: Natural-language question requiring structured data lookup.
        table_hint: Optional hint about which table(s) to query.
        filter_campaign_id: Optional campaign ID filter.
        filter_product_sku: Optional product SKU filter.
        date_from: Optional start date in YYYY-MM-DD format.
        date_to: Optional end date in YYYY-MM-DD format.
        max_rows: Maximum rows to return.
    """

    question: str = Field(
        ...,
        description="Natural-language question requiring a structured data lookup from the database.",
    )
    table_hint: str | None = Field(
        default=None,
        description="Optional hint about which table(s) to focus the query on.",
    )
    filter_campaign_id: str | None = Field(
        default=None,
        description="Optional campaign ID to filter results.",
    )
    filter_product_sku: str | None = Field(
        default=None,
        description="Optional product SKU to filter results.",
    )
    date_from: str | None = Field(
        default=None,
        description="Optional start date filter in YYYY-MM-DD format.",
    )
    date_to: str | None = Field(
        default=None,
        description="Optional end date filter in YYYY-MM-DD format.",
    )
    max_rows: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of rows to return.",
    )


class AnalyticsQueryInput(BaseModel):
    """Input schema for the ``ecommerce_analytics_query`` tool.

    Identical to :class:`SQLQueryInput` but with a higher default
    ``max_rows`` since aggregated results are typically smaller.

    Attributes:
        question: Natural-language question requiring aggregation or trend analysis.
        table_hint: Optional hint about which table(s) to query.
        filter_campaign_id: Optional campaign ID filter.
        filter_product_sku: Optional product SKU filter.
        date_from: Optional start date in YYYY-MM-DD format.
        date_to: Optional end date in YYYY-MM-DD format.
        max_rows: Maximum rows to return (default 20 for aggregations).
    """

    question: str = Field(
        ...,
        description="Natural-language question requiring aggregation, trend analysis, or cohort comparison.",
    )
    table_hint: str | None = Field(
        default=None,
        description="Optional hint about which table(s) to focus the query on.",
    )
    filter_campaign_id: str | None = Field(
        default=None,
        description="Optional campaign ID to filter results.",
    )
    filter_product_sku: str | None = Field(
        default=None,
        description="Optional product SKU to filter results.",
    )
    date_from: str | None = Field(
        default=None,
        description="Optional start date filter in YYYY-MM-DD format.",
    )
    date_to: str | None = Field(
        default=None,
        description="Optional end date filter in YYYY-MM-DD format.",
    )
    max_rows: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of rows to return (higher default for aggregations).",
    )


class TavilySearchInput(BaseModel):
    """Input schema for the ``web_market_search`` tool.

    Attributes:
        query: Natural-language question requiring current web data.
        search_depth: Tavily search depth — ``basic`` (fast) or ``advanced`` (thorough).
        max_results: Maximum number of web results to return.
    """

    query: str = Field(
        ...,
        description="Natural-language question requiring current market data, benchmarks, or competitor intelligence.",
    )
    search_depth: str = Field(
        default="advanced",
        description="Search depth: 'basic' for fast results or 'advanced' for thorough analysis.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of web search results to return.",
    )
