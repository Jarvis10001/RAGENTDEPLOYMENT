"""Singleton Supabase client with connection pooling.

Usage::

    from src.db.supabase_client import get_supabase_client
    client = get_supabase_client()
    result = client.table("orders").select("*").limit(10).execute()
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from supabase import Client, create_client

from src.config import get_settings

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)

_POOL_SIZE: int = 5  # kept small — Supabase manages pooling server-side


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a singleton Supabase client reused across the application.

    The client is created once on first call and cached for the process
    lifetime via :func:`functools.lru_cache`.  Connection pooling is
    handled by Supabase's built-in PgBouncer on the server side; this
    function avoids creating redundant client instances on our end.

    Returns:
        A fully-initialised :class:`supabase.Client`.

    Raises:
        Exception: If the Supabase URL or service key is invalid or the
            connection cannot be established.
    """
    settings: Settings = get_settings()
    logger.info(
        "Creating Supabase client for %s (pool_size=%d)",
        settings.supabase_url,
        _POOL_SIZE,
    )
    client: Client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key,
    )
    logger.info("Supabase client initialised successfully.")
    return client


def health_check() -> bool:
    """Run a lightweight query to verify database connectivity.

    Returns:
        ``True`` if the database is reachable, ``False`` otherwise.
    """
    try:
        client = get_supabase_client()
        # A lightweight RPC or simple select to verify connectivity
        client.table("customers").select("customer_id").limit(1).execute()
        logger.info("Supabase health check passed.")
        return True
    except Exception as exc:
        logger.error("Supabase health check failed: %s", exc)
        return False
