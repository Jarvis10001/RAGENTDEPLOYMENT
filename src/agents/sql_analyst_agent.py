"""SQL Analyst Agent — generates and executes parameterised queries.

This agent answers quantitative questions about campaign ROI, split
shipment rates, profit margins, customer CLV cohorts, and acquisition
cost efficiency by querying the Supabase structured tables.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from crewai import Agent, Task
from crewai import LLM

from src.config import get_settings
from src.models.query_intent import QueryIntent
from src.models.sql_result import SQLAnalysisResult, Severity
from src.tools.supabase_sql_tool import SupabaseSQLTool

logger = logging.getLogger(__name__)


def build_sql_analyst_agent() -> Agent:
    """Construct the SQL Analyst Agent.

    Returns:
        A fully-configured :class:`crewai.Agent` for structured data analysis.
    """
    settings = get_settings()

    llm = LLM(
        model=settings.analyst_model_name,   # "groq/llama-3.1-70b-versatile"
        temperature=0.0,
        max_tokens=1024,
    )

    sql_tool = SupabaseSQLTool()

    agent = Agent(
        role="Senior E-commerce Data Analyst",
        goal=(
            "Generate and execute parameterised queries against Supabase "
            "structured tables to answer quantitative business questions. "
            "Analyse campaign ROI, split shipment rates, profit margin "
            "trends, customer CLV cohorts, and acquisition cost efficiency. "
            "Always return a structured SQLAnalysisResult."
        ),
        backstory=(
            "You are a seasoned data analyst with deep expertise in "
            "e-commerce metrics.  You know the database schema inside-out: "
            "customers, orders, shipments, marketing_campaigns, "
            "campaign_products, and events_log.  You write precise, "
            "parameterised queries and interpret the numbers to surface "
            "actionable business insights."
        ),
        llm=llm,
        tools=[sql_tool],
        verbose=settings.debug,
        allow_delegation=False,
    )
    return agent


def build_sql_analyst_task(
    agent: Agent,
    intent: QueryIntent,
    user_query: str,
) -> Task:
    """Build the SQL analysis task.

    Args:
        agent: The SQL Analyst Agent.
        intent: Parsed query intent from the router.
        user_query: The original analyst question.

    Returns:
        A :class:`crewai.Task` whose output is a ``SQLAnalysisResult`` JSON.
    """
    settings = get_settings()
    filters_context: str = _build_filters_context(intent)

    description = f"""You are analysing the following business question:

QUESTION: {user_query}

AVAILABLE TABLES (Supabase PostgREST — NO raw SQL, NO aggregate functions like COUNT/SUM/AVG in select):
- customers (customer_id UUID, clv NUMERIC, acquisition_date DATE, status TEXT, status_updated_at TIMESTAMP)
- marketing_campaigns (campaign_id TEXT, campaign_name TEXT, channel TEXT, daily_spend NUMERIC, impressions INTEGER, clicks INTEGER, cac NUMERIC)
- campaign_products (campaign_id TEXT, product_sku TEXT)
- orders (order_id UUID, customer_id UUID, campaign_id TEXT, dynamic_price_paid NUMERIC, is_split_shipment INTEGER, net_profit_margin NUMERIC, order_date TIMESTAMP)
- shipments (shipment_id UUID, order_id UUID, product_sku TEXT, warehouse_shipped_from TEXT, freight_cost NUMERIC, dispatch_date TIMESTAMP, delivery_status TEXT)
- events_log (event_id UUID, customer_id UUID, campaign_id TEXT, event_type TEXT, event_timestamp TIMESTAMP)

IMPORTANT: The supabase_sql_query tool uses Supabase PostgREST API. It does NOT support SQL aggregate functions (COUNT, SUM, AVG, GROUP BY) in the select field. You must:
- Select raw columns only (e.g. "campaign_id, daily_spend, cac")
- Use filters with operators: eq, gt, lt, gte, lte, neq, like, ilike, in
- Compute aggregations yourself from the returned rows

{filters_context}

INSTRUCTIONS:
1. Use the supabase_sql_query tool to query the relevant tables.
2. You may make MULTIPLE tool calls to gather data from different tables.
3. Retrieve a maximum of {settings.max_sql_rows} rows per query.
4. After gathering data, produce a JSON response with EXACTLY these fields:
   - sql_executed (str): description of the queries you ran
   - key_metrics (dict): metric name → value pairs (max 8 entries)
   - affected_segment (str): which customer/product/campaign segment is affected
   - severity (str): one of "low", "medium", "high", "critical"
   - raw_rows (list of dicts): AT MOST 5 representative rows
   - analysis_summary (str): 2-3 sentences MAX. Be concise.
   - query_type (str): "{intent.query_type.value}"

Respond with ONLY valid JSON, no markdown fences."""

    task = Task(
        description=description,
        expected_output=(
            "A single valid JSON object conforming to SQLAnalysisResult. "
            "No markdown fences, no preamble, no explanation — raw JSON only. "
            "The raw_rows array has at most 5 items. "
            "The analysis_summary is at most 3 sentences."
        ),
        agent=agent,
        output_pydantic=SQLAnalysisResult,
    )
    return task


def parse_sql_analyst_output(raw_output: Any) -> SQLAnalysisResult:
    """Parse the raw LLM output into a validated SQLAnalysisResult.

    Args:
        raw_output: The raw output from the SQL analyst task.

    Returns:
        A validated :class:`SQLAnalysisResult` instance.

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
            "SQL analyst output is not valid JSON. Using raw text as summary."
        )
        return SQLAnalysisResult(
            sql_executed="Unable to parse — see analysis_summary.",
            analysis_summary=raw_str[:2000],
            severity=Severity.MEDIUM,
        )

    # Normalise severity
    sev_raw: str = data.get("severity", "medium").lower()
    try:
        data["severity"] = Severity(sev_raw)
    except ValueError:
        data["severity"] = Severity.MEDIUM

    # Truncate raw_rows to 5
    if "raw_rows" in data and isinstance(data["raw_rows"], list):
        data["raw_rows"] = data["raw_rows"][:5]

    result = SQLAnalysisResult(**data)
    logger.info(
        "Parsed SQLAnalysisResult — severity=%s metrics_count=%d rows=%d",
        result.severity.value,
        len(result.key_metrics),
        len(result.raw_rows),
    )
    return result


def _build_filters_context(intent: QueryIntent) -> str:
    """Build a contextual filter string from the QueryIntent.

    Args:
        intent: The parsed query intent.

    Returns:
        A formatted string describing active filters.
    """
    parts: list[str] = []
    if intent.campaign_id:
        parts.append(f"Filter by campaign_id = '{intent.campaign_id}'")
    if intent.product_sku:
        parts.append(f"Filter by product_sku = '{intent.product_sku}'")
    if intent.date_from:
        parts.append(f"Filter dates from {intent.date_from}")
    if intent.date_to:
        parts.append(f"Filter dates to {intent.date_to}")
    if intent.focus_metric:
        parts.append(f"Focus metric: {intent.focus_metric}")

    if parts:
        return "EXTRACTED FILTERS:\n" + "\n".join(f"- {p}" for p in parts)
    return "No specific filters extracted from the question."


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
