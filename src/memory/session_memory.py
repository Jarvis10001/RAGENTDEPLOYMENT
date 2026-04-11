"""Session memory wrapper using LangChain ConversationSummaryBufferMemory.

Provides cross-turn session context so the diagnostic crew can reference
previous questions and findings within the same analyst session.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain.memory import ConversationSummaryBufferMemory
from langchain_community.chat_models import ChatLiteLLM

from src.config import get_settings

logger = logging.getLogger(__name__)


class SessionMemory:
    """Wrapper around LangChain's ConversationSummaryBufferMemory.

    Maintains a running summary of the conversation, automatically
    trimming older turns when the token budget is exceeded.

    Attributes:
        _memory: The underlying LangChain memory instance.
    """

    def __init__(self, session_id: str = "default") -> None:
        """Initialise a session memory instance.

        Uses ChatLiteLLM to route through the same Groq provider as the
        rest of the pipeline, avoiding a separate Mistral dependency.

        Args:
            session_id: Unique identifier for this analyst session.
        """
        settings = get_settings()

        llm = ChatLiteLLM(
            model=settings.router_model_name,  # fast 8B model for summarization
            temperature=0.0,
            max_tokens=512,
        )

        self._memory: ConversationSummaryBufferMemory = (
            ConversationSummaryBufferMemory(
                llm=llm,
                max_token_limit=settings.memory_max_token_limit,
                memory_key="chat_history",
                return_messages=True,
            )
        )
        self._session_id: str = session_id
        logger.info(
            "SessionMemory initialised — session=%s max_tokens=%d",
            session_id,
            settings.memory_max_token_limit,
        )

    def add_interaction(self, user_input: str, agent_output: str) -> None:
        """Record a user question and the agent's response.

        Args:
            user_input: The analyst's question.
            agent_output: The system's response (typically the executive summary).
        """
        self._memory.save_context(
            {"input": user_input},
            {"output": agent_output},
        )
        logger.debug(
            "Saved interaction to session %s (input_len=%d output_len=%d).",
            self._session_id,
            len(user_input),
            len(agent_output),
        )

    def get_context(self) -> str:
        """Retrieve the conversation context as a formatted string.

        Returns:
            A string containing the summarised conversation history.
        """
        memory_vars: dict[str, Any] = self._memory.load_memory_variables({})
        messages = memory_vars.get("chat_history", [])

        if not messages:
            return "No previous conversation context."

        context_parts: list[str] = []
        for msg in messages:
            role: str = getattr(msg, "type", "unknown")
            content: str = getattr(msg, "content", str(msg))
            context_parts.append(f"[{role}] {content}")

        context: str = "\n".join(context_parts)
        logger.debug(
            "Retrieved context for session %s (length=%d chars).",
            self._session_id,
            len(context),
        )
        return context

    def clear(self) -> None:
        """Clear all conversation history for this session."""
        self._memory.clear()
        logger.info("Cleared session memory for %s.", self._session_id)

    @property
    def session_id(self) -> str:
        """Return the session identifier.

        Returns:
            The session ID string.
        """
        return self._session_id
