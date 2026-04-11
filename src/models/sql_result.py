"""Pydantic model for structured SQL analysis results.

Returned by the SQL Analyst Agent after running parameterised queries
against the Supabase structured tables.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Impact severity of the finding."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SQLAnalysisResult(BaseModel):
    """Structured output from the SQL Analyst Agent.

    Keeping raw_rows bounded to 5 prevents token overflow when this
    object is serialised into the Synthesis Agent's context.

    Attributes:
        sql_executed: Description of the parameterised queries that were run.
        key_metrics: Dictionary of metric-name → value pairs (max 8 entries).
        affected_segment: Human-readable description of the affected segment.
        severity: How severe the finding is for the business.
        raw_rows: Up to 5 representative data rows for evidence.
        analysis_summary: 2-3 sentence plain-English summary of findings.
        query_type: The type of query that produced this result.
    """

    sql_executed: str = Field(
        ...,
        description="Description of the parameterised SQL queries that were run.",
    )
    key_metrics: dict[str, object] = Field(
        default_factory=dict,
        description="Key numeric findings as a flat key-value dict. Max 8 entries.",
    )
    affected_segment: str = Field(
        default="",
        description="The specific customer/product/campaign segment most impacted.",
    )
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="Severity classification based on business impact.",
    )
    raw_rows: list[dict[str, object]] = Field(
        default_factory=list,
        max_length=5,
        description="Up to 5 representative result rows for evidence. NOT the full result set.",
    )
    analysis_summary: str = Field(
        default="",
        description=(
            "2-3 sentence plain-English summary of the findings. "
            "Do NOT repeat raw numbers already in key_metrics."
        ),
    )
    query_type: Optional[str] = Field(
        default=None,
        description="Classification label echoed from QueryIntent.",
    )
