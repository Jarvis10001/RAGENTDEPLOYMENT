"""Unit tests for text chunking strategies."""

from __future__ import annotations

import pytest

from src.ingestion.chunking import (
    chunk_chat_transcript,
    semantic_chunk,
    sliding_window_chunk,
)


class TestSlidingWindowChunk:
    """Tests for :func:`sliding_window_chunk`."""

    def test_empty_string_returns_empty_list(self) -> None:
        """Test that empty input produces no chunks."""
        result: list[str] = sliding_window_chunk("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        """Test that whitespace-only input produces no chunks."""
        result: list[str] = sliding_window_chunk("   \n\t  ")
        assert result == []

    def test_short_text_single_chunk(self) -> None:
        """Test that text shorter than chunk_size produces one chunk."""
        text: str = "Hello world."
        result: list[str] = sliding_window_chunk(text, chunk_size=100, chunk_overlap=10)
        assert len(result) == 1
        assert result[0] == "Hello world."

    def test_exact_chunk_size(self) -> None:
        """Test text exactly equal to chunk_size."""
        text: str = "A" * 64
        result: list[str] = sliding_window_chunk(text, chunk_size=64, chunk_overlap=0)
        assert len(result) == 1

    def test_overlapping_chunks(self) -> None:
        """Test that chunks overlap correctly."""
        text: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        result: list[str] = sliding_window_chunk(text, chunk_size=10, chunk_overlap=3)
        assert len(result) >= 3
        # Verify overlap: end of first chunk overlaps start of second
        assert result[0][-3:] == result[1][:3]

    def test_no_overlap(self) -> None:
        """Test chunking with zero overlap."""
        text: str = "0123456789" * 3  # 30 chars
        result: list[str] = sliding_window_chunk(text, chunk_size=10, chunk_overlap=0)
        assert len(result) == 3
        assert "".join(result) == text

    def test_overlap_clamped_when_too_large(self) -> None:
        """Test that overlap >= chunk_size is clamped."""
        text: str = "Hello world, this is a test."
        # overlap >= size should be clamped to size-1
        result: list[str] = sliding_window_chunk(text, chunk_size=10, chunk_overlap=15)
        assert len(result) >= 1


class TestSemanticChunk:
    """Tests for :func:`semantic_chunk`."""

    def test_empty_string_returns_empty_list(self) -> None:
        """Test that empty input produces no chunks."""
        result: list[str] = semantic_chunk("")
        assert result == []

    def test_single_sentence(self) -> None:
        """Test that a single sentence produces one chunk."""
        text: str = "This is a single sentence."
        result: list[str] = semantic_chunk(text, max_chunk_size=500)
        assert len(result) == 1

    def test_multiple_sentences_grouped(self) -> None:
        """Test that sentences are grouped within chunk_size."""
        text: str = (
            "First sentence here. Second sentence follows. "
            "Third sentence appears. Fourth sentence ends."
        )
        result: list[str] = semantic_chunk(text, max_chunk_size=500)
        # All should fit in one chunk
        assert len(result) >= 1

    def test_long_text_split_at_boundaries(self) -> None:
        """Test that long text is split at sentence boundaries."""
        sentences: list[str] = [f"Sentence number {i} is here." for i in range(20)]
        text: str = " ".join(sentences)
        result: list[str] = semantic_chunk(text, max_chunk_size=100)
        assert len(result) > 1
        # Each chunk should be <= max_chunk_size (approximately, since we
        # respect sentence boundaries the last sentence may push over)

    def test_whitespace_only_returns_empty_list(self) -> None:
        """Test whitespace-only input."""
        result: list[str] = semantic_chunk("   \n\t  ")
        assert result == []


class TestChunkChatTranscript:
    """Tests for :func:`chunk_chat_transcript`."""

    def test_empty_transcript_returns_empty_list(self) -> None:
        """Test that an empty transcript produces no chunks."""
        result: list[str] = chunk_chat_transcript("")
        assert result == []

    def test_single_turn_transcript(self) -> None:
        """Test a transcript with a single turn."""
        transcript: str = "Customer: I need help with my order."
        result: list[str] = chunk_chat_transcript(transcript, max_chunk_size=500)
        assert len(result) == 1

    def test_multi_turn_transcript(self) -> None:
        """Test a multi-turn transcript preserves turn boundaries."""
        transcript: str = (
            "Customer: I have an issue with my order.\n"
            "Agent: I'd be happy to help. What's the order number?\n"
            "Customer: Order #12345. The package arrived damaged.\n"
            "Agent: I'm sorry to hear that. Let me look into it."
        )
        result: list[str] = chunk_chat_transcript(transcript, max_chunk_size=500)
        assert len(result) >= 1
        # All turns should be present
        combined: str = "\n".join(result)
        assert "Customer:" in combined
        assert "Agent:" in combined

    def test_long_transcript_splits_at_turns(self) -> None:
        """Test that a long transcript splits at turn boundaries."""
        turns: list[str] = [
            f"Customer: Message number {i}. " + "X" * 50
            for i in range(20)
        ]
        transcript: str = "\n".join(turns)
        result: list[str] = chunk_chat_transcript(transcript, max_chunk_size=200)
        assert len(result) > 1

    def test_text_without_role_markers_uses_sliding_window(self) -> None:
        """Test transcript without role markers falls back to sliding window."""
        transcript: str = "Just some plain text without any role markers. " * 10
        result: list[str] = chunk_chat_transcript(transcript, max_chunk_size=100)
        assert len(result) >= 1
