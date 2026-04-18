"""Query intent classifier — deterministic pre-processing before the ReAct loop.

Classifies incoming user queries into structured intents to eliminate
non-deterministic tool selection and parameter interpretation. When a query
is ambiguous, generates a clarifying question instead of guessing.

Design decisions
----------------
* Uses the sub-agent model (Gemini Flash) at temperature=0.0 for cost
  efficiency and determinism.
* Classification is cached to avoid redundant LLM calls on retries.
* Moderate strictness: only asks for clarification when the query is
  genuinely ambiguous (e.g., "best campaigns" without a metric), not
  for minor specificity gaps.
"""

from __future__ import annotations

import logging
from typing import Final

from pydantic import BaseModel, Field

from src.config import settings
from src.cache import response_cache as cache
from src.llm import extract_text, get_sub_llm
from src.utils.retry import exponential_backoff

logger = logging.getLogger(__name__)


# ── Pydantic schema for structured classification output ─────────────

class QueryIntent(BaseModel):
    """Structured classification result for a user query.

    Attributes:
        intent_type: High-level category of the user's question.
        primary_metric: The main metric the user cares about, if identifiable.
        required_tools: Ordered list of tool names the agent should call.
        missing_params: Parameters that are too ambiguous to guess.
        clarifying_question: Question to ask the user, if ambiguous.
        rewritten_query: A precise, unambiguous version of the user query.
        confidence: How confident the classifier is (high/medium/low).
    """

    intent_type: str = Field(
        ...,
        description=(
            "One of: 'sql_lookup', 'sql_analytics', 'rag_feedback', "
            "'rag_marketing', 'web_search', 'multi_tool', 'clarification_needed'"
        ),
    )
    primary_metric: str | None = Field(
        default=None,
        description="The main metric: revenue, roi, clv, cac, margin, freight_cost, etc.",
    )
    required_tools: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered tool names: omnichannel_feedback_search, marketing_content_search, "
            "ecommerce_sql_query, ecommerce_analytics_query, web_market_search"
        ),
    )
    missing_params: list[str] = Field(
        default_factory=list,
        description="Parameters the user hasn't specified: date_range, campaign_id, metric, product_sku, scope",
    )
    clarifying_question: str | None = Field(
        default=None,
        description="The clarifying question to ask the user, or null if the query is clear.",
    )
    rewritten_query: str = Field(
        ...,
        description="A precise, unambiguous version of the user's query.",
    )
    confidence: str = Field(
        default="high",
        description="Confidence level: high, medium, or low.",
    )


# ── Schema doc (mirrors sql_tools._SCHEMA_DOC for consistency) ───────

_SCHEMA_FOR_CLASSIFIER: Final[str] = """Database tables:
  customers(customer_id, clv, acquisition_date, status, status_updated_at)
  marketing_campaigns(campaign_id, campaign_name, channel, daily_spend, impressions, clicks, cac)
  campaign_products(campaign_id, product_sku)
  orders(order_id, customer_id, campaign_id, dynamic_price_paid, is_split_shipment, net_profit_margin, order_date)
  shipments(shipment_id, order_id, product_sku, warehouse_shipped_from, freight_cost, dispatch_date, delivery_status)
  events_log(event_id, customer_id, campaign_id, event_type, event_timestamp)
  omnichannel_vectors(feedback text — customer reviews, support tickets, complaints)
  marketing_vectors(campaign ad copy, briefs, promotional materials)"""


# ── Classification prompt ─────────────────────────────────────────────

_CLASSIFIER_PROMPT: Final[str] = """You are a query intent classifier for an e-commerce intelligence system. Classify the user's question into a structured JSON response.

{schema}

Available tools (use exact names):
- ecommerce_sql_query: Row-level lookups — individual orders, customer records, campaign spend
- ecommerce_analytics_query: Aggregations, trends, cohort comparisons, rankings, time-series
- omnichannel_feedback_search: Customer sentiment, complaints, reviews, support tickets (vector search)
- marketing_content_search: Campaign ad copy, messaging, brand positioning (vector search)
- web_market_search: Industry benchmarks, competitor data, current market conditions (web search)

CLASSIFICATION RULES:
1. If the user asks for "best", "top", or "most successful" without specifying a metric (revenue, ROI, clicks, CLV, margin), set intent_type to "clarification_needed" and ask which metric they want to rank by.
2. If the user asks about profit/margin/revenue changes without a time period, accept general time references like "last month" or "recently" — only ask for clarification if NO time context exists at all AND the question requires time comparison.
3. If the user says "customer feedback" or "what are customers saying" without any product/campaign/topic context, accept it as-is — only ask if the scope is critical for an actionable answer.
4. For root-cause questions ("why did X happen?"), always include BOTH an SQL tool AND omnichannel_feedback_search.
5. For questions about campaign messaging alignment, include BOTH marketing_content_search AND omnichannel_feedback_search.
6. For questions about industry benchmarks or competitors, use web_market_search.
7. Always produce a rewritten_query that is precise and unambiguous — fill in reasonable defaults when possible.

CONFIDENCE LEVELS:
- "high": Query is clear, tools and metrics are obvious
- "medium": Query is reasonable but could have multiple interpretations — proceed with best guess
- "low": Query is too ambiguous to provide a reliable answer — ask for clarification

MODERATE STRICTNESS: Only set intent_type to "clarification_needed" when the ambiguity would lead to materially different answers. When in doubt, proceed with the most common interpretation and note it in rewritten_query.

Return ONLY valid JSON matching this schema (no markdown fences, no extra text):
{{
  "intent_type": "...",
  "primary_metric": "..." or null,
  "required_tools": ["tool1", "tool2"],
  "missing_params": ["param1"] or [],
  "clarifying_question": "..." or null,
  "rewritten_query": "...",
  "confidence": "high" | "medium" | "low"
}}

User question: {question}

{context}"""


@exponential_backoff(max_retries=2, base_delay_seconds=1.0)
def classify_query(
    question: str,
    chat_context: str = "",
) -> QueryIntent:
    """Classify a user query into a structured intent.

    Args:
        question: The raw user question.
        chat_context: Optional recent chat history for context.

    Returns:
        A :class:`QueryIntent` with classification results.
    """
    logger.info("Classifying query: %r", question[:80])

    # Check cache first
    cache_key = cache.make_key("classifier", question, chat_context[:200])
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("Cache hit for query classification.")
        try:
            return QueryIntent.model_validate_json(cached)
        except Exception:
            pass  # Cache corruption — re-classify

    context_section = f"Recent conversation context:\n{chat_context}" if chat_context else ""

    prompt = _CLASSIFIER_PROMPT.format(
        schema=_SCHEMA_FOR_CLASSIFIER,
        question=question,
        context=context_section,
    )

    response = get_sub_llm().invoke(prompt)
    raw_output: str = extract_text(response.content).strip()

    # Strip markdown fences if present
    if raw_output.startswith("```"):
        lines = [ln for ln in raw_output.splitlines() if not ln.strip().startswith("```")]
        raw_output = "\n".join(lines).strip()

    try:
        intent = QueryIntent.model_validate_json(raw_output)
    except Exception as exc:
        logger.warning(
            "Failed to parse classifier output as JSON (%s). Falling through with defaults. Raw: %s",
            exc,
            raw_output[:300],
        )
        # Fallback: proceed without classification — let the ReAct agent handle it
        intent = QueryIntent(
            intent_type="multi_tool",
            primary_metric=None,
            required_tools=[],
            missing_params=[],
            clarifying_question=None,
            rewritten_query=question,
            confidence="low",
        )

    # Cache the result
    try:
        cache.set(cache_key, intent.model_dump_json(), ttl=settings.cache_ttl_seconds)
    except Exception:
        pass  # Non-fatal

    logger.info(
        "Classification result — type=%s confidence=%s tools=%s clarify=%s",
        intent.intent_type,
        intent.confidence,
        intent.required_tools,
        intent.clarifying_question is not None,
    )

    return intent


def needs_clarification(intent: QueryIntent) -> bool:
    """Check whether the classified intent requires user clarification.

    Args:
        intent: The classification result.

    Returns:
        ``True`` if the agent should ask the user a clarifying question
        before proceeding.
    """
    return (
        intent.intent_type == "clarification_needed"
        and intent.clarifying_question is not None
    )


def build_enhanced_input(
    original_question: str,
    intent: QueryIntent,
) -> str:
    """Build an enhanced prompt for the ReAct agent using classified intent.

    Injects the classification result as structured guidance into the agent's
    input, so the ReAct loop follows a deterministic tool-calling order.

    Args:
        original_question: The user's original question.
        intent: The classified intent.

    Returns:
        An enhanced query string with embedded tool guidance.
    """
    parts: list[str] = []

    # Use the rewritten query as the primary question
    parts.append(f"QUESTION: {intent.rewritten_query}")

    # Add tool guidance
    if intent.required_tools:
        tool_list = ", ".join(intent.required_tools)
        parts.append(f"\nTOOL GUIDANCE: Call these tools in this order: {tool_list}")

    # Add metric guidance
    if intent.primary_metric:
        parts.append(f"PRIMARY METRIC: Focus on {intent.primary_metric}")

    # Add original question for reference
    if intent.rewritten_query != original_question:
        parts.append(f"\n(Original user question for reference: {original_question})")

    return "\n".join(parts)
