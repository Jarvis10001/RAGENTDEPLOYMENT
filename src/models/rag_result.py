"""Pydantic model for qualitative RAG retrieval results.

Returned by the RAG Retrieval Agent after vector search + cross-encoder
reranking against ``omnichannel_vectors`` and ``marketing_vectors``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RAGResult(BaseModel):
    """Output of the RAG Retrieval Agent.

    Attributes:
        top_themes: Dominant themes extracted from retrieved text chunks.
        representative_quotes: Up to 5 verbatim quotes that best
            illustrate customer sentiment or marketing copy issues.
        source_breakdown: Mapping of source type (e.g. "reviews",
            "support_tickets", "ad_copy") to count of relevant chunks.
        sentiment_scores: Mapping of sentiment label (e.g. "positive",
            "negative", "neutral") to normalised score (0-1).
        urgency_signals: Phrases or patterns that indicate time-sensitive
            issues (e.g. "chargeback threat", "viral complaint").
        full_narrative: A coherent narrative synthesising all retrieved
            evidence into a qualitative assessment.
    """

    top_themes: list[str] = Field(
        default_factory=list,
        description="Dominant themes from retrieved chunks.",
    )
    representative_quotes: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Up to 5 verbatim quotes.",
    )
    source_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Source type → chunk count.",
    )
    sentiment_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Sentiment label → normalised score.",
    )
    urgency_signals: list[str] = Field(
        default_factory=list,
        description="Time-sensitive issue indicators.",
    )
    full_narrative: str = Field(
        default="",
        description="Coherent qualitative narrative.",
    )
