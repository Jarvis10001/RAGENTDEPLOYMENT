"""Embed text and upsert into Supabase vector tables.

Handles the ingestion pipeline:

1. Chunk raw text using strategies from :mod:`src.ingestion.chunking`.
2. Embed each chunk with ``sentence-transformers/all-MiniLM-L6-v2``.
3. Upsert the (text, embedding) pairs into ``omnichannel_vectors`` or
   ``marketing_vectors`` via the Supabase client.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.config import settings
from src.db.supabase_client import get_supabase_client
from src.embeddings.encoder import encode
from src.ingestion.chunking import semantic_chunk, sliding_window_chunk

logger = logging.getLogger(__name__)

# Batch size for upsert operations
_UPSERT_BATCH_SIZE: int = 50


def embed_and_upsert_omnichannel(
    text_content: str,
    feedback_id: Optional[str] = None,
    order_id: Optional[str] = None,
    chunking_strategy: str = "semantic",
) -> int:
    """Chunk, embed, and upsert text into ``omnichannel_vectors``.

    Args:
        text_content: The raw text (review, support ticket, feedback).
        feedback_id: Optional UUID linking to the source feedback record.
        order_id: Optional UUID linking to the associated order.
        chunking_strategy: Either ``"semantic"`` or ``"sliding_window"``.

    Returns:
        The number of chunks successfully upserted.

    Raises:
        ValueError: If ``chunking_strategy`` is not recognised.
    """
    chunks: list[str] = _chunk_text(text_content, chunking_strategy)
    if not chunks:
        logger.warning("No chunks produced from input text (len=%d).", len(text_content))
        return 0

    records: list[dict[str, Any]] = []
    for chunk in chunks:
        embedding: list[float] = encode([chunk])[0]
        record: dict[str, Any] = {
            "text_content": chunk,
            "embedding": embedding,
        }
        if feedback_id:
            record["feedback_id"] = feedback_id
        if order_id:
            record["order_id"] = order_id
        records.append(record)

    upserted: int = _batch_upsert("omnichannel_vectors", records)
    logger.info(
        "Upserted %d chunks to omnichannel_vectors (feedback_id=%s order_id=%s).",
        upserted,
        feedback_id,
        order_id,
    )
    return upserted


def embed_and_upsert_marketing(
    text_content: str,
    asset_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    asset_type: Optional[str] = None,
    chunking_strategy: str = "semantic",
) -> int:
    """Chunk, embed, and upsert text into ``marketing_vectors``.

    Args:
        text_content: The raw text (ad copy, campaign brief, creative).
        asset_id: Optional identifier for the marketing asset.
        campaign_id: Optional campaign ID this asset belongs to.
        asset_type: Optional type descriptor (e.g. ``"ad_copy"``,
            ``"campaign_brief"``).
        chunking_strategy: Either ``"semantic"`` or ``"sliding_window"``.

    Returns:
        The number of chunks successfully upserted.

    Raises:
        ValueError: If ``chunking_strategy`` is not recognised.
    """
    chunks: list[str] = _chunk_text(text_content, chunking_strategy)
    if not chunks:
        logger.warning("No chunks produced from input text (len=%d).", len(text_content))
        return 0

    records: list[dict[str, Any]] = []
    for chunk in chunks:
        embedding: list[float] = encode([chunk])[0]
        record: dict[str, Any] = {
            "text_content": chunk,
            "embedding": embedding,
        }
        if asset_id:
            record["asset_id"] = asset_id
        if campaign_id:
            record["campaign_id"] = campaign_id
        if asset_type:
            record["asset_type"] = asset_type
        records.append(record)

    upserted: int = _batch_upsert("marketing_vectors", records)
    logger.info(
        "Upserted %d chunks to marketing_vectors (campaign_id=%s asset_type=%s).",
        upserted,
        campaign_id,
        asset_type,
    )
    return upserted


def _chunk_text(text: str, strategy: str) -> list[str]:
    """Chunk text using the specified strategy.

    Args:
        text: Raw input text.
        strategy: ``"semantic"`` or ``"sliding_window"``.

    Returns:
        List of text chunks.

    Raises:
        ValueError: If strategy is not recognised.
    """
    if strategy == "semantic":
        return semantic_chunk(text)
    elif strategy == "sliding_window":
        return sliding_window_chunk(text)
    else:
        raise ValueError(
            f"Unknown chunking strategy '{strategy}'. "
            f"Use 'semantic' or 'sliding_window'."
        )


def _batch_upsert(table_name: str, records: list[dict[str, Any]]) -> int:
    """Upsert records into a Supabase table in batches.

    Args:
        table_name: Target Supabase table.
        records: List of record dicts to insert.

    Returns:
        Total number of records successfully upserted.
    """
    client = get_supabase_client()
    total_upserted: int = 0

    for i in range(0, len(records), _UPSERT_BATCH_SIZE):
        batch: list[dict[str, Any]] = records[i : i + _UPSERT_BATCH_SIZE]
        try:
            response = client.table(table_name).insert(batch).execute()
            batch_count: int = len(response.data) if response.data else 0
            total_upserted += batch_count
            logger.debug(
                "Upserted batch %d-%d to %s (%d records).",
                i,
                i + len(batch),
                table_name,
                batch_count,
            )
        except Exception as exc:
            logger.error(
                "Failed to upsert batch %d-%d to %s: %s",
                i,
                i + len(batch),
                table_name,
                exc,
            )

    return total_upserted
