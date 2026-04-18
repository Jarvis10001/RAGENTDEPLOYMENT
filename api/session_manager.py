"""Session manager — one AgentExecutor per (session_id, mode) pair.

Sessions are stored in an in-process dict. In production this would be
backed by Redis; for the hackathon an in-memory dict is sufficient since
all requests hit a single Uvicorn worker.

Each session can have up to two executors (fast and thinking), each with
its own memory so conversation context is preserved independently per mode.
"""

from __future__ import annotations

import logging
from typing import Final, Literal

from langchain_classic.agents import AgentExecutor

from src.agent.primary_agent import get_agent_executor
from src.memory.session_memory import create_memory

logger = logging.getLogger(__name__)

_MAX_SESSIONS: Final[int] = 50  # evict oldest when limit reached


class SessionManager:
    """Manages a pool of AgentExecutor instances keyed by (session_id, mode)."""

    def __init__(self) -> None:
        self._sessions: dict[str, AgentExecutor] = {}
        # Track insertion order for LRU-style eviction
        self._order: list[str] = []

    def _make_key(self, session_id: str, mode: str) -> str:
        """Create a composite cache key from session_id and mode."""
        return f"{session_id}::{mode}"

    def get_or_create(
        self,
        session_id: str,
        mode: Literal["fast", "thinking"] = "fast",
    ) -> AgentExecutor:
        """Return an existing executor or create a new one.

        Args:
            session_id: Browser-generated UUID identifying the conversation.
            mode: Model mode — 'fast' or 'thinking'.

        Returns:
            A fully configured :class:`AgentExecutor` with its own memory.
        """
        key = self._make_key(session_id, mode)

        if key not in self._sessions:
            # Evict oldest if at capacity
            if len(self._sessions) >= _MAX_SESSIONS:
                oldest = self._order.pop(0)
                del self._sessions[oldest]
                logger.info("Evicted oldest session: %s", oldest)

            logger.info(
                "Creating new AgentExecutor for session=%s mode=%s",
                session_id, mode,
            )
            memory = create_memory()
            executor = get_agent_executor(memory=memory, mode=mode)
            self._sessions[key] = executor
            self._order.append(key)
        else:
            logger.debug(
                "Reusing existing AgentExecutor for session=%s mode=%s",
                session_id, mode,
            )

        return self._sessions[key]

    def clear(self, session_id: str) -> bool:
        """Remove all executors (fast + thinking) for a session.

        Args:
            session_id: The session to clear.

        Returns:
            ``True`` if any executors existed and were cleared.
        """
        cleared = False
        for mode in ("fast", "thinking"):
            key = self._make_key(session_id, mode)
            if key in self._sessions:
                del self._sessions[key]
                if key in self._order:
                    self._order.remove(key)
                cleared = True
        if cleared:
            logger.info("Cleared session: %s", session_id)
        return cleared

    @property
    def active_count(self) -> int:
        """Number of active executor instances."""
        return len(self._sessions)


# Module-level singleton used by the FastAPI app
session_manager = SessionManager()
