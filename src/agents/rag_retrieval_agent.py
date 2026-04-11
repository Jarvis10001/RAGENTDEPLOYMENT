"""RAG Retrieval Agent — retrieves and reranks qualitative text evidence.

This agent searches ``omnichannel_vectors`` (customer feedback, reviews,
support tickets) and ``marketing_vectors`` (ad copy, campaign briefs)
via pgvector cosine similarity, then reranks results with a cross-encoder
to surface the most relevant qualitative evidence.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from crewai import Agent, Task
from crewai import LLM

from src.config import get_settings
from src.models.query_intent import QueryIntent
from src.models.rag_result import RAGResult
from src.tools.reranker_tool import RerankerTool
from src.tools.vector_search_tool import VectorSearchTool

logger = logging.getLogger(__name__)


def build_rag_retrieval_agent() -> Agent:
    """Construct the RAG Retrieval Agent.

    Returns:
        A fully-configured :class:`crewai.Agent` for qualitative evidence
        retrieval and reranking.
    """
    settings = get_settings()

    llm = LLM(
        model=settings.rag_model_name,   # "groq/llama-3.1-70b-versatile"
        temperature=0.0,
        max_tokens=1024,
    )

    vector_tool = VectorSearchTool()
    reranker_tool = RerankerTool()

    agent = Agent(
        role="Customer Intelligence Analyst",
        goal=(
            "Retrieve semantically relevant text chunks from customer "
            "feedback, support tickets, reviews, and marketing copy using "
            "pgvector cosine similarity.  Rerank results with a cross-encoder "
            "for precision.  Synthesise findings into themes, representative "
            "quotes, sentiment scores, and urgency signals."
        ),
        backstory=(
            "You are an expert in qualitative research and natural language "
            "analysis.  You can sift through thousands of customer voices "
            "to identify patterns, concerns, and opportunities.  You "
            "understand marketing copy and can assess whether campaign "
            "messaging aligns with customer expectations."
        ),
        llm=llm,
        tools=[vector_tool, reranker_tool],
        verbose=settings.debug,
        allow_delegation=False,
    )
    return agent


def build_rag_retrieval_task(
    agent: Agent,
    intent: QueryIntent,
    user_query: str,
) -> Task:
    """Build the RAG retrieval task.

    Args:
        agent: The RAG Retrieval Agent.
        intent: Parsed query intent from the router.
        user_query: The original analyst question.

    Returns:
        A :class:`crewai.Task` whose output is a ``RAGResult`` JSON.
    """
    filter_instructions: str = _build_rag_filter_instructions(intent)

    description = f"""You are investigating qualitative evidence for the following question:

QUESTION: {user_query}

INSTRUCTIONS:
1. Use the vector_similarity_search tool to search for relevant text.
   - Search the "omnichannel" table for customer feedback, reviews, and support tickets.
   - Search the "marketing" table for ad copy and campaign briefs if relevant.
   {filter_instructions}

2. After retrieving candidates, use the rerank_documents tool to rerank them
   against the original question for better precision.

3. Analyse the reranked results and produce a JSON response with EXACTLY these fields:
   - top_themes (list of str): the dominant themes you identified
   - representative_quotes (list of str, max 5): verbatim quotes that best illustrate the findings
   - source_breakdown (dict): mapping of source type to count (e.g. {{"reviews": 3, "support_tickets": 2}})
   - sentiment_scores (dict): mapping of sentiment label to score 0-1 (e.g. {{"positive": 0.2, "negative": 0.7, "neutral": 0.1}})
   - urgency_signals (list of str): any phrases indicating time-sensitive issues
   - full_narrative (str): a coherent narrative synthesising all evidence (3-4 sentences max)

Respond with ONLY valid JSON, no markdown fences."""

    task = Task(
        description=description,
        expected_output="A JSON object matching the RAGResult schema.",
        agent=agent,
        output_pydantic=RAGResult,
    )
    return task


def parse_rag_retrieval_output(raw_output: Any) -> RAGResult:
    """Parse the raw LLM output into a validated RAGResult.

    Args:
        raw_output: The raw output from the RAG retrieval task.

    Returns:
        A validated :class:`RAGResult` instance.

    Raises:
        ValueError: If parsing fails irrecoverably.
    """
    if hasattr(raw_output, "pydantic") and raw_output.pydantic:
        return raw_output.pydantic

    raw_str = str(raw_output)
    cleaned: str = _strip_markdown_fences(raw_str)

    try:
        data: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(
            "RAG output is not valid JSON. Using raw text as narrative."
        )
        return RAGResult(
            full_narrative=raw_str[:3000],
            top_themes=["Unable to parse structured themes"],
        )

    # Enforce max 5 quotes
    if "representative_quotes" in data and isinstance(
        data["representative_quotes"], list
    ):
        data["representative_quotes"] = data["representative_quotes"][:5]

    result = RAGResult(**data)
    logger.info(
        "Parsed RAGResult — themes=%d quotes=%d narrative_len=%d",
        len(result.top_themes),
        len(result.representative_quotes),
        len(result.full_narrative),
    )
    return result


def _build_rag_filter_instructions(intent: QueryIntent) -> str:
    """Build RAG-specific filter instructions from the QueryIntent.

    Args:
        intent: The parsed query intent.

    Returns:
        Formatted filter instructions for the agent prompt.
    """
    parts: list[str] = []
    if intent.campaign_id:
        parts.append(
            f'- Pass filter_campaign_id="{intent.campaign_id}" when searching marketing vectors.'
        )
    if intent.product_sku:
        parts.append(
            f"- The question is about product SKU {intent.product_sku} — "
            f"include it in your search query text."
        )
    # Order ID filtering would typically come from SQL results context
    if not parts:
        parts.append("- No specific metadata filters extracted; search broadly.")
    return "\n   ".join(parts)


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from a string.

    Args:
        text: Raw text potentially wrapped in code fences.

    Returns:
        Cleaned text without fences.
    """
    cleaned: str = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return cleaned.strip()
