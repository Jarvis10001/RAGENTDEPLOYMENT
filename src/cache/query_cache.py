"""Query-level cache for diagnostic reports.

Stores final reports keyed by a normalized query hash so repeated questions
can return instantly without calling upstream LLM providers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

from src.models.diagnostic_report import DiagnosticReport

logger = logging.getLogger(__name__)


class QueryCache:
    """Persistent SQLite cache with TTL eviction for report reuse."""

    def __init__(self, db_path: str, ttl_seconds: int, enabled: bool = True) -> None:
        self._enabled = enabled
        self._ttl_seconds = ttl_seconds
        self._db_path = Path(db_path)

        if not self._enabled:
            return

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def get(self, query: str) -> Optional[DiagnosticReport]:
        """Return a cached report if present and not expired."""
        if not self._enabled:
            return None

        normalized = _normalize_query(query)
        key = _hash_query(normalized)

        now = int(time.time())
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT report_json, created_at FROM query_cache WHERE query_hash = ?",
                (key,),
            ).fetchone()

            if row is None:
                return None

            report_json, created_at = row
            if now - int(created_at) > self._ttl_seconds:
                conn.execute("DELETE FROM query_cache WHERE query_hash = ?", (key,))
                conn.commit()
                logger.info("Cache expired for query hash %s", key)
                return None

            try:
                payload = json.loads(report_json)
                return DiagnosticReport(**payload)
            except Exception as exc:
                logger.warning("Failed to decode cached report (%s). Evicting key=%s", exc, key)
                conn.execute("DELETE FROM query_cache WHERE query_hash = ?", (key,))
                conn.commit()
                return None

    def set(self, query: str, report: DiagnosticReport) -> None:
        """Persist or update a cached report for a query."""
        if not self._enabled:
            return

        normalized = _normalize_query(query)
        key = _hash_query(normalized)
        created_at = int(time.time())
        report_json = report.model_dump_json()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO query_cache (query_hash, normalized_query, report_json, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(query_hash)
                DO UPDATE SET
                    normalized_query = excluded.normalized_query,
                    report_json = excluded.report_json,
                    created_at = excluded.created_at
                """,
                (key, normalized, report_json, created_at),
            )
            conn.commit()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    normalized_query TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_query_cache_created_at ON query_cache(created_at)"
            )
            conn.commit()


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _hash_query(normalized_query: str) -> str:
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
