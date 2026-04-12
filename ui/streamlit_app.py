"""Streamlit chat interface for the E-commerce Intelligence Agent.

Run with::

    streamlit run ui/streamlit_app.py

The UI uses a two-column layout:
  • Left  (2.5x): Chat area with streaming message history.
  • Right (1x)  : Session controls, live tool activity, query intent, example queries.

Query Classification Flow
--------------------------
Before invoking the agent, every user query passes through a classifier.
If the classifier detects ambiguity, a clarifying question is displayed
as a normal assistant chat message. The user's follow-up answer is
combined with the original query and re-classified.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so ``src.*`` imports work when
# Streamlit runs this file as a standalone script outside the package.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

# ── Page config MUST be the very first Streamlit call ────────────────
st.set_page_config(
    page_title="E-commerce Intelligence Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.agent.primary_agent import get_agent_executor, run_with_classifier  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════
# Session State Initialisation
# ═══════════════════════════════════════════════════════════════════════

if "agent_executor" not in st.session_state:
    with st.spinner("⚙️ Loading Intelligence Agent & verifying database…"):
        try:
            st.session_state.agent_executor = get_agent_executor()
            st.session_state.init_error = None
        except Exception as exc:
            st.session_state.agent_executor = None
            st.session_state.init_error = str(exc)

if "messages" not in st.session_state:
    st.session_state.messages = []  # list[dict[str, str]]

if "tool_calls" not in st.session_state:
    st.session_state.tool_calls = []  # list[dict[str, str]]

if "token_estimate" not in st.session_state:
    st.session_state.token_estimate = 0

if "last_intent" not in st.session_state:
    st.session_state.last_intent = None  # QueryIntent or None

# Clarification tracking: when the classifier asks a question, we store
# the original query so the follow-up answer can be combined with it.
if "pending_clarification" not in st.session_state:
    st.session_state.pending_clarification = None  # str or None


# ═══════════════════════════════════════════════════════════════════════
# Layout
# ═══════════════════════════════════════════════════════════════════════

left_col, right_col = st.columns([2.5, 1])

# ─── Right column: controls & info ───────────────────────────────────
with right_col:
    st.subheader("⚙️ Session")

    # Show init error if agent failed to load
    if st.session_state.get("init_error"):
        st.error(f"Agent init failed: {st.session_state.init_error}")

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tool_calls = []
        st.session_state.token_estimate = 0
        st.session_state.last_intent = None
        st.session_state.pending_clarification = None
        if st.session_state.agent_executor is not None:
            mem = getattr(st.session_state.agent_executor, "memory", None)
            if mem is not None:
                mem.clear()
        st.rerun()

    st.caption(f"~{st.session_state.token_estimate:,} tokens used this session")

    # ─── Clarification indicator ─────────────────────────────────────
    if st.session_state.pending_clarification is not None:
        st.warning("⏳ Awaiting your clarification…")

    st.divider()

    # ─── Query Intent Panel ──────────────────────────────────────────
    st.subheader("🎯 Query Intent")
    if st.session_state.last_intent is not None:
        intent = st.session_state.last_intent
        with st.expander("Classification Details", expanded=False):
            st.markdown(f"**Type:** `{intent.intent_type}`")
            st.markdown(f"**Confidence:** `{intent.confidence}`")
            if intent.primary_metric:
                st.markdown(f"**Metric:** `{intent.primary_metric}`")
            if intent.required_tools:
                st.markdown(f"**Tools:** `{', '.join(intent.required_tools)}`")
            st.markdown(f"**Rewritten:** {intent.rewritten_query}")
            if intent.missing_params:
                st.markdown(f"**Missing:** `{', '.join(intent.missing_params)}`")
    else:
        st.caption("No query classified yet.")

    st.divider()

    st.subheader("🔧 Tool Activity")
    if st.session_state.tool_calls:
        for tc in st.session_state.tool_calls:
            tool_name = tc.get("tool", "unknown")
            raw_input = str(tc.get("input", ""))
            display_input = raw_input[:120] + ("…" if len(raw_input) > 120 else "")
            st.info(f"**{tool_name}**\n\n{display_input}")
    else:
        st.caption("No tools called yet in this turn.")

    st.divider()

    st.subheader("💡 Example Questions")
    st.caption("Click to copy → paste into the chat")

    _EXAMPLE_QUERIES = [
        "Why did our net profit margin drop last month?",
        "Which campaigns have the best ROI?",
        "What are customers saying about our packaging?",
        "Compare split shipment rates across warehouses",
        "What are 2024 e-commerce return rate benchmarks?",
        "Is our SUMMER_SALE messaging aligned with feedback?",
        "Which customers acquired via Instagram have highest CLV?",
        "High freight costs on SKU-4421 — are customers complaining?",
    ]

    for eq in _EXAMPLE_QUERIES:
        st.code(eq, language=None)


# ─── Left column: chat area ──────────────────────────────────────────
with left_col:
    st.title("📊 E-commerce Intelligence Agent")
    st.caption("Ask natural-language questions about your operations, campaigns, and customers")

    # Render persisted message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Guard: if agent didn't initialise, show error and stop
    if st.session_state.agent_executor is None:
        st.error(
            "The agent could not be initialised. Check your API keys "
            "and database connection, then refresh the page."
        )
        st.stop()

    # Chat input — blocks until user submits
    question = st.chat_input("Ask a question about your e-commerce data…")

    if question:
        # 1. Show user message immediately
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # 2. Build the effective query
        # If we have a pending clarification, combine original + user answer
        effective_question = question
        chat_context = ""
        if st.session_state.pending_clarification is not None:
            original = st.session_state.pending_clarification
            effective_question = (
                f"{original}\n\n"
                f"User clarification: {question}"
            )
            chat_context = f"Original question: {original}"
            st.session_state.pending_clarification = None  # Clear it

        # Build context from recent messages for the classifier
        if not chat_context:
            recent = st.session_state.messages[-6:]  # Last 3 exchanges
            chat_context = "\n".join(
                f"{m['role']}: {m['content'][:200]}" for m in recent
            )

        # 3. Run through classifier → agent pipeline
        output = "⚠️ No response generated."
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analysing…"):
                try:
                    result = run_with_classifier(
                        executor=st.session_state.agent_executor,
                        question=effective_question,
                        chat_context=chat_context,
                    )

                    output = result.get("output") or "No response generated."
                    is_clarification = result.get("needs_clarification", False)
                    intent = result.get("intent")

                    # Store intent for the right panel
                    if intent is not None:
                        st.session_state.last_intent = intent

                    # If this is a clarifying question, track original query
                    if is_clarification:
                        # Store the original question for when the user responds
                        st.session_state.pending_clarification = effective_question
                        output = f"🤔 {output}"  # Visual indicator
                        st.session_state.tool_calls = []
                    else:
                        # Parse intermediate steps → populate tool activity panel
                        intermediate_steps = result.get("intermediate_steps", [])
                        tool_calls_this_turn: list[dict[str, str]] = []
                        for step in intermediate_steps:
                            if len(step) >= 2:
                                action = step[0]
                                tool_calls_this_turn.append(
                                    {
                                        "tool": getattr(action, "tool", "unknown"),
                                        "input": str(getattr(action, "tool_input", "")),
                                    }
                                )
                        st.session_state.tool_calls = tool_calls_this_turn

                    # Rough token estimate: 4 chars ≈ 1 token
                    st.session_state.token_estimate += (len(question) + len(output)) // 4

                except Exception as exc:
                    output = (
                        f"❌ **Error**: `{type(exc).__name__}: {exc}`\n\n"
                        "Please try a more specific question or check your API keys."
                    )

                st.markdown(output)

        # 4. Persist assistant message
        st.session_state.messages.append({"role": "assistant", "content": output})

        # 5. Rerun ONLY to update the side panel (tool activity, intent).
        # The chat messages are already rendered above, so the rerun
        # just refreshes the right column with the latest state.
        st.rerun()


# ── Entry point note ─────────────────────────────────────────────────
if __name__ == "__main__":
    # Streamlit executes the whole script on each interaction — no main() needed.
    pass
