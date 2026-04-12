"""Centralised sub-agent LLM singleton.

Every module that needs a lightweight, fast LLM (SQL generation, query
rewriting, classification, memory summarisation) imports the shared
instance from here.  This avoids creating 3-4 duplicate
``ChatGoogleGenerativeAI`` instances with identical configurations.

Thread-safety
-------------
Uses double-checked locking so the hot path (after first init) is
lock-free.
"""

from __future__ import annotations

import logging
import threading

from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import settings

logger = logging.getLogger(__name__)

_sub_llm: ChatGoogleGenerativeAI | None = None
_sub_llm_lock = threading.Lock()


def get_sub_llm(
    max_output_tokens: int | None = None,
) -> ChatGoogleGenerativeAI:
    """Return a shared sub-agent LLM, creating it on first call.

    The singleton is configured with ``settings.sub_agent_model`` at
    temperature 0 for deterministic output.  Callers that need a
    *different* ``max_output_tokens`` (e.g. the Tavily query rewriter
    only needs 100 tokens) should pass the override here — but the
    underlying model instance is shared.

    .. note::
       ``max_output_tokens`` only affects the *first* call that creates
       the singleton.  Subsequent calls reuse the existing instance.  If
       you truly need a separate token budget, create a local LLM.

    Args:
        max_output_tokens: Override for ``max_output_tokens``.  Defaults
            to ``settings.sub_agent_max_tokens``.

    Returns:
        Shared :class:`ChatGoogleGenerativeAI` instance.
    """
    global _sub_llm
    if _sub_llm is not None:
        return _sub_llm
    with _sub_llm_lock:
        if _sub_llm is None:
            tokens = max_output_tokens or settings.sub_agent_max_tokens
            _sub_llm = ChatGoogleGenerativeAI(
                model=settings.sub_agent_model,
                google_api_key=settings.google_api_key,
                temperature=0.0,
                max_output_tokens=tokens,
            )
            logger.info(
                "Sub-agent LLM initialised — model=%s max_tokens=%d",
                settings.sub_agent_model,
                tokens,
            )
    return _sub_llm
