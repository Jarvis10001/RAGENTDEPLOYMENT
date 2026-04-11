"""Query Router Agent — classifies analyst intent and routes to the right agents.

This agent is the entry-point of the diagnostic crew.  It parses the
natural-language question into a :class:`QueryIntent` Pydantic model,
deciding which downstream agents (SQL, RAG, Synthesis) should be
activated.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from crewai import Agent, Task
from crewai import LLM

from src.config import get_settings
from src.models.query_intent import QueryIntent, QueryType

logger = logging.getLogger(__name__)


def build_query_router_agent() -> Agent:
    """Construct the Query Router Agent.

    Uses the fast 8B model — classification does not need the 70B model,
    and keeping this cheap preserves Groq rate-limit quota for the
    heavier reasoning agents downstream.

    Returns:
        A fully-configured :class:`crewai.Agent` for intent classification.
    """
    settings = get_settings()

    llm = LLM(
        model=settings.router_model_name,   # "groq/llama-3.1-8b-instant"
        temperature=0.0,                    # deterministic classification
        max_tokens=512,                     # intent JSON is small — cap aggressively
    )

    agent = Agent(
        role="Senior Analytics Query Classifier",
        goal=(
            "Parse the analyst's natural-language question into a structured "
            "QueryIntent.  Determine which downstream agents (SQL Analyst, "
            "RAG Retrieval, Synthesis) must run, extract any campaign_id, "
            "product_sku, date range, or focus metric, and classify the "
            "query type."
        ),
        backstory=(
            "You are an expert in e-commerce analytics who understands the "
            "data landscape across marketing campaigns, order fulfilment, "
            "customer lifecycle, and customer feedback.  Given any business "
            "question, you can instantly identify what kind of data is "
            "needed (structured metrics, unstructured feedback, or both) "
            "and extract key filter parameters."
        ),
        llm=llm,
        verbose=settings.debug,
        allow_delegation=False,
        max_iter=2,  # classification should not need retries
    )
    return agent


def build_query_router_task(agent: Agent, user_query: str) -> Task:
    """Build the routing task for the Query Router Agent.

    Args:
        agent: The Query Router Agent instance.
        user_query: The raw analyst question.

    Returns:
        A :class:`crewai.Task` whose expected output is a ``QueryIntent``
        JSON string.
    """
    description = f"""Analyse the following analyst question and produce a JSON object
with exactly these fields:

- original_query (str): the verbatim question
- needs_sql (bool): true if structured/quantitative data is needed
- needs_rag (bool): true if unstructured text search is needed
- needs_synthesis (bool): true if both SQL and RAG results should be merged
- query_type (str): one of {[qt.value for qt in QueryType]}
- campaign_id (str or null): extracted campaign identifier, if any
- product_sku (str or null): extracted product SKU, if any
- date_from (str or null): start date in ISO 8601, if any
- date_to (str or null): end date in ISO 8601, if any
- focus_metric (str or null): specific metric the analyst asks about
- reasoning (str): brief explanation of your routing decision

ROUTING RULES:
1. If the question asks about numbers, KPIs, trends, or comparisons → needs_sql = true
2. If the question asks about customer sentiment, feedback, reviews, or qualitative insights → needs_rag = true
3. If both SQL and RAG are needed, set needs_synthesis = true
4. If only one is needed, needs_synthesis = false
5. Always try to extract campaign_id, product_sku, and date ranges from the question

QUESTION: {user_query}

Respond ONLY with valid JSON, no markdown fences, no extra text."""

    task = Task(
        description=description,
        expected_output="A JSON object matching the QueryIntent schema. You MUST set at least one of needs_sql or needs_rag to true.",
        agent=agent,
        output_pydantic=QueryIntent,
    )
    return task


def parse_router_output(raw_output: Any) -> QueryIntent:
    """Parse the raw LLM output into a validated QueryIntent.

    Args:
        raw_output: The raw output from the router task.

    Returns:
        A validated :class:`QueryIntent` instance.

    Raises:
        ValueError: If the output cannot be parsed into a valid QueryIntent.
    """
    if hasattr(raw_output, "pydantic") and raw_output.pydantic:
        intent = raw_output.pydantic
        if not intent.needs_sql and not intent.needs_rag:
            logger.warning("Router selected neither SQL nor RAG. Defaulting to SQL.")
            intent.needs_sql = True
        return intent

    raw_str = str(raw_output)
    # Strip markdown fences if present
    cleaned: str = raw_str.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        data: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(
            "Router output is not valid JSON. Falling back to defaults. Output: %s",
            raw_str[:500],
        )
        return QueryIntent(
            original_query=raw_str,
            needs_sql=True,
            needs_rag=True,
            needs_synthesis=True,
            query_type=QueryType.GENERAL,
            reasoning="Failed to parse router output; activating all agents as fallback.",
        )

    # Map string query_type to enum
    qt_raw: str = data.get("query_type", "general")
    try:
        data["query_type"] = QueryType(qt_raw)
    except ValueError:
        data["query_type"] = QueryType.GENERAL

    intent = QueryIntent(**data)
    
    # Fallback: if everything is false, default to SQL
    if not intent.needs_sql and not intent.needs_rag:
        logger.warning("Router selected neither SQL nor RAG. Defaulting to SQL.")
        intent.needs_sql = True
        
    logger.info(
        "Parsed QueryIntent — sql=%s rag=%s synthesis=%s type=%s",
        intent.needs_sql,
        intent.needs_rag,
        intent.needs_synthesis,
        intent.query_type.value,
    )
    return intent
