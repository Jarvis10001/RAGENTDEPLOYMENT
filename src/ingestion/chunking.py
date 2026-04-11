"""Semantic and sliding-window text chunking strategies.

Provides two chunking methods:

1. **Sliding-window** — fixed-size character windows with configurable overlap.
   Best for homogeneous text (reviews, support tickets).
2. **Semantic** — splits on sentence boundaries and groups sentences that
   are thematically related.  Uses simple heuristics (sentence length / count)
   rather than an embedding model, keeping chunking fast and local.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from src.config import get_settings

logger = logging.getLogger(__name__)

# Regex for splitting text into sentences
_SENTENCE_BOUNDARY: re.Pattern[str] = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])"
)


def sliding_window_chunk(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[str]:
    """Split text into fixed-size overlapping windows.

    Args:
        text: The input text to chunk.
        chunk_size: Maximum characters per chunk.  Defaults to the
            value from application settings.
        chunk_overlap: Characters of overlap between adjacent chunks.
            Defaults to the value from application settings.

    Returns:
        A list of text chunks.  An empty list if the input is empty.
    """
    if not text or not text.strip():
        return []

    settings = get_settings()
    size: int = chunk_size if chunk_size is not None else settings.chunk_size
    overlap: int = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    if overlap >= size:
        logger.warning(
            "chunk_overlap (%d) >= chunk_size (%d); clamping overlap to size-1.",
            overlap,
            size,
        )
        overlap = size - 1

    chunks: list[str] = []
    start: int = 0
    text_len: int = len(text)

    while start < text_len:
        end: int = min(start + size, text_len)
        chunk: str = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        # Advance by (size - overlap) to create the overlap
        start += size - overlap

    logger.info(
        "Sliding-window chunking produced %d chunks (size=%d overlap=%d).",
        len(chunks),
        size,
        overlap,
    )
    return chunks


def semantic_chunk(
    text: str,
    max_chunk_size: Optional[int] = None,
    min_sentences_per_chunk: int = 2,
) -> list[str]:
    """Split text on sentence boundaries, grouping related sentences.

    Sentences are accumulated into a chunk until the ``max_chunk_size``
    character limit is reached.  Each chunk contains at least
    ``min_sentences_per_chunk`` sentences when possible.

    Args:
        text: The input text to chunk.
        max_chunk_size: Maximum characters per chunk.  Defaults to the
            value from application settings.
        min_sentences_per_chunk: Minimum number of sentences per chunk.

    Returns:
        A list of semantically-coherent text chunks.
    """
    if not text or not text.strip():
        return []

    settings = get_settings()
    size: int = max_chunk_size if max_chunk_size is not None else settings.chunk_size

    sentences: list[str] = _split_sentences(text)
    if not sentences:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length: int = 0

    for sentence in sentences:
        sentence_len: int = len(sentence)

        # If adding this sentence would exceed size and we have enough sentences
        if (
            current_length + sentence_len > size
            and len(current_chunk) >= min_sentences_per_chunk
        ):
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(sentence)
        current_length += sentence_len + 1  # +1 for the joining space

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    logger.info(
        "Semantic chunking produced %d chunks from %d sentences (max_size=%d).",
        len(chunks),
        len(sentences),
        size,
    )
    return chunks


def _split_sentences(text: str) -> list[str]:
    """Split text into individual sentences.

    Uses a regex-based sentence boundary detector that splits on
    ``[.!?]`` followed by whitespace and an uppercase letter.

    Args:
        text: Input text.

    Returns:
        A list of sentence strings, with whitespace stripped.
    """
    raw_sentences: list[str] = _SENTENCE_BOUNDARY.split(text)
    sentences: list[str] = [s.strip() for s in raw_sentences if s.strip()]
    return sentences


def chunk_chat_transcript(
    transcript: str,
    max_chunk_size: Optional[int] = None,
) -> list[str]:
    """Chunk a multi-turn chat transcript preserving turn boundaries.

    Each turn (identified by lines starting with common prefixes like
    ``"Customer:"``, ``"Agent:"``, ``"User:"``, ``"Support:"``) is kept
    intact within a chunk when possible.

    Args:
        transcript: The full chat transcript.
        max_chunk_size: Maximum characters per chunk.

    Returns:
        A list of chunks preserving turn boundaries.
    """
    if not transcript or not transcript.strip():
        return []

    settings = get_settings()
    size: int = max_chunk_size if max_chunk_size is not None else settings.chunk_size

    turn_pattern: re.Pattern[str] = re.compile(
        r"^(Customer|Agent|User|Support|Bot|System)\s*:", re.MULTILINE
    )

    # Split on turn boundaries, keeping the delimiter
    parts: list[str] = turn_pattern.split(transcript)

    # Reassemble turns: parts come as [pre, role, content, role, content, ...]
    turns: list[str] = []
    if parts and not turn_pattern.match(parts[0]):
        # There's text before the first role marker
        if parts[0].strip():
            turns.append(parts[0].strip())
        parts = parts[1:]

    for i in range(0, len(parts) - 1, 2):
        role: str = parts[i]
        content: str = parts[i + 1] if i + 1 < len(parts) else ""
        turn_text: str = f"{role}: {content.strip()}"
        if turn_text.strip():
            turns.append(turn_text)

    if not turns:
        return sliding_window_chunk(transcript, chunk_size=size)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length: int = 0

    for turn in turns:
        turn_len: int = len(turn)

        if current_length + turn_len > size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(turn)
        current_length += turn_len + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    logger.info(
        "Chat transcript chunking produced %d chunks from %d turns.",
        len(chunks),
        len(turns),
    )
    return chunks
