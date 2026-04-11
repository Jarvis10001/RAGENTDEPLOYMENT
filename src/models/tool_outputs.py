"""Pydantic v2 output models for tool results.

These models provide structured validation for tool outputs before they
are passed back to the agent for synthesis.  They are primarily used for
internal type safety and can be serialised to strings for the agent.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Base output model shared by all tools.

    Attributes:
        tool_name: Name of the tool that produced this result.
        success: Whether the tool executed successfully.
        result: The formatted result string.
        error: Error message if the tool failed.
    """

    tool_name: str = Field(
        ...,
        description="Name of the tool that produced this result.",
    )
    success: bool = Field(
        default=True,
        description="Whether the tool executed successfully.",
    )
    result: str = Field(
        default="",
        description="The formatted result string returned to the agent.",
    )
    error: str | None = Field(
        default=None,
        description="Error description if the tool failed.",
    )


class RAGToolResult(ToolResult):
    """Output model for RAG search tools (omnichannel and marketing).

    Attributes:
        query: The original search query.
        retrieved_count: Number of chunks retrieved from pgvector.
        reranked_count: Number of chunks after reranking.
        passages: List of top reranked text passages.
    """

    query: str = Field(
        default="",
        description="The original search query.",
    )
    retrieved_count: int = Field(
        default=0,
        description="Number of chunks retrieved from pgvector.",
    )
    reranked_count: int = Field(
        default=0,
        description="Number of chunks after reranking.",
    )
    passages: list[str] = Field(
        default_factory=list,
        description="List of top reranked text passages.",
    )


class SQLToolResult(ToolResult):
    """Output model for SQL tools (query and analytics).

    Attributes:
        question: The original analyst question.
        sql_executed: The SQL statement that was generated and executed.
        row_count: Number of rows returned by the query.
        rows: List of row dictionaries.
    """

    question: str = Field(
        default="",
        description="The original analyst question.",
    )
    sql_executed: str = Field(
        default="",
        description="The SQL statement that was generated and executed.",
    )
    row_count: int = Field(
        default=0,
        description="Number of rows returned by the query.",
    )
    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Raw row dictionaries from the query.",
    )


class WebSearchResult(ToolResult):
    """Output model for the web search tool.

    Attributes:
        original_query: The analyst's original question.
        search_query: The optimised search query sent to Tavily.
        results_count: Number of web results found.
        sources: List of source URLs from the search results.
    """

    original_query: str = Field(
        default="",
        description="The analyst's original question.",
    )
    search_query: str = Field(
        default="",
        description="The optimised search query sent to Tavily.",
    )
    results_count: int = Field(
        default=0,
        description="Number of web results found.",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="List of source URLs from the search results.",
    )
