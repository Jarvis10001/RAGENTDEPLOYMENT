"""SQL tools — LLM-generated SQL queries against the Supabase structured database.

Tool 3: ``ecommerce_sql_query``
    Row-level lookups for individual orders, customer records, campaign spend, etc.

Tool 4: ``ecommerce_analytics_query``
    Aggregations, cohort comparisons, trend analysis, and multi-table JOINs.

Both tools follow the same pipeline: cache check → Gemini Flash generates SQL →
security validation → execute via Supabase → compress rows → format → cache write.

Security guarantees
-------------------
* Only SELECT statements are executed (enforced pre-execution).
* A frozen allow-list blocks all DML / DDL keywords via word-boundary match.
* Queries run via ``execute_readonly_sql`` RPC which has a read-only Postgres role.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

from langchain_classic.tools import tool

from src.cache import response_cache as cache
from src.config import settings
from src.db.supabase_client import get_supabase_client
from src.llm import extract_text, get_sub_llm
from src.models.tool_inputs import AnalyticsQueryInput, SQLQueryInput
from src.utils.retry import exponential_backoff
from src.utils.token_budget import compress_sql_rows

logger = logging.getLogger(__name__)

# ── SQL safety — forbidden keyword patterns (word-boundary anchored) ──
_FORBIDDEN_PATTERN: re.Pattern[str] = re.compile(
    r"\b("
    + "|".join(
        [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "TRUNCATE",
            "CREATE",
            "ALTER",
            "GRANT",
            "REVOKE",
            "EXECUTE",
            "COPY",
        ]
    )
    + r")\b",
    re.IGNORECASE,
)

# ── Input validation patterns ─────────────────────────────────────────
_SAFE_ID_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_\-]+$")
_SAFE_DATE_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ── Schema documentation shared by both tools ─────────────────────────
_SCHEMA_DOC = """Available tables (PostgreSQL / Supabase):

  customers(customer_id uuid PK, clv numeric, acquisition_date date,
            status text, status_updated_at timestamp)

  marketing_campaigns(campaign_id text PK, campaign_name text,
                      channel text, daily_spend numeric,
                      impressions int, clicks int, cac numeric)

  campaign_products(campaign_id text FK, product_sku text)

  orders(order_id uuid PK, customer_id uuid FK, campaign_id text FK,
         dynamic_price_paid numeric, is_split_shipment int,
         net_profit_margin numeric, order_date timestamp)

  shipments(shipment_id uuid PK, order_id uuid FK, product_sku text,
            warehouse_shipped_from text, freight_cost numeric,
            dispatch_date timestamp, delivery_status text)

  events_log(event_id uuid PK, customer_id uuid FK, campaign_id text FK,
             event_type text, event_timestamp timestamp)"""

_ANALYTICS_GUIDANCE = """
Additional guidance for analytical queries:
- Use GROUP BY, DATE_TRUNC, WINDOW functions (LAG, LEAD, ROW_NUMBER), and HAVING freely.
- Use multi-table JOINs for cross-dimensional analysis.
- Prefer DATE_TRUNC('month', col) or DATE_TRUNC('week', col) for trend analysis.
- Use ROUND(value, 2) for readable numeric output.
- Use CTEs (WITH clauses) for complex multi-step analyses.

DETERMINISTIC DEFAULTS (follow these exactly to ensure consistent output):
- **CRITICAL**: If the user asks for the "best", "top", or "most successful" campaigns/products without specifying a metric, ALWAYS calculate and return BOTH `total_revenue` (SUM of dynamic_price_paid) and `roi` (Total Revenue / Total Spend). Order the results by `total_revenue` DESC by default to provide a consistent baseline.
- Always alias computed columns with EXACTLY these names: total_revenue, total_spend, roi, avg_margin, order_count, avg_clv, total_freight.
- When no date range is specified, include ALL available data — do NOT filter by date.
- Always use COALESCE(value, 0) for SUM aggregations to handle NULLs consistently.
- For campaign rankings, always JOIN marketing_campaigns with orders on campaign_id.
- When comparing periods, always use the SAME date granularity (month, week, etc.) consistently."""


# ═══════════════════════════════════════════════════════════════════════
# TOOL 3: ecommerce_sql_query
# ═══════════════════════════════════════════════════════════════════════


@tool("ecommerce_sql_query", args_schema=SQLQueryInput)
def ecommerce_sql_query(
    question: str,
    table_hint: str | None = None,
    filter_campaign_id: str | None = None,
    filter_product_sku: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    max_rows: int = 10,
) -> str:
    """Query the Supabase structured e-commerce database for quantitative
    data. Use this for questions about individual orders, revenue,
    profit margins, customer acquisition costs, split shipment counts,
    campaign spend, customer lifetime value, and any other numerical
    or transactional lookup. Generates and executes safe read-only
    SQL automatically. The query may include JOINs across tables.

    Args:
        question: Natural-language question requiring structured data.
        table_hint: Optional hint about which table(s) to query.
        filter_campaign_id: Optional campaign ID filter.
        filter_product_sku: Optional product SKU filter.
        date_from: Optional start date in YYYY-MM-DD format.
        date_to: Optional end date in YYYY-MM-DD format.
        max_rows: Maximum rows to return (default 10).

    Returns:
        Formatted string with the SQL query executed and compressed result
        table, or an error message if the query fails.
    """
    logger.info("ecommerce_sql_query called — question=%r", question[:80])
    try:
        # Step 1: Check cache
        cache_key = cache.make_key(
            "sql",
            question,
            table_hint,
            filter_campaign_id,
            filter_product_sku,
            date_from,
            date_to,
            max_rows,
        )
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit for SQL query.")
            return cached

        # Step 2: Generate SQL with Gemini Flash sub-LLM
        sql_query = _generate_sql(
            question=question,
            table_hint=table_hint,
            max_rows=max_rows,
            filter_campaign_id=filter_campaign_id,
            filter_product_sku=filter_product_sku,
            date_from=date_from,
            date_to=date_to,
            analytics_mode=False,
        )

        # Step 3: Security validation — reject DML/DDL
        _validate_sql(sql_query)

        # Step 4: Execute via read-only Supabase RPC
        rows = _execute_sql(sql_query)

        # Step 5: Compress to stay within agent token budget
        compressed = compress_sql_rows(rows, max_rows=5)

        # Step 6: Format for the agent
        output = _format_sql_output(
            question=question,
            sql_query=sql_query,
            row_count=len(rows),
            compressed_table=compressed,
        )

        # Step 7: Cache the result
        cache.set(cache_key, output, ttl=settings.cache_ttl_seconds)

        return output

    except Exception as e:
        logger.error("ecommerce_sql_query failed: %s: %s", type(e).__name__, e)
        error_msg = f"ecommerce_sql_query failed: {type(e).__name__}: {e}"
        try:
            if 'sql_query' in locals() and sql_query:
                error_msg += f"\nGenerated SQL that caused error:\n{sql_query}\n(Tip: Instruct the sub-agent to fix this specific syntax error by including it in your question.)"
        except Exception:
            pass
        return error_msg


# ═══════════════════════════════════════════════════════════════════════
# TOOL 4: ecommerce_analytics_query
# ═══════════════════════════════════════════════════════════════════════


@tool("ecommerce_analytics_query", args_schema=AnalyticsQueryInput)
def ecommerce_analytics_query(
    question: str,
    table_hint: str | None = None,
    filter_campaign_id: str | None = None,
    filter_product_sku: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    max_rows: int = 20,
) -> str:
    """Run aggregation and analytical queries against the Supabase
    e-commerce database. Use this specifically for trend analysis,
    cohort comparisons, campaign performance rankings, week-over-week
    metrics, channel attribution breakdowns, warehouse comparisons,
    and any question requiring grouped or time-series data. Use this
    alongside ecommerce_sql_query for complex multi-angle analysis.

    Args:
        question: Natural-language question requiring aggregation or trend analysis.
        table_hint: Optional hint about which table(s) to query.
        filter_campaign_id: Optional campaign ID filter.
        filter_product_sku: Optional product SKU filter.
        date_from: Optional start date in YYYY-MM-DD format.
        date_to: Optional end date in YYYY-MM-DD format.
        max_rows: Maximum rows to return (default 20 for aggregations).

    Returns:
        Formatted string with the SQL query, compressed result table, and
        optional trend note, or an error message if the query fails.
    """
    logger.info("ecommerce_analytics_query called — question=%r", question[:80])
    try:
        # Step 1: Check cache
        cache_key = cache.make_key(
            "analytics",
            question,
            table_hint,
            filter_campaign_id,
            filter_product_sku,
            date_from,
            date_to,
            max_rows,
        )
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit for analytics query.")
            return cached

        # Step 2: Generate SQL with analytics-focused prompt
        sql_query = _generate_sql(
            question=question,
            table_hint=table_hint,
            max_rows=max_rows,
            filter_campaign_id=filter_campaign_id,
            filter_product_sku=filter_product_sku,
            date_from=date_from,
            date_to=date_to,
            analytics_mode=True,
        )

        # Step 3: Security validation — reject DML/DDL
        _validate_sql(sql_query)

        # Step 4: Execute via read-only Supabase RPC
        rows = _execute_sql(sql_query)

        # Step 5: Compress to stay within agent token budget
        compressed = compress_sql_rows(rows, max_rows=10)

        # Step 6: Format with optional trend note
        output = _format_sql_output(
            question=question,
            sql_query=sql_query,
            row_count=len(rows),
            compressed_table=compressed,
        )

        # Append trend note when time-based or grouped aggregation detected
        sql_upper = sql_query.upper()
        if "DATE_TRUNC" in sql_upper or "GROUP BY" in sql_upper:
            output += (
                "\n\nTrend note: This query uses time-based grouping — "
                "examine the results for period-over-period changes."
            )

        # Step 7: Cache the result
        cache.set(cache_key, output, ttl=settings.cache_ttl_seconds)

        return output

    except Exception as e:
        logger.error("ecommerce_analytics_query failed: %s: %s", type(e).__name__, e)
        error_msg = f"ecommerce_analytics_query failed: {type(e).__name__}: {e}"
        try:
            if 'sql_query' in locals() and sql_query:
                error_msg += f"\nGenerated SQL that caused error:\n{sql_query}\n(Tip: Instruct the sub-agent to fix this specific syntax error by explicitly telling it what to avoid in your question.)"
        except Exception:
            pass
        return error_msg


# ═══════════════════════════════════════════════════════════════════════
# Shared private helpers
# ═══════════════════════════════════════════════════════════════════════


@exponential_backoff(max_retries=0, base_delay_seconds=2.0)
def _generate_sql(
    question: str,
    max_rows: int,
    filter_campaign_id: str | None,
    filter_product_sku: str | None,
    date_from: str | None,
    date_to: str | None,
    analytics_mode: bool,
    table_hint: str | None = None,
) -> str:
    """Use Gemini Flash to generate a safe SELECT query from a natural-language question.

    Args:
        question: The analyst's natural-language question.
        max_rows: LIMIT value appended to every query.
        filter_campaign_id: Optional campaign ID to inject as a filter hint.
        filter_product_sku: Optional product SKU to inject as a filter hint.
        date_from: Optional start date filter hint (YYYY-MM-DD).
        date_to: Optional end date filter hint (YYYY-MM-DD).
        analytics_mode: Whether to add analytics-specific prompt guidance.
        table_hint: Optional table name hint for the LLM.

    Returns:
        Raw SQL SELECT statement string (stripped of markdown fences).

    Raises:
        ValueError: If the LLM returns an empty response.
    """
    extra_guidance = _ANALYTICS_GUIDANCE if analytics_mode else ""
    table_context = f"\nFocus on table(s): {table_hint}." if table_hint else ""

    active_filters: list[str] = []
    if filter_campaign_id and _SAFE_ID_PATTERN.match(filter_campaign_id):
        active_filters.append(f"campaign_id = '{filter_campaign_id}'")
    if filter_product_sku and _SAFE_ID_PATTERN.match(filter_product_sku):
        active_filters.append(f"product_sku = '{filter_product_sku}'")
    if date_from and _SAFE_DATE_PATTERN.match(date_from):
        active_filters.append(f"date >= '{date_from}'")
    if date_to and _SAFE_DATE_PATTERN.match(date_to):
        active_filters.append(f"date <= '{date_to}'")
    filter_clause = (
        f"\nApply these WHERE filters where applicable: {', '.join(active_filters)}."
        if active_filters
        else ""
    )

    prompt = f"""You are a PostgreSQL expert. Generate a single, correct SELECT query.
Return ONLY the raw SQL statement — no markdown fences, no explanation.

{_SCHEMA_DOC}

Rules:
- SELECT only. Never generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, etc.
- Always include LIMIT {max_rows}.
- Use standard PostgreSQL syntax.
- Use table aliases for readability on JOINs.
- ALWAYS include an explicit ORDER BY clause to ensure deterministic results.
- Use COALESCE() around nullable aggregations for consistent NULL handling.
- Alias all computed columns with clear, descriptive names.{table_context}{filter_clause}{extra_guidance}

Question: {question}"""

    response = get_sub_llm(max_output_tokens=600).invoke(prompt)
    sql_query = extract_text(response.content).strip()

    import re
    match = re.search(r"```(?:sql)?\n?(.*?)\n?```", sql_query, flags=re.IGNORECASE | re.DOTALL)
    if match:
        sql_query = match.group(1).strip()
        
    sql_query = "\n".join([ln for ln in sql_query.splitlines() if not ln.strip().startswith("```")]).strip()
    # Strip any trailing semicolons which cause Supabase RPC syntax errors
    sql_query = sql_query.rstrip(";")

    if not sql_query:
        raise ValueError("Sub-agent LLM returned an empty SQL response.")

    logger.info("Generated SQL (first 200 chars): %s", sql_query[:200])
    return sql_query


def _validate_sql(sql_query: str) -> None:
    """Validate that a SQL query is safe to execute.

    Performs two checks:
    1. The statement must begin with SELECT (after stripping whitespace/CTEs).
    2. No forbidden DML/DDL keyword appears at a word boundary.

    Args:
        sql_query: The SQL string to validate.

    Raises:
        ValueError: If the query fails either safety check.
    """
    stripped = sql_query.strip()

    # A read-only query must start with SELECT or WITH (for CTEs)
    upper_start = stripped.upper()

    if not (upper_start.startswith("SELECT") or upper_start.startswith("WITH")):
        raise ValueError(
            f"SQL must start with SELECT or WITH. Got: {stripped[:60]!r}"
        )

    match = _FORBIDDEN_PATTERN.search(stripped)
    if match:
        raise ValueError(
            f"SQL contains forbidden keyword '{match.group()}' — "
            "only read-only SELECT queries are permitted."
        )


@exponential_backoff(max_retries=0, base_delay_seconds=2.0)
def _execute_sql(sql_query: str) -> list[dict[str, Any]]:
    """Execute a validated SELECT query against Supabase via the read-only RPC.

    Args:
        sql_query: A validated SELECT query string.

    Returns:
        List of row dictionaries from the query result.

    Raises:
        Exception: Propagated after all retry attempts are exhausted.
    """
    client = get_supabase_client()
    response = client.rpc(
        "execute_readonly_sql",
        {"query": sql_query},
    ).execute()
    data: list[dict[str, Any]] = response.data or []
    logger.info("SQL query returned %d rows.", len(data))
    return data


def _format_sql_output(
    question: str,
    sql_query: str,
    row_count: int,
    compressed_table: str,
) -> str:
    """Format SQL query results into a structured string for the agent.

    Args:
        question: The original analyst question.
        sql_query: The SQL statement that was executed.
        row_count: Total rows returned by the query.
        compressed_table: Compressed markdown table (token-budget-aware).

    Returns:
        Formatted multi-line string ready for the agent to synthesise.
    """
    return "\n".join(
        [
            "SQL QUERY RESULT",
            "─────────────────────────────────────",
            f"Question : {question}",
            f"SQL      : {sql_query}",
            f"Rows     : {row_count}",
            "─────────────────────────────────────",
            compressed_table,
        ]
    )
