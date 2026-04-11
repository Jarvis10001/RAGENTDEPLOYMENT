"""Diagnostic Crew — orchestrates all agents through the diagnostic pipeline.

Flow::

    User Question
        → Query Router Agent  (intent classification)
        → SQL Analyst Agent   (if needs_sql)
        → RAG Retrieval Agent (if needs_rag)
        → Synthesis Agent     (if needs_synthesis, or if both SQL & RAG ran)
        → DiagnosticReport

The crew runs sequentially: router first, then conditional branches, then
synthesis.  When both SQL and RAG are needed the agents execute their
tasks and their outputs are merged by the Synthesis Agent.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from crewai import Crew, Process

from src.agents.query_router_agent import (
    build_query_router_agent,
    build_query_router_task,
    parse_router_output,
)
from src.agents.rag_retrieval_agent import (
    build_rag_retrieval_agent,
    build_rag_retrieval_task,
    parse_rag_retrieval_output,
)
from src.agents.sql_analyst_agent import (
    build_sql_analyst_agent,
    build_sql_analyst_task,
    parse_sql_analyst_output,
)
from src.agents.synthesis_agent import (
    build_synthesis_agent,
    build_synthesis_task,
    parse_synthesis_output,
)
from src.models.diagnostic_report import ActionItem, DiagnosticReport
from src.models.query_intent import QueryIntent
from src.models.rag_result import RAGResult
from src.models.sql_result import SQLAnalysisResult

logger = logging.getLogger(__name__)


class DiagnosticCrew:
    """Orchestrate the multi-agent diagnostic pipeline.

    This class wires together the Query Router, SQL Analyst, RAG Retrieval,
    and Synthesis agents into a conditional sequential flow.

    Attributes:
        verbose: Whether to enable verbose logging in agents.
    """

    def __init__(self, verbose: bool = False) -> None:
        """Initialise the crew with pre-built agents.

        Args:
            verbose: Enable verbose agent output.
        """
        self.verbose: bool = verbose
        self._router_agent = build_query_router_agent()
        self._sql_agent = build_sql_analyst_agent()
        self._rag_agent = build_rag_retrieval_agent()
        self._synthesis_agent = build_synthesis_agent()
        logger.info("DiagnosticCrew initialised with all agents.")

    def run(self, user_query: str) -> DiagnosticReport:
        """Execute the full diagnostic pipeline for a user query.

        Args:
            user_query: The analyst's natural-language question.

        Returns:
            A validated :class:`DiagnosticReport` with root-cause analysis,
            evidence, and action items.

        Raises:
            RuntimeError: If the crew execution fails catastrophically.
        """
        logger.info("═══ Starting diagnostic pipeline ═══")
        logger.info("Query: %s", user_query)

        # ── Step 1: Route the query ──────────────────────
        intent: QueryIntent = self._route_query(user_query)
        logger.info(
            "Routing decision — sql=%s rag=%s synthesis=%s type=%s",
            intent.needs_sql,
            intent.needs_rag,
            intent.needs_synthesis,
            intent.query_type.value,
        )

        # ── Step 2: Execute SQL analysis (conditional) ───
        sql_result: Optional[SQLAnalysisResult] = None
        if intent.needs_sql:
            sql_result = self._run_sql_analysis(intent, user_query)
            logger.info("SQL analysis complete — severity=%s", sql_result.severity.value)

        # ── Step 3: Execute RAG retrieval (conditional) ──
        rag_result: Optional[RAGResult] = None
        if intent.needs_rag:
            rag_result = self._run_rag_retrieval(intent, user_query)
            logger.info(
                "RAG retrieval complete — themes=%d",
                len(rag_result.top_themes),
            )

        # ── Step 4: Synthesise results ───────────────────
        if intent.needs_synthesis or (sql_result and rag_result):
            report = self._run_synthesis(user_query, sql_result, rag_result)
        elif sql_result and not rag_result:
            report = self._sql_only_report(sql_result, user_query)
        elif rag_result and not sql_result:
            report = self._rag_only_report(rag_result, user_query)
        else:
            report = self._fallback_report(user_query)

        logger.info(
            "═══ Pipeline complete — urgency=%d confidence=%d ═══",
            report.urgency_score,
            report.confidence_score,
        )
        return report

    def _route_query(self, user_query: str) -> QueryIntent:
        """Run the Query Router Agent to classify intent.

        Args:
            user_query: The original analyst question.

        Returns:
            A validated :class:`QueryIntent`.
        """
        router_task = build_query_router_task(self._router_agent, user_query)

        crew = Crew(
            agents=[self._router_agent],
            tasks=[router_task],
            process=Process.sequential,
            verbose=self.verbose,
        )

        result = crew.kickoff()
        return parse_router_output(result)

    def _run_sql_analysis(
        self,
        intent: QueryIntent,
        user_query: str,
    ) -> SQLAnalysisResult:
        """Run the SQL Analyst Agent.

        Args:
            intent: Parsed intent with extracted filters.
            user_query: The original question.

        Returns:
            A validated :class:`SQLAnalysisResult`.
        """
        sql_task = build_sql_analyst_task(self._sql_agent, intent, user_query)

        crew = Crew(
            agents=[self._sql_agent],
            tasks=[sql_task],
            process=Process.sequential,
            verbose=self.verbose,
        )

        result = crew.kickoff()
        return parse_sql_analyst_output(result)

    def _run_rag_retrieval(
        self,
        intent: QueryIntent,
        user_query: str,
    ) -> RAGResult:
        """Run the RAG Retrieval Agent.

        Args:
            intent: Parsed intent with extracted filters.
            user_query: The original question.

        Returns:
            A validated :class:`RAGResult`.
        """
        rag_task = build_rag_retrieval_task(self._rag_agent, intent, user_query)

        crew = Crew(
            agents=[self._rag_agent],
            tasks=[rag_task],
            process=Process.sequential,
            verbose=self.verbose,
        )

        result = crew.kickoff()
        return parse_rag_retrieval_output(result)

    def _run_synthesis(
        self,
        user_query: str,
        sql_result: Optional[SQLAnalysisResult],
        rag_result: Optional[RAGResult],
    ) -> DiagnosticReport:
        """Run the Synthesis Agent to merge findings.

        Args:
            user_query: The original question.
            sql_result: SQL findings (may be None).
            rag_result: RAG findings (may be None).

        Returns:
            A validated :class:`DiagnosticReport`.
        """
        synthesis_task = build_synthesis_task(
            self._synthesis_agent, user_query, sql_result, rag_result
        )

        crew = Crew(
            agents=[self._synthesis_agent],
            tasks=[synthesis_task],
            process=Process.sequential,
            verbose=self.verbose,
        )

        result = crew.kickoff()
        return parse_synthesis_output(result)

    def _sql_only_report(
        self,
        sql_result: SQLAnalysisResult,
        user_query: str,
    ) -> DiagnosticReport:
        """Build a report from SQL-only results without synthesis.

        Args:
            sql_result: The SQL analysis result.
            user_query: The original question.

        Returns:
            A :class:`DiagnosticReport` based on SQL evidence alone.
        """
        return DiagnosticReport(
            executive_summary=(
                f"SQL analysis for: {user_query}\n\n"
                f"{sql_result.analysis_summary}"
            ),
            confirmed_root_cause=sql_result.analysis_summary or "See key metrics.",
            contributing_factors=[],
            revenue_impact_estimate="See key metrics for quantitative details.",
            urgency_score=_severity_to_urgency(sql_result.severity.value),
            confidence_score=7,
            action_items=[
                ActionItem(
                    action="Review the key metrics and investigate further.",
                    owner="Analytics Team",
                    priority="short_term",
                    expected_impact="Identify specific root cause.",
                )
            ],
            data_gaps=["No qualitative RAG analysis was performed."],
            supporting_sql_evidence=sql_result.key_metrics,
            supporting_rag_evidence=[],
        )

    def _rag_only_report(
        self,
        rag_result: RAGResult,
        user_query: str,
    ) -> DiagnosticReport:
        """Build a report from RAG-only results without synthesis.

        Args:
            rag_result: The RAG retrieval result.
            user_query: The original question.

        Returns:
            A :class:`DiagnosticReport` based on qualitative evidence alone.
        """
        return DiagnosticReport(
            executive_summary=(
                f"Qualitative analysis for: {user_query}\n\n"
                f"{rag_result.full_narrative}"
            ),
            confirmed_root_cause=rag_result.full_narrative[:500] or "See themes below.",
            contributing_factors=rag_result.top_themes,
            revenue_impact_estimate="Requires quantitative analysis to estimate.",
            urgency_score=7 if rag_result.urgency_signals else 4,
            confidence_score=5,
            action_items=[
                ActionItem(
                    action="Run quantitative analysis to validate qualitative findings.",
                    owner="Analytics Team",
                    priority="short_term",
                    expected_impact="Quantify the revenue impact of identified themes.",
                )
            ],
            data_gaps=["No SQL quantitative analysis was performed."],
            supporting_sql_evidence={},
            supporting_rag_evidence=rag_result.representative_quotes,
        )

    def _fallback_report(self, user_query: str) -> DiagnosticReport:
        """Build a fallback report when no agents produced results.

        Args:
            user_query: The original question.

        Returns:
            A minimal :class:`DiagnosticReport` indicating no data was found.
        """
        return DiagnosticReport(
            executive_summary=(
                f"Unable to produce a diagnostic report for: {user_query}. "
                f"Neither SQL nor RAG analysis was triggered by the router."
            ),
            confirmed_root_cause="Insufficient data to determine root cause.",
            urgency_score=3,
            confidence_score=1,
            action_items=[
                ActionItem(
                    action="Rephrase the question with more specificity.",
                    owner="Analyst",
                    priority="immediate",
                    expected_impact="Enable the system to route to the right data sources.",
                )
            ],
            data_gaps=[
                "Router did not activate any analysis agents.",
                "Consider rephrasing with specific metrics, campaigns, or product SKUs.",
            ],
        )


def _severity_to_urgency(severity: str) -> int:
    """Map a severity label to an urgency score.

    Args:
        severity: One of ``"low"``, ``"medium"``, ``"high"``, ``"critical"``.

    Returns:
        Integer urgency score from 1 to 10.
    """
    mapping: dict[str, int] = {
        "low": 3,
        "medium": 5,
        "high": 7,
        "critical": 9,
    }
    return mapping.get(severity, 5)
