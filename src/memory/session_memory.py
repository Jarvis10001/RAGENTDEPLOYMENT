"""Session memory factory using LangChain ConversationSummaryBufferMemory.

Provides a factory function that creates memory instances backed by
Google Gemini Flash for summarisation.  The AgentExecutor uses this
memory to maintain cross-turn context within an analyst session.
"""

from __future__ import annotations

import logging

from langchain.memory import ConversationSummaryBufferMemory

# Fix Pydantic v2 forward-reference resolution for BaseCache.
# See: https://errors.pydantic.dev/2.12/u/class-not-fully-defined
ConversationSummaryBufferMemory.model_rebuild()

from src.config import settings
from src.llm import get_sub_llm

logger = logging.getLogger(__name__)


def create_memory() -> ConversationSummaryBufferMemory:
    """Create a fresh ConversationSummaryBufferMemory instance.

    Uses the shared sub-agent LLM (Gemini Flash) for summarisation,
    keeping memory lightweight while automatically trimming older
    conversational turns when the token budget is exceeded.

    Returns:
        A configured :class:`ConversationSummaryBufferMemory` ready to
        be passed to an ``AgentExecutor``.
    """
    sub_llm = get_sub_llm()

    memory = ConversationSummaryBufferMemory(
        llm=sub_llm,
        max_token_limit=settings.memory_max_token_limit,
        memory_key="chat_history",
        return_messages=True,
        output_key="output",
    )

    logger.info(
        "ConversationSummaryBufferMemory created — max_tokens=%d model=%s",
        settings.memory_max_token_limit,
        settings.sub_agent_model,
    )
    return memory
