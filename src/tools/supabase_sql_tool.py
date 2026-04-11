"""LangChain tool wrapping parameterised SQL queries against Supabase structured tables.

This tool is given to the SQL Analyst Agent so it can safely query
``customers``, ``orders``, ``shipments``, ``marketing_campaigns``,
``campaign_products``, and ``events_log``.

All queries go through the Supabase PostgREST API — never raw SQL
string interpolation.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from crewai.tools import BaseTool
from pydantic import Field

from src.config import get_settings
from src.db.supabase_client import get_supabase_client
from src.tools.retry_mixin import with_exponential_backoff

logger = logging.getLogger(__name__)

# Tables the agent is allowed to query
ALLOWED_TABLES: frozenset[str] = frozenset(
    {
        "customers",
        "orders",
        "shipments",
        "marketing_campaigns",
        "campaign_products",
        "events_log",
    }
)


class SupabaseSQLTool(BaseTool):
    """Execute parameterised queries against Supabase structured tables.

    The tool accepts a JSON instruction string with the following keys:

    * ``table`` (str): Name of the table to query.
    * ``select`` (str): Comma-separated column list (default ``"*"``).
      **Do NOT use SQL aggregate functions** (COUNT, SUM, AVG, GROUP BY)
      — PostgREST does not support them.
    * ``filters`` (list[dict]): Optional list of filter objects, each with
      ``column``, ``operator`` (``eq``, ``gt``, ``lt``, ``gte``, ``lte``,
      ``neq``, ``like``, ``ilike``, ``in``), and ``value``.
    * ``order_by`` (str): Optional column name to sort by.
    * ``ascending`` (bool): Sort direction (default ``True``).
    * ``limit`` (int): Maximum rows to return (capped at max_sql_rows).

    Attributes:
        name: Tool name visible to the agent.
        description: Human-readable purpose of this tool.
    """

    name: str = "supabase_sql_query"
    description: str = (
        "Execute a parameterised read query against Supabase structured "
        "e-commerce tables (customers, orders, shipments, marketing_campaigns, "
        "campaign_products, events_log). Input must be a JSON string with keys: "
        "table, select (raw columns ONLY — no COUNT/SUM/AVG), "
        "filters (list of {column, operator, value} where operator is one of: "
        "eq, gt, lt, gte, lte, neq, like, ilike, in), "
        "order_by, ascending, limit."
    )

    @with_exponential_backoff(max_retries=3, base_delay_seconds=2.0)
    def _run(self, query_json: str) -> str:
        """Execute the parameterised Supabase query.

        Args:
            query_json: JSON string describing the query.

        Returns:
            JSON string containing the query results or an error message.

        Raises:
            ValueError: If the table name is not in the allow-list.
        """
        try:
            params: dict[str, Any] = json.loads(query_json)
        except json.JSONDecodeError as exc:
            error_msg = f"Invalid JSON input: {exc}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

        table_name: str = params.get("table", "")
        if table_name not in ALLOWED_TABLES:
            error_msg = (
                f"Table '{table_name}' is not allowed. "
                f"Permitted tables: {sorted(ALLOWED_TABLES)}"
            )
            logger.warning(error_msg)
            return json.dumps({"error": error_msg})

        # Reject aggregate functions in select — PostgREST doesn't support them
        select_cols: str = params.get("select", "*")
        aggregate_keywords = ("count(", "sum(", "avg(", "min(", "max(", "group by")
        if any(kw in select_cols.lower() for kw in aggregate_keywords):
            error_msg = (
                f"Aggregate functions are not supported in PostgREST select. "
                f"Select raw columns only and compute aggregations from returned rows. "
                f"Rejected select: '{select_cols}'"
            )
            logger.warning(error_msg)
            return json.dumps({"error": error_msg})

        filters: list[dict[str, Any]] = params.get("filters", [])
        order_by: Optional[str] = params.get("order_by")
        ascending: bool = params.get("ascending", True)

        settings = get_settings()
        max_rows = settings.max_sql_rows
        limit: int = min(params.get("limit", max_rows), max_rows)

        client = get_supabase_client()
        query = client.table(table_name).select(select_cols)

        query = _apply_filters(query, filters)

        if order_by:
            query = query.order(order_by, desc=(not ascending))

        query = query.limit(limit)

        logger.info(
            "Executing Supabase query — table=%s select=%s filters=%s limit=%d",
            table_name,
            select_cols,
            filters,
            limit,
        )

        try:
            response = query.execute()
            data: list[dict[str, Any]] = response.data if response.data else []
            result = {
                "table": table_name,
                "row_count": len(data),
                "rows": data,
            }
            logger.info("Query returned %d rows.", len(data))
            return json.dumps(result, default=str)
        except Exception as exc:
            error_msg = f"Supabase query failed: {exc}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})


def _apply_filters(
    query: Any,
    filters: list[dict[str, Any]],
) -> Any:
    """Apply a list of filter predicates to a Supabase query builder.

    Supports operator aliases so LLMs using standard SQL-style operators
    (``>=``, ``<=``, ``>``, ``<``, ``!=``) are automatically mapped to
    the corresponding PostgREST methods.

    Args:
        query: An in-progress Supabase query builder.
        filters: List of filter dicts with ``column``, ``operator``, ``value``.

    Returns:
        The query builder with all filters applied.

    Raises:
        ValueError: If an unsupported operator is used.
    """
    operator_map: dict[str, str] = {
        "eq": "eq",
        "gt": "gt",
        "lt": "lt",
        "gte": "gte",
        "lte": "lte",
        "neq": "neq",
        "like": "like",
        "ilike": "ilike",
        "in": "in_",
        # Aliases — LLMs often generate standard SQL-style operators
        ">=": "gte",
        "<=": "lte",
        ">": "gt",
        "<": "lt",
        "!=": "neq",
        "=": "eq",
    }
    for f in filters:
        col: str = f.get("column", "")
        op: str = f.get("operator", "eq")
        val: Any = f.get("value")

        supabase_method: Optional[str] = operator_map.get(op)
        if supabase_method is None:
            logger.warning("Unsupported filter operator '%s' — skipping.", op)
            continue

        method = getattr(query, supabase_method, None)
        if method is None:
            logger.warning("Query builder has no method '%s'.", supabase_method)
            continue

        query = method(col, val)
        logger.debug("Applied filter: %s %s %s", col, op, val)

    return query
