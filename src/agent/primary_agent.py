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
* Memory: ConversationBufferMemory — keeps recent turns verbatim
  without summarization limits offline.
* max_iterations=3: Sufficient for multi-tool root-cause questions while
  preventing infinite loops. Adjust via env if needed.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Final

# --- Monkeypatch JSON for langchain_google_genai Extra data errors ---
_original_loads = json.loads
def _patched_loads(s, *args, **kwargs):
    try:
        return _original_loads(s, *args, **kwargs)
    except json.JSONDecodeError as e:
        if isinstance(s, str) and "Extra data" in str(e):
            try:
                # Attempt to parse up to the point of extra data
                return _original_loads(s[:e.pos].strip(), *args, **kwargs)
            except Exception:
                pass
        raise
json.loads = _patched_loads

# --- Monkeypatch langchain_google_genai to fix empty tool names ---
try:
    import langchain_google_genai.chat_models as genai_models
    _original_parse_chat_history = genai_models._parse_chat_history

    def _patched_parse_chat_history(*args, **kwargs):
        system_instruction, history = _original_parse_chat_history(*args, **kwargs)
        for content in history:
            if hasattr(content, "parts"):
                for part in content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        if not part.function_response.name:
                            part.function_response.name = "unknown_tool"
                    elif hasattr(part, "function_call") and part.function_call:
                        if not part.function_call.name:
                            part.function_call.name = "unknown_tool"
        return system_instruction, history

    genai_models._parse_chat_history = _patched_parse_chat_history
except ImportError:
    pass
# ---------------------------------------------------------------------

from langchain_classic import hub
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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


def _extract_text(output: object) -> str:
    """Normalize Gemini output to a plain string.

    ``include_thoughts=True`` wraps the response in a list of content-block
    dicts.  Gemini 2.5+ may also append plain strings as continuation
    fragments after the initial dict block.  This helper captures both forms.
    """
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        parts = []
        for block in output:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
            elif isinstance(block, str):
                if block.strip():
                    parts.append(block)
        return "".join(parts).strip() or "No response generated."
    return str(output)

# ── System prompt injected into the ReAct prompt ─────────────────────
_SYSTEM_PREFIX: Final[str] = """You are an E-commerce Intelligence Analyst with access \
to five specialised tools. You MUST use tools to answer every question — \
never answer from your own training knowledge alone.

CRITICAL INSTRUCTION - MINIMISE API CALLS:
You are operating under severe API rate limits (15 Requests Per Minute). 
You MUST arrive at your Final Answer within 2 to 3 iterations. 
Do not over-think. Combine multiple queries into a single tool call if possible, 
and do not search repeatedly if the first result is mostly sufficient. 

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
"""


from google.api_core.retry import Retry

# ── Model profiles per mode ──────────────────────────────────────────
_MODE_PROFILES: dict[str, dict] = {
    "fast": {
        "model": settings.primary_model,           # gemini-3.1-flash-lite-preview
        "max_tokens": settings.primary_max_tokens,  # 2048
        "fallback": "gemini-2.5-flash",
        "suffix": "\n\nALWAYS structure your final answer beautifully with markdown: use bullet points, clear headings, and highlight key metrics. Don't mention the technical names of the tools used.",
    },
    "thinking": {
        "model": "gemini-2.5-flash",
        "max_tokens": 8192,
        "fallback": "gemini-2.0-flash",
        "suffix": (
            "\n\nYou are in DEEP THINKING mode. Your response MUST be significantly "
            "more comprehensive and detailed than a normal answer."
            "\n- Provide thorough, multi-paragraph analysis with concrete evidence."
            "\n- Include exact numbers, percentages, and verbatim customer quotes."
            "\n- Discuss strategic implications, root causes, and second-order effects."
            "\n- Present trade-offs and alternative perspectives where relevant."
            "\n- End with prioritised, actionable recommendations."
            "\nALWAYS structure your final answer beautifully with markdown: "
            "use bullet points, clear headings, tables for data, and highlight key metrics. "
            "Don't mention the technical names of the tools used. "
            "Your response should be AT LEAST twice as detailed as a quick answer would be."
        ),
    },
}

def get_agent_executor(
    memory: ConversationBufferMemory | None = None,
    mode: str = "fast",
) -> AgentExecutor:
    """Build and return a fully configured AgentExecutor.

    Args:
        memory: Optional pre-built memory instance. If ``None``, a fresh
                :class:`ConversationBufferMemory` is created via
                :func:`~src.memory.session_memory.create_memory`.
        mode: ``'fast'`` for quick answers (Flash Lite) or
              ``'thinking'`` for deeper analysis (Gemini 2.5 Flash).

    Returns:
        :class:`AgentExecutor` ready for ``.invoke()`` or ``.stream()`` calls.
    """
    profile = _MODE_PROFILES.get(mode, _MODE_PROFILES["fast"])

    # ── Health check — verify DB connectivity early ───────────────────
    if not health_check():
        logger.warning(
            "Supabase health check failed — DB-dependent tools may not work."
        )

    # ── Primary LLM — selected by mode ───────────────────────────────
    primary_llm = ChatGoogleGenerativeAI(
        model=profile["model"],
        google_api_key=settings.google_api_key,
        temperature=0.0,
        max_output_tokens=profile["max_tokens"],
        max_retries=0,
        timeout=120.0,
        include_thoughts=True,
    ).bind(retry=Retry(initial=0.0, maximum=0.0, multiplier=1.0, timeout=0.0))
    fallback_llm = ChatGoogleGenerativeAI(
        model=profile["fallback"],
        google_api_key=settings.google_api_key,
        temperature=0.0,
        max_output_tokens=profile["max_tokens"],
        max_retries=0,
        timeout=120.0,
        include_thoughts=True,
    ).bind(retry=Retry(initial=0.0, maximum=0.0, multiplier=1.0, timeout=0.0))

    llm_with_fallback = primary_llm.with_fallbacks(
        [fallback_llm],
        exceptions_to_handle=(Exception,)
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

    # ── Fetch and customise the tool-calling prompt ───────────
    tool_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PREFIX + profile["suffix"]),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # ── Wire agent and executor ───────────────────────────────────────
    agent = create_tool_calling_agent(
        llm=llm_with_fallback,
        tools=tools,
        prompt=tool_prompt,
    )

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        max_iterations=None,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        verbose=settings.debug,
    )

    logger.info(
        "AgentExecutor ready — mode=%s model=%s fallback=%s max_tokens=%d tools=%s",
        mode,
        profile["model"],
        profile["fallback"],
        profile["max_tokens"],
        [t.name for t in tools],
    )

    return executor


def _bypass_classifier(question: str) -> QueryIntent:
    """Helper to bypass classification to save API requests."""
    return QueryIntent(
        intent_type="multi_tool",
        primary_metric=None,
        required_tools=[],
        missing_params=[],
        clarifying_question=None,
        rewritten_query=question,
        confidence="medium"
    )


def _resolve_intent(question: str, chat_context: str = "") -> QueryIntent:
    """Resolve intent using classifier when enabled, else bypass."""
    if not settings.enable_classifier:
        return _bypass_classifier(question)
    try:
        return classify_query(question, chat_context=chat_context)
    except Exception as exc:
        logger.warning(
            "Classifier failed (%s). Falling back to bypass mode.",
            type(exc).__name__,
        )
        return _bypass_classifier(question)


def run_with_classifier(
    executor: AgentExecutor,
    question: str,
    chat_context: str = "",
) -> dict[str, Any]:
    """Run a user question through the classifier -> agent pipeline.

    Classification is controlled by the ENABLE_CLASSIFIER setting.
    """
    # Step 1: Resolve intent (classifier enabled/disabled via settings)
    intent = _resolve_intent(question, chat_context=chat_context)

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

    output = _extract_text(result.get("output", "No response generated."))

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
    # Step 1: Resolve intent (classifier enabled/disabled via settings)
    intent = _resolve_intent(question, chat_context=chat_context)

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
            final_output = _extract_text(chunk["output"])

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

