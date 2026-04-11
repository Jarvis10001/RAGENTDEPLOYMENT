"""Disk-backed response cache using ``diskcache``.

Provides ``make_key``, ``get``, and ``set_value`` helpers that all tool modules
use to avoid redundant LLM / Supabase calls within the configured TTL.
Cache failures are always non-fatal — the tool simply re-executes the query.

Thread-safety
-------------
``diskcache.Cache`` is process-safe and thread-safe for reads. The singleton
creation here is additionally guarded by a ``threading.Lock`` to ensure the
cache directory is created exactly once even under high concurrency.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from typing import Any

import diskcache

from src.config import settings

logger = logging.getLogger(__name__)

_cache: diskcache.Cache | None = None
_cache_lock = threading.Lock()


def _get_cache() -> diskcache.Cache:
    """Return the shared ``diskcache.Cache`` instance, creating it on first call.

    Thread-safe via double-checked locking.

    Returns:
        Open :class:`diskcache.Cache` pointing at ``settings.cache_dir``.
    """
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                os.makedirs(settings.cache_dir, exist_ok=True)
                _cache = diskcache.Cache(
                    settings.cache_dir,
                    size_limit=512 * 1024 * 1024,  # 512 MiB limit
                )
                logger.info("diskcache initialised at %r", settings.cache_dir)
    return _cache


def make_key(namespace: str, *args: Any) -> str:
    """Build a deterministic SHA-256 cache key from a namespace and arguments.

    Args:
        namespace: Logical group name, e.g. ``"omnichannel"``, ``"sql"``.
        *args: Arbitrary positional values that distinguish cache entries.
               Any type is accepted; non-serialisable values are stringified.

    Returns:
        64-character hex-encoded SHA-256 digest.
    """
    payload = json.dumps(
        {"ns": namespace, "args": args},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def get(key: str) -> Any | None:
    """Read a cached value.

    Args:
        key: Cache key produced by :func:`make_key`.

    Returns:
        The cached value, or ``None`` if caching is disabled, the key is
        absent, or a read error occurs (non-fatal).
    """
    if not settings.cache_enabled:
        return None
    try:
        value = _get_cache().get(key)
        return value  # diskcache returns None for missing keys
    except Exception as exc:
        logger.warning("Cache read failed (non-fatal): %s", exc)
        return None


def set_value(key: str, value: Any, ttl: int | None = None) -> None:
    """Write a value to the cache with an optional TTL.

    Named ``set_value`` (not ``set``) to avoid shadowing the Python built-in
    in calling modules that do ``from src.cache import response_cache as cache``.

    Args:
        key: Cache key produced by :func:`make_key`.
        value: JSON-serialisable value to store.
        ttl: Time-to-live in seconds. Falls back to ``settings.cache_ttl_seconds``
             when ``None``.
    """
    if not settings.cache_enabled:
        return
    try:
        expire = ttl if ttl is not None else settings.cache_ttl_seconds
        _get_cache().set(key, value, expire=expire)
    except Exception as exc:
        logger.warning("Cache write failed (non-fatal): %s", exc)


# ── Compatibility alias kept so existing call-sites using .set() still work ──
set = set_value
