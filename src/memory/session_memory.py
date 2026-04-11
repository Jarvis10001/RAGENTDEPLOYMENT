"""Session memory factory using LangChain ConversationSummaryBufferMemory.

Provides a factory function that creates memory instances backed by
Google Gemini Flash for summarisation.  The AgentExecutor uses this
memory to maintain cross-turn context within an analyst session.
"""

from __future__ import annotations

import logging

from langchain.memory import ConversationSummaryBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import settings

logger = logging.getLogger(__name__)


def create_memory() -> ConversationSummaryBufferMemory:
    """Create a fresh ConversationSummaryBufferMemory instance.

    Uses Gemini Flash as the summarisation LLM (cheaper and faster than
    the primary model) to automatically trim older conversational turns
    when the token budget is exceeded.

    Returns:
        A configured :class:`ConversationSummaryBufferMemory` ready to
        be passed to an ``AgentExecutor``.
    """
    sub_llm = ChatGoogleGenerativeAI(
        model=settings.sub_agent_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
        max_output_tokens=settings.sub_agent_max_tokens,
        convert_system_message_to_human=True,
    )

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
