"""Session memory factory using LangChain ConversationBufferMemory.

Provides a factory function that creates memory instances. The AgentExecutor uses this
memory to maintain cross-turn context within an analyst session.
"""

from __future__ import annotations

import logging

from langchain_classic.memory import ConversationBufferMemory
from langchain_core.caches import BaseCache  # noqa: F401 — required for Pydantic v2 forward-ref resolution
from langchain_core.callbacks.manager import Callbacks  # noqa: F401 — required for Pydantic v2 forward-ref

from src.config import settings

logger = logging.getLogger(__name__)

def create_memory() -> ConversationBufferMemory:
    """Create a fresh ConversationBufferMemory instance.

    Returns:
        A configured :class:`ConversationBufferMemory` ready to
        be passed to an ``AgentExecutor``.
    """
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="output",
    )

    logger.info("ConversationBufferMemory created (bypassed summarization limit)")
    return memory

