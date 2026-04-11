"""Synthesis Agent — merges SQL and RAG findings into a diagnostic report.

This agent acts as the "Chief Revenue Intelligence Officer", combining
quantitative metrics with qualitative customer signals to produce a
single :class:`DiagnosticReport` with root-cause analysis, revenue
impact estimates, and prioritised action items.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from crewai import Agent, Task
from crewai import LLM

from src.config import get_settings
from src.models.diagnostic_report import ActionItem, DiagnosticReport
from src.models.rag_result import RAGResult
from src.models.sql_result import SQLAnalysisResult

logger = logging.getLogger(__name__)


def build_synthesis_agent() -> Agent:
    """Construct the Synthesis Agent.

    This agent needs the most output room to write the full diagnostic
    report, so it gets max_tokens=2048.

    Returns:
        A fully-configured :class:`crewai.Agent` for diagnostic synthesis.
    """
    settings = get_settings()

    llm = LLM(
        model=settings.synthesis_model_name,   # "groq/llama-3.1-70b-versatile"
        temperature=0.1,
        max_tokens=2048,
    )

    agent = Agent(
        role="Chief Revenue Intelligence Officer",
        goal=(
            "Combine SQLAnalysisResult and RAGResult into a comprehensive "
            "DiagnosticReport.  Identify the confirmed root cause, list "
            "contributing factors, estimate revenue impact, assign urgency "
            "and confidence scores, and produce prioritised action items. "
            "Always cite specific evidence from both SQL and RAG findings."
        ),
        backstory=(
            "You are a C-suite revenue strategist who can read both "
            "spreadsheets and customer sentiment.  You triangulate hard "
            "metrics with qualitative signals to deliver root-cause analyses "
            "that drive executive decisions.  Your reports are known for "
            "their clarity, specificity, and actionability."
        ),
        llm=llm,
        verbose=settings.debug,
        allow_delegation=False,
    )
    return agent


def build_synthesis_task(
    agent: Agent,
    user_query: str,
    sql_result: Optional[SQLAnalysisResult] = None,
    rag_result: Optional[RAGResult] = None,
) -> Task:
    """Build the synthesis task merging SQL and RAG results.

    Args:
        agent: The Synthesis Agent.
        user_query: The original analyst question.
        sql_result: Structured findings from the SQL Analyst Agent (may be None).
        rag_result: Qualitative findings from the RAG Retrieval Agent (may be None).

    Returns:
        A :class:`crewai.Task` whose output is a ``DiagnosticReport`` JSON.
    """
    sql_section: str = _format_sql_evidence(sql_result)
    rag_section: str = _format_rag_evidence(rag_result)

    description = f"""You are synthesising a diagnostic report for the following question:

QUESTION: {user_query}

═══ SQL ANALYSIS FINDINGS ═══
{sql_section}

═══ RAG QUALITATIVE FINDINGS ═══
{rag_section}

INSTRUCTIONS:
Produce a JSON object with EXACTLY these fields:
- executive_summary (str): one-paragraph executive brief
- confirmed_root_cause (str): the most likely root cause, citing specific evidence
- contributing_factors (list of str): additional factors that compound the issue
- revenue_impact_estimate (str): estimated revenue effect (e.g. "$45k/month at risk")
- urgency_score (int 1-10): how urgently this needs action
- confidence_score (int 1-10): how confident you are in the root cause
- action_items (list of objects): each with "action", "owner", "priority" (immediate/short_term/long_term), "expected_impact"
- data_gaps (list of str): missing data or blind spots
- supporting_sql_evidence (dict): key metrics from SQL analysis
- supporting_rag_evidence (list of str): key quotes/themes from RAG

RULES:
1. You MUST cite specific numbers from SQL findings in your executive_summary.
2. You MUST reference specific customer quotes or themes from RAG findings.
3. If one data source is missing, acknowledge the gap and adjust confidence_score downward.
4. action_items must be concrete and assignable — no vague suggestions.
5. Provide at least 2 action_items.

Respond with ONLY valid JSON, no markdown fences."""

    task = Task(
        description=description,
        expected_output="A JSON object matching the DiagnosticReport schema.",
        agent=agent,
        output_pydantic=DiagnosticReport,
    )
    return task


def parse_synthesis_output(raw_output: Any) -> DiagnosticReport:
    """Parse the raw LLM output into a validated DiagnosticReport.

    Args:
        raw_output: The raw output from the synthesis task.

    Returns:
        A validated :class:`DiagnosticReport` instance.

    Raises:
        ValueError: If parsing fails and no fallback is possible.
    """
    if hasattr(raw_output, "pydantic") and raw_output.pydantic:
        return raw_output.pydantic

    raw_str = str(raw_output)
    cleaned: str = _strip_markdown_fences(raw_str)

    try:
        data: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(
            "Synthesis output is not valid JSON. Building fallback report."
        )
        return DiagnosticReport(
            executive_summary=raw_str[:2000],
            confirmed_root_cause="Unable to parse structured root cause from LLM output.",
            confidence_score=2,
            urgency_score=5,
            action_items=[
                ActionItem(
                    action="Review the raw synthesis output for insights.",
                    owner="Analytics Team",
                    priority="immediate",
                    expected_impact="Unblock the investigation.",
                )
            ],
            data_gaps=["Synthesis output was not parseable as JSON."],
        )

    # Parse nested action_items
    if "action_items" in data and isinstance(data["action_items"], list):
        parsed_items: list[ActionItem] = []
        for item in data["action_items"]:
            if isinstance(item, dict):
                parsed_items.append(ActionItem(**item))
        data["action_items"] = parsed_items

    report = DiagnosticReport(**data)
    logger.info(
        "Parsed DiagnosticReport — urgency=%d confidence=%d actions=%d",
        report.urgency_score,
        report.confidence_score,
        len(report.action_items),
    )
    return report


def _format_sql_evidence(result: Optional[SQLAnalysisResult]) -> str:
    """Format SQL analysis results for the synthesis prompt.

    Args:
        result: The SQL analysis result, or None if not available.

    Returns:
        Formatted string of SQL evidence.
    """
    if result is None:
        return "No SQL analysis was performed for this query."

    parts: list[str] = [
        f"Query executed: {result.sql_executed}",
        f"Severity: {result.severity.value}",
        f"Affected segment: {result.affected_segment}",
        f"Analysis: {result.analysis_summary}",
        "Key metrics:",
    ]
    for metric, value in result.key_metrics.items():
        parts.append(f"  - {metric}: {value}")

    if result.raw_rows:
        parts.append(f"\nSample data ({len(result.raw_rows)} rows):")
        for row in result.raw_rows[:5]:
            parts.append(f"  {json.dumps(row, default=str)}")

    return "\n".join(parts)


def _format_rag_evidence(result: Optional[RAGResult]) -> str:
    """Format RAG results for the synthesis prompt.

    Args:
        result: The RAG result, or None if not available.

    Returns:
        Formatted string of RAG evidence.
    """
    if result is None:
        return "No RAG retrieval was performed for this query."

    parts: list[str] = [
        "Top themes: " + ", ".join(result.top_themes) if result.top_themes else "No themes identified.",
        "\nRepresentative quotes:",
    ]
    for quote in result.representative_quotes:
        parts.append(f'  - "{quote}"')

    if result.sentiment_scores:
        parts.append("\nSentiment scores:")
        for label, score in result.sentiment_scores.items():
            parts.append(f"  - {label}: {score:.2f}")

    if result.urgency_signals:
        parts.append("\nUrgency signals:")
        for signal in result.urgency_signals:
            parts.append(f"  - {signal}")

    parts.append(f"\nFull narrative: {result.full_narrative}")

    if result.source_breakdown:
        parts.append("\nSource breakdown:")
        for source, count in result.source_breakdown.items():
            parts.append(f"  - {source}: {count} chunks")

    return "\n".join(parts)


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
