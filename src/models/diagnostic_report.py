"""Pydantic model for the final synthesised diagnostic report.

Produced by the Synthesis Agent after merging SQL and RAG findings.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ActionItem(BaseModel):
    """A recommended action with owner and priority.

    Attributes:
        action: What should be done.
        owner: Suggested team or role responsible.
        priority: ``"immediate"`` | ``"short_term"`` | ``"long_term"``.
        expected_impact: Estimated business impact of taking this action.
    """

    action: str = Field(
        ...,
        description="Actionable recommendation.",
    )
    owner: str = Field(
        default="Operations",
        description="Team or role responsible.",
    )
    priority: str = Field(
        default="short_term",
        description="One of: immediate, short_term, long_term.",
    )
    expected_impact: str = Field(
        default="",
        description="Estimated business impact.",
    )


class DiagnosticReport(BaseModel):
    """Final synthesised report combining quantitative and qualitative evidence.

    Attributes:
        executive_summary: One-paragraph executive brief.
        confirmed_root_cause: The most likely root cause, backed by evidence.
        contributing_factors: Additional factors that compound the issue.
        revenue_impact_estimate: Estimated revenue effect (e.g. "$45k/month").
        urgency_score: 1 (low) – 10 (critical).
        confidence_score: 1 (speculative) – 10 (highly certain).
        action_items: Ordered list of recommended actions.
        data_gaps: Missing data or blind spots the analyst should address.
        supporting_sql_evidence: Key metrics referenced from SQL analysis.
        supporting_rag_evidence: Key quotes / themes from RAG analysis.
    """

    executive_summary: str = Field(
        ...,
        min_length=1,
        description="One-paragraph executive brief.",
    )
    confirmed_root_cause: str = Field(
        ...,
        min_length=1,
        description="Most likely root cause backed by evidence.",
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="Additional compounding factors.",
    )
    revenue_impact_estimate: str = Field(
        default="Unable to estimate",
        description="Estimated revenue effect.",
    )
    urgency_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Urgency: 1 (low) – 10 (critical).",
    )
    confidence_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Confidence: 1 (speculative) – 10 (certain).",
    )
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Ordered recommended actions.",
    )
    data_gaps: list[str] = Field(
        default_factory=list,
        description="Missing data or blind spots.",
    )
    supporting_sql_evidence: dict[str, object] = Field(
        default_factory=dict,
        description="Key SQL metrics cited in reasoning.",
    )
    supporting_rag_evidence: list[str] = Field(
        default_factory=list,
        description="Key quotes / themes from RAG.",
    )

    @field_validator("urgency_score", "confidence_score")
    @classmethod
    def _clamp_score(cls, value: int) -> int:
        """Clamp scores to the 1-10 range.

        Args:
            value: The raw integer score.

        Returns:
            The score clamped between 1 and 10.
        """
        return max(1, min(10, value))
