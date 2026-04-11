"""Token-budget compression utilities.

These helpers ensure that tool outputs sent back to the primary LLM stay
within a reasonable token budget, preventing context-window overflow and
reducing cost.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compress_sql_rows(
    rows: list[dict[str, Any]],
    max_rows: int = 5,
) -> str:
    """Convert a list of row dicts into a compact markdown table.

    If the result set exceeds *max_rows*, only the first *max_rows* rows
    are included and a footer note indicates how many were omitted.

    Args:
        rows: List of dictionaries (one per database row).
        max_rows: Maximum number of rows to include in the output.

    Returns:
        A markdown-formatted table string, or a "no rows" message if the
        input is empty.
    """
    if not rows:
        return "_No rows returned._"

    truncated = rows[:max_rows]
    headers = list(truncated[0].keys())

    # Header row
    header_line = "| " + " | ".join(str(h) for h in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"

    # Data rows
    data_lines: list[str] = []
    for row in truncated:
        values = "| " + " | ".join(_truncate_cell(row.get(h, "")) for h in headers) + " |"
        data_lines.append(values)

    table = "\n".join([header_line, separator, *data_lines])

    if len(rows) > max_rows:
        table += f"\n\n_({len(rows) - max_rows} additional rows omitted — {len(rows)} total)_"

    return table


def compress_rag_chunks(
    chunks: list[str],
    max_chars_per_chunk: int = 350,
    max_chunks: int = 5,
) -> str:
    """Compress RAG retrieval results into a token-friendly string.

    Each chunk is truncated to *max_chars_per_chunk* characters, and at
    most *max_chunks* are included.

    Args:
        chunks: Raw text passages from vector search.
        max_chars_per_chunk: Maximum character count per passage.
        max_chunks: Maximum number of passages to include.

    Returns:
        Numbered, truncated passages as a single formatted string, or a
        "no chunks" message if the input is empty.
    """
    if not chunks:
        return "_No relevant text passages found._"

    lines: list[str] = []
    for idx, chunk in enumerate(chunks[:max_chunks], start=1):
        text = chunk[:max_chars_per_chunk]
        if len(chunk) > max_chars_per_chunk:
            text += "…"
        lines.append(f"[{idx}] {text}")

    result = "\n─────────────────────────────────────\n".join(lines)

    if len(chunks) > max_chunks:
        result += f"\n\n_({len(chunks) - max_chunks} additional passages omitted)_"

    return result


def _truncate_cell(value: Any, max_len: int = 60) -> str:
    """Truncate a single table cell value to keep tables readable.

    Args:
        value: Cell value of any type.
        max_len: Maximum string length before truncation.

    Returns:
        String representation of the value, truncated with ``…`` if needed.
    """
    s = str(value)
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s
