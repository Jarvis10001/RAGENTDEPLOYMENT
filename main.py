"""Interactive CLI for the E-commerce Intelligence Agent.

Environment variables are set before any CrewAI or LiteLLM imports
to guarantee they are available when those modules initialise their
telemetry and provider routing subsystems.

Run with::

    python main.py

Or with a one-shot question::

    python main.py --query "Why did our profit margin drop last month?"
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

# ── Silence CrewAI/OpenTelemetry telemetry BEFORE any crewai import ──
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

# ── Force LiteLLM to find the Groq key by its expected env var name ──
# Must happen before litellm is imported (which happens inside crewai).
from src.config import get_settings

_settings = get_settings()
os.environ["GROQ_API_KEY"] = _settings.groq_api_key

# ── Configure LiteLLM Rate Limit Auto-Retries ──
os.environ["LITELLM_NUM_RETRIES"] = "5"
os.environ["LITELLM_MAX_BACKOFF"] = "30" # Wait up to 30s per retry

from src.crews.diagnostic_crew import DiagnosticCrew
from src.models.diagnostic_report import DiagnosticReport


def _setup_logging() -> None:
    """Configure console logging based on settings."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.value,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy third-party loggers
    for noisy in (
        "httpx", "httpcore", "urllib3",
        "sentence_transformers", "transformers",
        "opentelemetry", "openinference", "crewai.telemetry",
        "LiteLLM",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _print_report(report: DiagnosticReport) -> None:
    """Pretty-print a DiagnosticReport to the console."""
    cyan  = "\033[96m"
    green = "\033[92m"
    yellow = "\033[93m"
    red   = "\033[91m"
    bold  = "\033[1m"
    reset = "\033[0m"

    print(f"\n{'═'*70}")
    print(f"{bold}{cyan}  DIAGNOSTIC REPORT{reset}")
    print(f"{'═'*70}\n")

    print(f"{bold}📋 EXECUTIVE SUMMARY{reset}")
    print(f"  {report.executive_summary}\n")

    print(f"{bold}🔍 CONFIRMED ROOT CAUSE{reset}")
    print(f"  {report.confirmed_root_cause}\n")

    if report.contributing_factors:
        print(f"{bold}⚠️  CONTRIBUTING FACTORS{reset}")
        for factor in report.contributing_factors:
            print(f"  • {factor}")
        print()

    print(f"{bold}💰 REVENUE IMPACT{reset}")
    print(f"  {report.revenue_impact_estimate}\n")

    # Urgency colour coding
    urgency_colour = green if report.urgency_score <= 3 else (yellow if report.urgency_score <= 6 else red)
    print(f"{bold}📊 SCORES{reset}")
    print(f"  Urgency:    {urgency_colour}{report.urgency_score}/10{reset}")
    print(f"  Confidence: {report.confidence_score}/10\n")

    if report.action_items:
        print(f"{bold}✅ ACTION ITEMS{reset}")
        priority_icons = {"immediate": "🔴", "short_term": "🟡", "long_term": "🟢"}
        for i, item in enumerate(report.action_items, 1):
            icon = priority_icons.get(item.priority, "⚪")
            print(f"  {i}. {icon} [{item.priority.upper()}] {item.action}")
            print(f"      Owner: {item.owner} | Impact: {item.expected_impact}")
        print()

    if report.supporting_sql_evidence:
        print(f"{bold}📈 KEY METRICS (SQL){reset}")
        for k, v in report.supporting_sql_evidence.items():
            print(f"  • {k}: {v}")
        print()

    if report.supporting_rag_evidence:
        print(f"{bold}💬 CUSTOMER EVIDENCE (RAG){reset}")
        for quote in report.supporting_rag_evidence:
            print(f'  • "{quote}"')
        print()

    if report.data_gaps:
        print(f"{bold}🕳️  DATA GAPS{reset}")
        for gap in report.data_gaps:
            print(f"  • {gap}")
        print()

    print(f"{'═'*70}\n")


def run_interactive(crew: DiagnosticCrew) -> None:
    """Start an interactive question-answer loop.

    Args:
        crew: Initialised DiagnosticCrew instance.
    """
    print("\n\033[1m\033[96mE-commerce Intelligence Agent\033[0m")
    print("Type your question and press Enter. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            query = input("\033[93m❓ Your question: \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break

        print("\n\033[90m⏳ Running diagnostic pipeline...\033[0m\n")
        try:
            report = crew.run(query)
            _print_report(report)
        except Exception as exc:
            print(f"\033[91m❌ Error: {exc}\033[0m\n")
            logging.exception("Pipeline error")


def run_oneshot(crew: DiagnosticCrew, query: str) -> None:
    """Run a single query and exit.

    Args:
        crew: Initialised DiagnosticCrew instance.
        query: The analyst's question.
    """
    print(f"\n\033[90m⏳ Running diagnostic pipeline for:\033[0m\n  {query}\n")
    report = crew.run(query)
    _print_report(report)


def main() -> None:
    """Entry point for the E-commerce Intelligence Agent CLI."""
    parser = argparse.ArgumentParser(
        description="E-commerce Intelligence Agent — ask questions about your business.",
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Run a single question and exit (skips interactive mode).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose agent output.",
    )
    args = parser.parse_args()

    _setup_logging()

    print("\033[90mInitialising agents...\033[0m")
    try:
        crew = DiagnosticCrew(verbose=args.verbose)
    except Exception as exc:
        print(f"\033[91m❌ Failed to initialise crew: {exc}\033[0m")
        print("Make sure your .env file is configured correctly.")
        sys.exit(1)

    if args.query:
        run_oneshot(crew, args.query)
    else:
        run_interactive(crew)


if __name__ == "__main__":
    main()
