"""Singleton Supabase client with thread-safe initialisation.

Usage::

    from src.db.supabase_client import get_supabase_client
    client = get_supabase_client()
    result = client.table("orders").select("*").limit(10).execute()
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from supabase import Client, create_client

from src.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_client: Client | None = None
_lock: threading.Lock = threading.Lock()


def get_supabase_client() -> Client:
    """Return a singleton Supabase client reused across the application.

    The client is created once on first call and protected by a threading
    lock for safety under Streamlit's threaded callback model.

    Returns:
        A fully-initialised :class:`supabase.Client`.

    Raises:
        Exception: If the Supabase URL or service key is invalid or the
            connection cannot be established.
    """
    global _client
    with _lock:
        if _client is None:
            _client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_service_key,
            )
            logger.info("Supabase client initialised: %s", settings.supabase_url)
    return _client


def health_check() -> bool:
    """Run a lightweight query to verify database connectivity.

    Returns:
        ``True`` if the database is reachable, ``False`` otherwise.
    """
    try:
        client = get_supabase_client()
        client.table("customers").select("customer_id").limit(1).execute()
        logger.info("Supabase health check passed.")
        return True
    except Exception as exc:
        logger.error("Supabase health check failed: %s", exc)
        return False
