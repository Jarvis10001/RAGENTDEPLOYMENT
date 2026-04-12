"""Primary Agent — LangChain AgentExecutor with ReAct pattern.

Builds the orchestrator agent using ``create_react_agent()`` and wraps it
in ``AgentExecutor``.  The agent delegates all work to five specialised
tools and synthesises their outputs into a coherent final answer.

A **query classifier** pre-processes every user question to produce a
structured intent, eliminating non-deterministic tool selection. When a
query is ambiguous, the classifier returns a clarifying question instead
of passing the ambiguous input to the ReAct loop.

Design decisions
----------------
* Primary LLM: Gemini Pro — highest reasoning quality, used for the
  Thought/Act/Observe loop.
* Sub-agent LLM: Gemini Flash — fast and cheap, used for SQL generation,
  conversation summarisation, and query classification.
* Memory: ConversationSummaryBufferMemory — keeps recent turns verbatim
  and compresses older history into a rolling summary via Gemini Flash.
* max_iterations=8: Sufficient for multi-tool root-cause questions while
  preventing infinite loops. Adjust via env if needed.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Final

from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationSummaryBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI

from src.cache import response_cache as cache
from src.config import settings
from src.db.supabase_client import health_check
from src.memory.session_memory import create_memory
from src.tools.rag_tools import marketing_content_search, omnichannel_feedback_search
from src.tools.sql_tools import ecommerce_analytics_query, ecommerce_sql_query
from src.tools.tavily_tool import web_market_search

from src.agent.query_classifier import (
    QueryIntent,
    build_enhanced_input,
    classify_query,
    needs_clarification,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
_MAX_ITERATIONS: Final[int] = 8

# ── System prompt injected into the ReAct prompt ─────────────────────
_SYSTEM_PREFIX: Final[str] = """You are an E-commerce Intelligence Analyst with access \
to five specialised tools. You MUST use tools to answer every question — \
never answer from your own training knowledge alone.

IMPORTANT — Deterministic Execution:
When the input contains TOOL GUIDANCE, you MUST follow the specified tool \
order exactly. Do NOT skip any listed tool. Do NOT call tools not listed \
unless the results from the guided tools are insufficient.

When the input contains PRIMARY METRIC, focus your queries and analysis \
on that specific metric. Use it as the ORDER BY / aggregation target.

Tool selection rules (used when NO tool guidance is provided):
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

When using search tools (omnichannel_feedback_search, \
marketing_content_search, web_market_search), pass the exact QUESTION \
provided in the input as the search string for optimal semantic retrieval.

After receiving tool results, structure every final answer as:
  **Finding** → **Evidence** (cite numbers and quote customer phrases verbatim) \
→ **Recommended Action**

Always cite source URLs when using web search results.

CRITICAL INSTRUCTION FOR GEMINI MODELS: 
You must strictly adhere to the ReAct format. 
1. If you need to use a tool, you MUST write "Action: <exact_tool_name>" followed exactly by "Action Input: <input>". Do NOT invent tool names like "Ecommerce Sql Query". Use the exact snake_case tool name provided in the list below.
2. If you are ready to give the final answer, you MUST write "Final Answer: <your answer>".
Failure to follow this exact format will break the system."""


def get_agent_executor(
    memory: ConversationSummaryBufferMemory | None = None,
) -> AgentExecutor:
    """Build and return a fully configured AgentExecutor.

    This function is designed to be called once per Streamlit session.
    Each call creates a new primary LLM instance but reuses the shared
    sub-agent singleton from :mod:`src.llm`.

    Also runs a lightweight database health check on first build to
    surface connection issues immediately rather than on the first query.

    Args:
        memory: Optional pre-built memory instance. If ``None``, a fresh
                :class:`ConversationSummaryBufferMemory` is created via
                :func:`~src.memory.session_memory.create_memory`.

    Returns:
        :class:`AgentExecutor` ready for ``.invoke()`` or ``.stream()`` calls.
    """
    # ── Health check — verify DB connectivity early ───────────────────
    if not health_check():
        logger.warning(
            "Supabase health check failed — DB-dependent tools may not work."
        )

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


def run_with_classifier(
    executor: AgentExecutor,
    question: str,
    chat_context: str = "",
) -> dict[str, Any]:
    """Run a user question through the classifier → agent pipeline.

    This is the main entry point for processing user queries.  It:
    1. Classifies the query to produce a :class:`QueryIntent`.
    2. If the query needs clarification, returns immediately with the
       clarifying question (no tool calls made).
    3. Otherwise, builds an enhanced input with tool guidance and
       invokes the AgentExecutor.

    The clarification mechanism is fully preserved — when the classifier
    detects ambiguity (e.g. "best campaigns" without specifying a metric),
    it returns a ``clarifying_question`` which is surfaced to the user
    as a chat message.  The user's follow-up is then combined with the
    original question and re-classified.

    **Cache behaviour**: The response-level cache includes a hash of the
    ``chat_context`` so that context-dependent queries (e.g. "what about
    last month?") are not served stale cached answers from a different
    conversation context.  Clarification queries bypass the cache entirely.

    Args:
        executor: The configured :class:`AgentExecutor`.
        question: The user's raw question.
        chat_context: Optional recent chat history for classification context.

    Returns:
        Dict with keys:
        - ``"output"``: The agent's answer or clarifying question.
        - ``"needs_clarification"``: ``True`` if the output is a question.
        - ``"intent"``: The :class:`QueryIntent` for UI display.
        - ``"intermediate_steps"``: Tool call details (empty if clarifying).
    """
    # Step 1: Classify the query
    try:
        intent = classify_query(question, chat_context)
    except Exception as exc:
        logger.warning("Classifier failed (%s), falling through to agent.", exc)
        intent = QueryIntent(
            intent_type="multi_tool",
            primary_metric=None,
            required_tools=[],
            missing_params=[],
            clarifying_question=None,
            rewritten_query=question,
            confidence="low",
        )

    # Step 2: Check if clarification is needed — return immediately
    # (no cache, no tool calls — just ask the user)
    if needs_clarification(intent):
        logger.info("Returning clarifying question to user.")
        if executor.memory is not None:
            executor.memory.save_context({"input": question}, {"output": intent.clarifying_question})
        return {
            "output": intent.clarifying_question,
            "needs_clarification": True,
            "intent": intent,
            "intermediate_steps": [],
        }

    # Step 3: Build enhanced input with tool guidance
    enhanced_input = build_enhanced_input(question, intent)

    # Step 4: Check response-level determinism cache
    # Key includes chat_context hash so conversations with different
    # history don't return stale cached answers.
    context_hash = hashlib.sha256(
        chat_context[:500].encode()
    ).hexdigest()[:16] if chat_context else "no_ctx"

    response_cache_key = cache.make_key(
        "agent_response",
        intent.rewritten_query,
        intent.required_tools,
        intent.primary_metric,
        context_hash,
    )
    cached_output = cache.get(response_cache_key)
    if cached_output is not None:
        logger.info("Response-level cache hit — returning deterministic answer.")
        if executor.memory is not None:
            executor.memory.save_context({"input": question}, {"output": cached_output})
        return {
            "output": cached_output,
            "needs_clarification": False,
            "intent": intent,
            "intermediate_steps": [],  # Not available from cache
        }

    # Step 5: Invoke the agent
    # Do NOT pass chat_history — let Memory auto-load it via memory_key.
    # Passing an empty list would override the memory's stored history.
    result = executor.invoke({"input": enhanced_input})

    output = result.get("output", "No response generated.")

    # Step 6: Cache the response for determinism
    cache.set(response_cache_key, output, ttl=settings.cache_ttl_seconds)

    return {
        "output": output,
        "needs_clarification": False,
        "intent": intent,
        "intermediate_steps": result.get("intermediate_steps", []),
    }


def stream_with_classifier(
    executor: AgentExecutor,
    question: str,
    chat_context: str = "",
):
    """Synchronous generator version of run_with_classifier for live streaming."""
    # Step 1: Classify the query
    try:
        intent = classify_query(question, chat_context)
    except Exception as exc:
        logger.warning("Classifier failed (%s), falling through to agent.", exc)
        intent = QueryIntent(
            intent_type="multi_tool", primary_metric=None, required_tools=[],
            missing_params=[], clarifying_question=None, rewritten_query=question, confidence="low"
        )

    # Step 2: Clarification
    if needs_clarification(intent):
        if executor.memory is not None:
            executor.memory.save_context({"input": question}, {"output": intent.clarifying_question})
        yield {"type": "clarification", "output": intent.clarifying_question, "intent": intent}
        return

    # Step 3: Cache
    enhanced_input = build_enhanced_input(question, intent)
    context_hash = hashlib.sha256(chat_context[:500].encode()).hexdigest()[:16] if chat_context else "no_ctx"
    response_cache_key = cache.make_key(
        "agent_response", intent.rewritten_query, intent.required_tools, intent.primary_metric, context_hash
    )
    
    cached_output = cache.get(response_cache_key)
    if cached_output is not None:
        if executor.memory is not None:
            executor.memory.save_context({"input": question}, {"output": cached_output})
        yield {"type": "cache_hit", "output": cached_output, "intent": intent}
        return

    yield {"type": "intent", "intent": intent}

    # Step 4: Stream the agent loop
    final_output = "No response generated."
    for chunk in executor.stream({"input": enhanced_input}):
        yield {"type": "stream_chunk", "chunk": chunk}
        if "output" in chunk:
            final_output = chunk["output"]

    # Step 5: Save to cache
    cache.set(response_cache_key, final_output, ttl=settings.cache_ttl_seconds)


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
