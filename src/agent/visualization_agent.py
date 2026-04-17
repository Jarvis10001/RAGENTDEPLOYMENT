"""Visualization Agent — analyzes tool output and generates chart specs.

Examines SQL/analytics tool output to determine if data is chartable,
selects the best chart type, and returns a structured Recharts-compatible
JSON spec that the frontend can render inline.

Design decisions
----------------
* Uses the shared sub-LLM (Gemini Flash) for fast, cheap chart reasoning.
* Returns None if data is not chartable (text-only, single scalar, errors).
* Chart spec is a plain dict matching the frontend ChartSpec TypeScript interface.
* Runs synchronously — called after tool outputs are collected.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.llm import extract_text, get_sub_llm

logger = logging.getLogger(__name__)

# Chart spec structure matching frontend ChartSpec interface
ChartSpecDict = dict[str, Any]

_CHART_PROMPT = """You are a data visualization expert. Analyze the tool output below and determine if it should be visualized as a chart.

RULES:
1. If the data contains ONLY a single scalar value, ONLY text (with no tabular data), or an error message, respond with exactly: NO_CHART
2. If the data contains tabular/structured data with at least 2 rows of numeric values, YOU MUST generate a chart specification — EVEN IF there is extra text or trend notes appended to the bottom. Ignore the extra text.
3. Choose the BEST chart type based on the data:
   - Time series / trends over periods → "line" or "area"
   - Category comparisons (revenue by campaign, cost by warehouse) → "bar"
   - Proportions / percentage breakdowns → "pie"
   - Correlation between two numeric variables → "scatter"
   - Multi-dimensional comparison (e.g. radar metrics) → "radar"
4. Extract ACTUAL data values from the tool output — never invent data.
5. Use descriptive, short labels for axes and legend.

RESPOND WITH ONLY valid JSON in this exact format (no markdown fences, no explanation):
{{
  "chart_type": "bar|line|area|pie|scatter|radar",
  "title": "Short descriptive title",
  "data": [{{ "key1": "value1", "key2": 123 }}, ...],
  "x_key": "field_name_for_x_axis",
  "y_keys": ["field_name_for_y_axis_1", "optional_second_y_field"],
  "colors": ["#6366F1", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#06B6D4"]
}}

Or respond with exactly: NO_CHART

TOOL OUTPUT:
{tool_output}
"""


def generate_chart_spec(tool_outputs: list[dict[str, str]]) -> ChartSpecDict | None:
    """Analyze tool outputs and generate a chart specification if appropriate.

    Args:
        tool_outputs: List of dicts with 'tool' and 'output' keys from the
                      agent's tool execution results.

    Returns:
        A dict matching the ChartSpec interface, or None if no chart is appropriate.
    """
    # Only analyze SQL/analytics outputs — skip RAG and web search
    chartable_outputs = []
    for to in tool_outputs:
        tool_name = to.get("tool", "")
        if "sql" in tool_name or "analytics" in tool_name:
            chartable_outputs.append(to)

    if not chartable_outputs:
        logger.debug("No chartable tool outputs found — skipping visualization.")
        return None

    # Combine relevant outputs for analysis
    combined_output = "\n\n".join(
        f"[{to['tool']}]\n{to['output'][:2000]}" for to in chartable_outputs
    )

    # Quick heuristic: skip if output looks like an error or single value
    if len(combined_output.strip()) < 50:
        return None

    try:
        prompt = _CHART_PROMPT.format(tool_output=combined_output)
        response = get_sub_llm().invoke(prompt)
        raw = extract_text(response.content).strip()

        # Check for explicit no-chart signal
        if "NO_CHART" in raw.upper():
            logger.info("Visualization agent decided: no chart needed.")
            return None

        # Strip markdown fences if present
        match = re.search(r"```(?:json)?\n?(.*?)\n?```", raw, flags=re.DOTALL)
        if match:
            raw = match.group(1).strip()

        spec = json.loads(raw)

        # Validate required fields
        required = {"chart_type", "title", "data", "x_key", "y_keys"}
        if not required.issubset(spec.keys()):
            logger.warning("Chart spec missing required fields: %s", required - spec.keys())
            return None

        # Validate chart_type
        valid_types = {"bar", "line", "area", "pie", "scatter", "radar"}
        if spec["chart_type"] not in valid_types:
            logger.warning("Invalid chart type: %s", spec["chart_type"])
            return None

        # Validate data is a non-empty list
        if not isinstance(spec["data"], list) or len(spec["data"]) < 2:
            logger.info("Chart data has fewer than 2 rows — skipping.")
            return None

        # Ensure colors default
        if "colors" not in spec or not spec["colors"]:
            spec["colors"] = ["#6366F1", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#06B6D4"]

        logger.info(
            "Visualization agent generated %s chart: %s (%d data points)",
            spec["chart_type"],
            spec["title"],
            len(spec["data"]),
        )
        return spec

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse chart spec JSON: %s", e)
        return None
    except Exception as e:
        logger.warning("Visualization agent error: %s: %s", type(e).__name__, e)
        return None
