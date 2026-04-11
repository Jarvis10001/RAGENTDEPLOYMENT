"""Primary Agent — LangChain AgentExecutor with ReAct pattern.

Builds the orchestrator agent using ``create_react_agent()`` and wraps it
in ``AgentExecutor``.  The agent delegates all work to five specialised
tools and synthesises their outputs into a coherent final answer.

Design decisions
----------------
* Primary LLM: Gemini Pro — highest reasoning quality, used for the
  Thought/Act/Observe loop.
* Sub-agent LLM: Gemini Flash — fast and cheap, used for SQL generation
  and conversation summarisation.
* Memory: ConversationSummaryBufferMemory — keeps recent turns verbatim
  and compresses older history into a rolling summary via Gemini Flash.
* max_iterations=8: Sufficient for multi-tool root-cause questions while
  preventing infinite loops. Adjust via env if needed.
"""

from __future__ import annotations

import logging
from typing import Final

from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationSummaryBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import settings
from src.memory.session_memory import create_memory
from src.tools.rag_tools import marketing_content_search, omnichannel_feedback_search
from src.tools.sql_tools import ecommerce_analytics_query, ecommerce_sql_query
from src.tools.tavily_tool import web_market_search

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
_MAX_ITERATIONS: Final[int] = 8

# ── System prompt injected into the ReAct prompt ─────────────────────
_SYSTEM_PREFIX: Final[str] = """You are an E-commerce Intelligence Analyst with access \
to five specialised tools. You MUST use tools to answer every question — \
never answer from your own training knowledge alone.

Tool selection rules:
• Metrics, revenue, costs, orders, profit margins, split shipments, CLV, \
CAC, campaigns → ecommerce_sql_query or ecommerce_analytics_query (or both).
• Customer sentiment, complaints, reviews, feedback, support tickets, \
"what are customers saying" → omnichannel_feedback_search.
• Campaign messaging, ad copy, marketing strategy, brand positioning \
→ marketing_content_search.
• Current market data, industry benchmarks, competitor intelligence, \
anything not in the database → web_market_search.
• Root-cause questions ("why did X happen?") → call at least one SQL tool \
AND omnichannel_feedback_search, then synthesise both.

After receiving tool results, structure every final answer as:
  **Finding** → **Evidence** (cite numbers and quote customer phrases verbatim) \
→ **Recommended Action**

Always cite source URLs when using web search results."""


def get_agent_executor(
    memory: ConversationSummaryBufferMemory | None = None,
) -> AgentExecutor:
    """Build and return a fully configured AgentExecutor.

    This function is designed to be called once per Streamlit session.
    Each call creates a new primary LLM instance but reuses the shared
    sub-agent singletons in sql_tools and tavily_tool.

    Args:
        memory: Optional pre-built memory instance. If ``None``, a fresh
                :class:`ConversationSummaryBufferMemory` is created via
                :func:`~src.memory.session_memory.create_memory`.

    Returns:
        :class:`AgentExecutor` ready for ``.invoke()`` or ``.stream()`` calls.
    """
    # ── Primary LLM (best reasoning quality — used for ReAct loop) ───
    primary_llm = ChatGoogleGenerativeAI(
        model=settings.primary_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
        max_output_tokens=settings.primary_max_tokens,
    )

    # ── Memory ────────────────────────────────────────────────────────
    if memory is None:
        memory = create_memory()

    # ── Ordered tool list (order affects tool description presentation) ─
    tools = [
        omnichannel_feedback_search,
        marketing_content_search,
        ecommerce_sql_query,
        ecommerce_analytics_query,
        web_market_search,
    ]

    # ── Fetch and customise the standard ReAct-chat prompt ───────────
    react_prompt = hub.pull("hwchase17/react-chat")
    _inject_system_prefix(react_prompt)

    # ── Wire agent and executor ───────────────────────────────────────
    agent = create_react_agent(
        llm=primary_llm,
        tools=tools,
        prompt=react_prompt,
    )

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        max_iterations=_MAX_ITERATIONS,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        verbose=settings.debug,
    )

    logger.info(
        "AgentExecutor ready — model=%s tools=%s max_iterations=%d",
        settings.primary_model,
        [t.name for t in tools],
        _MAX_ITERATIONS,
    )

    return executor


def _inject_system_prefix(prompt: object) -> None:
    """Prepend ``_SYSTEM_PREFIX`` into the ReAct prompt template in-place.

    Handles both ``ChatPromptTemplate`` (has ``.messages``) and plain
    ``PromptTemplate`` (has ``.template`` directly).

    Args:
        prompt: The pulled LangChain hub prompt object to mutate.
    """
    if hasattr(prompt, "messages") and prompt.messages:
        first = prompt.messages[0]
        if hasattr(first, "prompt") and hasattr(first.prompt, "template"):
            first.prompt.template = _SYSTEM_PREFIX + "\n\n" + first.prompt.template
            return

    if hasattr(prompt, "template"):
        prompt.template = _SYSTEM_PREFIX + "\n\n" + prompt.template
