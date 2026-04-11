"""Unit tests for token budget compression utilities.

Tests ``compress_sql_rows`` and ``compress_rag_chunks`` from
``src.utils.token_budget``.
"""

from __future__ import annotations

import pytest

from src.utils.token_budget import compress_rag_chunks, compress_sql_rows


class TestCompressSqlRows:
    """Tests for compress_sql_rows."""

    def test_empty_rows_returns_no_rows_message(self) -> None:
        """Verify that an empty row list returns a 'no rows' message."""
        result = compress_sql_rows([])
        assert "_No rows returned._" in result

    def test_single_row_produces_valid_table(self) -> None:
        """Verify that a single row produces a valid markdown table."""
        rows = [{"name": "Alice", "age": 30}]
        result = compress_sql_rows(rows, max_rows=5)
        assert "| name | age |" in result
        assert "| Alice | 30 |" in result
        assert "---" in result

    def test_rows_within_limit_all_included(self) -> None:
        """Verify that all rows are included when count <= max_rows."""
        rows = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3, "value": "c"},
        ]
        result = compress_sql_rows(rows, max_rows=5)
        assert "| 1 |" in result
        assert "| 2 |" in result
        assert "| 3 |" in result
        assert "additional rows omitted" not in result

    def test_rows_exceeding_limit_are_truncated(self) -> None:
        """Verify that rows beyond max_rows are truncated with footer note."""
        rows = [{"id": i, "val": f"row{i}"} for i in range(10)]
        result = compress_sql_rows(rows, max_rows=3)
        # First 3 rows present
        assert "| 0 |" in result
        assert "| 2 |" in result
        # Row 3 and beyond should NOT be in the table
        assert "7 additional rows omitted" in result
        assert "10 total" in result

    def test_long_cell_values_are_truncated(self) -> None:
        """Verify that very long cell values are truncated with ellipsis."""
        rows = [{"description": "x" * 100}]
        result = compress_sql_rows(rows, max_rows=5)
        # Default max_len is 60, so content should be truncated
        assert "…" in result


class TestCompressRagChunks:
    """Tests for compress_rag_chunks."""

    def test_empty_chunks_returns_no_passages_message(self) -> None:
        """Verify that an empty chunk list returns a 'no passages' message."""
        result = compress_rag_chunks([])
        assert "_No relevant text passages found._" in result

    def test_chunks_within_limit_all_included(self) -> None:
        """Verify that all chunks are included when count <= max_chunks."""
        chunks = ["First passage", "Second passage", "Third passage"]
        result = compress_rag_chunks(chunks, max_chunks=5)
        assert "[1] First passage" in result
        assert "[2] Second passage" in result
        assert "[3] Third passage" in result
        assert "additional passages omitted" not in result

    def test_chunks_exceeding_limit_are_truncated(self) -> None:
        """Verify that chunks beyond max_chunks are omitted with footer note."""
        chunks = [f"Passage {i}" for i in range(8)]
        result = compress_rag_chunks(chunks, max_chunks=3)
        assert "[1] Passage 0" in result
        assert "[3] Passage 2" in result
        assert "5 additional passages omitted" in result

    def test_long_chunks_are_character_truncated(self) -> None:
        """Verify that individual chunks are truncated at max_chars_per_chunk."""
        chunks = ["A" * 500]
        result = compress_rag_chunks(chunks, max_chars_per_chunk=100, max_chunks=5)
        # Should have 100 A's followed by ellipsis
        assert "…" in result
        # Should not contain all 500 A's
        assert "A" * 500 not in result
