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
from typing import Any
from google.api_core.retry import Retry

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable

from src.config import settings

logger = logging.getLogger(__name__)

_sub_llm: Runnable | None = None
_sub_llm_lock = threading.Lock()


def extract_text(output: object) -> str:
    """Normalize Gemini output to a plain string.

    ``include_thoughts=True`` wraps the response in a list of content-block
    dicts. This extracts only the plain-text parts for tools using the sub-LLM.
    """
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        parts = [
            block.get("text", "")
            for block in output
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
        ]
        return "".join(parts).strip() or "No response generated."
    return str(output)


def get_sub_llm(
    max_output_tokens: int | None = None,
) -> Runnable:
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
            main_llm = ChatGoogleGenerativeAI(
                model=settings.sub_agent_model,
                google_api_key=settings.google_api_key,
                temperature=0.0,
                max_output_tokens=tokens,
                max_retries=0,
                timeout=120.0,
                include_thoughts=True,
            ).bind(retry=Retry(initial=0.0, maximum=0.0, multiplier=1.0, timeout=0.0))
            fallback_llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=settings.google_api_key,
                temperature=0.0,
                max_output_tokens=tokens,
                max_retries=0,
                timeout=120.0,
                include_thoughts=True,
            ).bind(retry=Retry(initial=0.0, maximum=0.0, multiplier=1.0, timeout=0.0))

            _sub_llm = main_llm.with_fallbacks(
                [fallback_llm],
                exceptions_to_handle=(Exception,)
            )
            logger.info(
                "Sub-agent LLM initialised — model=%s max_tokens=%d",
                settings.sub_agent_model,
                tokens,
            )
    return _sub_llm

