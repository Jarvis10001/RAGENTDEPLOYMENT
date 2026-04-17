"""Session manager — one AgentExecutor per session_id.

Sessions are stored in an in-process dict. In production this would be
backed by Redis; for the hackathon an in-memory dict is sufficient since
all requests hit a single Uvicorn worker.
"""

from __future__ import annotations

import logging
from typing import Final

from langchain_classic.agents import AgentExecutor

from src.agent.primary_agent import get_agent_executor
from src.memory.session_memory import create_memory

logger = logging.getLogger(__name__)

_MAX_SESSIONS: Final[int] = 50  # evict oldest when limit reached


class SessionManager:
    """Manages a pool of AgentExecutor instances keyed by session_id."""

    def __init__(self) -> None:
        self._sessions: dict[str, AgentExecutor] = {}
        # Track insertion order for LRU-style eviction
        self._order: list[str] = []

    def get_or_create(self, session_id: str) -> AgentExecutor:
        """Return an existing executor or create a new one.

        Args:
            session_id: Browser-generated UUID identifying the conversation.

        Returns:
            A fully configured :class:`AgentExecutor` with its own memory.
        """
        if session_id not in self._sessions:
            # Evict oldest if at capacity
            if len(self._sessions) >= _MAX_SESSIONS:
                oldest = self._order.pop(0)
                del self._sessions[oldest]
                logger.info("Evicted oldest session: %s", oldest)

            logger.info("Creating new AgentExecutor for session: %s", session_id)
            memory = create_memory()
            executor = get_agent_executor(memory=memory)
            self._sessions[session_id] = executor
            self._order.append(session_id)
        else:
            logger.debug("Reusing existing AgentExecutor for session: %s", session_id)

        return self._sessions[session_id]

    def clear(self, session_id: str) -> bool:
        """Remove a session and its memory.

        Args:
            session_id: The session to clear.

        Returns:
            ``True`` if the session existed and was cleared, ``False`` otherwise.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._order:
                self._order.remove(session_id)
            logger.info("Cleared session: %s", session_id)
            return True
        return False

    @property
    def active_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)


# Module-level singleton used by the FastAPI app
session_manager = SessionManager()
