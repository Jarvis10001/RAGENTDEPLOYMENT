# Workspace + Agent Workflow Audit

Last reviewed: 2026-04-17  
Repo: `g:\Jashan\RAGENT`

## 1) What This Project Is (Current Reality)

This is a FastAPI + React (Vite) conversational analytics system that runs a LangChain tool-calling agent for e-commerce intelligence.  
It is effectively a **single primary runtime agent** with multiple tool modules and one shared sub-LLM utility used by helper steps (SQL generation, query rewrite, optional classifier).

## 2) Runtime Agent Inventory (with Prompt Sources)

## A. Primary Orchestrator Agent

- File: `src/agent/primary_agent.py`
- Constructor: `get_agent_executor()`
- Agent type: `create_tool_calling_agent(...)` (LangChain tool-calling agent)
- LLM: `settings.primary_model` with fallback to `gemini-2.5-flash`
- Tools wired:
  - `omnichannel_feedback_search`
  - `marketing_content_search`
  - `ecommerce_sql_query`
  - `ecommerce_analytics_query`
  - `web_market_search`
- System prompt source:
  - `_SYSTEM_PREFIX` (`src/agent/primary_agent.py`, around line 54)
  - Plus appended instruction in prompt template:
    - "ALWAYS structure your final answer beautifully with markdown..."

Core prompt behavior enforced:
- Must use tools for every answer.
- Minimize API calls (2-3 iterations target).
- Respect `TOOL GUIDANCE` order if present.
- Use `PRIMARY METRIC` if present.
- Structured final response style: Finding -> Evidence -> Recommended Action.

## B. Query Classifier Sub-Agent (Implemented, Currently Bypassed)

- File: `src/agent/query_classifier.py`
- Prompt constant: `_CLASSIFIER_PROMPT` (around line 98)
- Uses sub-LLM (`get_sub_llm()`) to produce strict JSON `QueryIntent`
- Includes classification rules:
  - Clarify for "best/top" without metric
  - Root-cause => SQL + feedback
  - Messaging alignment => marketing + feedback
  - Benchmarks/competitors => web search

Important current behavior:
- In `src/agent/primary_agent.py`, `run_with_classifier()` and `stream_with_classifier()` call `_bypass_classifier()` instead of `classify_query()`.
- So classifier prompt exists but is not executed in current runtime path.

## C. SQL Generation Sub-Agent Prompt

- File: `src/tools/sql_tools.py`
- Function: `_generate_sql(...)`
- Prompt seed:
  - "You are a PostgreSQL expert. Generate a single, correct SELECT query."
- Adds:
  - schema context
  - strict safety rules (SELECT/CTE only)
  - deterministic rules (`ORDER BY`, `LIMIT`, aliases, analytics defaults)
  - optional filter hints (`campaign_id`, `product_sku`, dates)

## D. Tavily Query-Rewrite / Domain-Guard Sub-Agent Prompt

- File: `src/tools/tavily_tool.py`
- Function: `_rewrite_query(...)`
- Prompt seed:
  - "You are an E-Commerce Business Intelligence agent..."
- Behavior:
  - Reject non-business query via exact token `REJECTED_DOMAIN`
  - Else rewrite to concise search query (<= 12 words)

## E. RAG Tools (No LLM Prompt for Retrieval Core)

- File: `src/tools/rag_tools.py`
- Functions:
  - `omnichannel_feedback_search`
  - `marketing_content_search`
- Pipeline is embedding + pgvector retrieval + reranker; no prompt template in retrieval path itself.

## F. Shared Sub-Agent LLM Singleton

- File: `src/llm.py`
- Function: `get_sub_llm()`
- Role:
  - Common helper LLM backend used by classifier/sql/tavily rewrite flows.
- Model:
  - `settings.sub_agent_model` with fallback to `gemini-2.5-flash`.

---

## 3) "Skill Agents" in `.agents/` (Non-Runtime, Instruction Packs)

These are **SKILL.md instruction agents** for coding-assistant workflows, not part of your FastAPI runtime request execution.

Total skill directories found: 21

1. `building-pydantic-ai-agents`  
Prompt intent: Build agents with Pydantic AI; tools, structured output, streaming, tests, multi-agent patterns.
2. `deep-agents-core`  
Prompt intent: Core Deep Agents setup (`create_deep_agent`, middleware, SKILL.md structure).
3. `deep-agents-memory`  
Prompt intent: Deep Agents persistence/memory/filesystem backend patterns.
4. `deep-agents-orchestration`  
Prompt intent: Subagents, todo planning, human approvals in Deep Agents.
5. `framework-selection`  
Prompt intent: Decide LangChain vs LangGraph vs Deep Agents before coding.
6. `instrumentation`  
Prompt intent: Add Pydantic Logfire observability/tracing/monitoring.
7. `langchain-dependencies`  
Prompt intent: Package/version setup for LangChain/LangGraph/LangSmith/Deep Agents.
8. `langchain-fundamentals`  
Prompt intent: Build LangChain agents with `create_agent`, tools, middleware.
9. `langchain-middleware`  
Prompt intent: HITL approvals, middleware hooks, structured output.
10. `langchain-rag`  
Prompt intent: End-to-end RAG architecture and implementation.
11. `langgraph-fundamentals`  
Prompt intent: StateGraph, nodes, edges, command/send, streaming.
12. `langgraph-human-in-the-loop`  
Prompt intent: LangGraph `interrupt()` and resume patterns.
13. `langgraph-persistence`  
Prompt intent: Checkpointers, thread IDs, state persistence.
14. `supabase`  
Prompt intent: Broad Supabase work (DB/Auth/Edge/Realtimes/SSR/RLS/CLI/MCP).
15. `supabase-postgres-best-practices`  
Prompt intent: Postgres optimization and best practices for Supabase.
16. `tavily-best-practices`  
Prompt intent: Production Tavily integration patterns.
17. `tavily-cli`  
Prompt intent: General Tavily CLI workflow (search/extract/crawl/map/research).
18. `tavily-crawl`  
Prompt intent: Multi-page website crawl and extraction.
19. `tavily-extract`  
Prompt intent: Clean text/markdown extraction from URLs.
20. `tavily-map`  
Prompt intent: URL discovery/site structure mapping.
21. `tavily-research` and `tavily-search`  
Prompt intent: deep cited research / optimized web search.

---

## 4) Actual End-to-End Workflow (Current Code Path)

## Startup Flow

1. Frontend starts (`frontend` Vite app), backend starts (`uvicorn api.main:app`).
2. `POST /api/chat` is served by `api/main.py`.
3. `SessionManager` (`api/session_manager.py`) creates/reuses one `AgentExecutor` per `session_id`.
4. `get_agent_executor()` builds tool-calling agent + memory + tool list.

## Query Flow (Per User Message)

1. Frontend `streamChat()` sends `{message, session_id, history}` to `/api/chat`.
2. Backend reconstructs short `history_context` from last items.
3. Backend calls `stream_with_classifier(...)`.
4. Current behavior in `stream_with_classifier`:
   - classifier is bypassed (`_bypass_classifier`)
   - enhanced input built (usually just QUESTION line, no tool guidance)
   - response-cache checked
   - if miss: `executor.stream({"input": enhanced_input})`
5. As agent streams:
   - backend emits SSE `tool_start` when action starts
   - backend emits SSE `tool_end` when observation returns
   - backend emits tokenized final output via `token`
   - backend emits `done` with full response
6. Frontend:
   - updates assistant message progressively
   - records tool calls in right panel
   - extracts SQL/vector previews
   - extracts citation URLs from web tool output

## Tool Execution Sequence Behavior

- Sequence is dynamic by model decision at runtime.
- Deterministic tool ordering only happens if `TOOL GUIDANCE` is present.
- Because classifier is bypassed now, explicit tool guidance is generally absent.
- Caches can short-circuit execution at:
  - response level
  - each tool level

---

## 5) Supporting Subsystems

## Caching

- File: `src/cache/response_cache.py`
- Backing store: `diskcache` at `.cache/responses` (512 MiB limit)
- Namespaces observed:
  - `agent_response`
  - `sql`, `analytics`
  - `omnichannel`, `marketing`
  - `tavily`
  - (classifier cache exists in code path but not used while bypassed)

## Memory

- File: `src/memory/session_memory.py`
- Type: `ConversationBufferMemory` (`chat_history`, `return_messages=True`)
- Per-session memory retained in backend `SessionManager`.
- If backend restarts and frontend still has history, backend rehydrates memory from provided history.

## Data/Knowledge Sources

- Structured analytics: Supabase SQL RPC `execute_readonly_sql`
- Vector retrieval: Supabase pgvector RPCs `match_omnichannel_vectors`, `match_marketing_vectors`
- External web: Tavily API
- Ingestion pipeline: `src/ingestion/*` and migration script under `scripts/`

---

## 6) Important Mismatches / Drift Found

1. **Classifier architecture documented, but bypassed in live path**  
Code now skips `classify_query()` and uses `_bypass_classifier()`.

2. **Docs mention older stack details**  
`WORKFLOW.md` describes Streamlit, `hub.pull("hwchase17/react-chat")`, classifier-first determinism, and summary memory; current runtime is FastAPI + React + `create_tool_calling_agent` + `ConversationBufferMemory`.

3. **Integration tests appear stale**  
`tests/integration/test_primary_agent.py` patches `create_react_agent`/`hub` paths that no longer match current `primary_agent.py`.

4. **Header comments in `primary_agent.py` are partly stale**  
Docstring still says `create_react_agent` and mentions `max_iterations=3`, but runtime sets `max_iterations=None`.

5. **Script hardcoded paths**  
`scripts/migrate_embeddings_to_768.py` uses fixed `e:\RAGENT2\Default (1)\...` paths and destructive delete-then-insert pattern.

---

## 7) Practical Improvement Suggestions (Prioritized)

## High Priority

1. Re-enable classifier behind feature flag  
- Add env flag like `ENABLE_CLASSIFIER=true/false`.
- Default ON in non-rate-limited environments.
- Keep bypass for fallback/quota protection.

2. Align docs/tests with code  
- Update `README.md` and `WORKFLOW.md` to FastAPI/React/tool-calling reality.
- Fix integration tests to current constructors and prompt assembly.

3. Add observability around agent decisions  
- Log chosen tools + cache hit paths + fallback model usage in structured form.
- This will make debugging tool-routing issues much faster.

## Medium Priority

4. Add deterministic execution mode toggle  
- Optional strict mode: enforce classifier guidance + tool order.
- Optional adaptive mode: let primary agent choose freely.

5. Add prompt registry module  
- Move all prompts to `src/prompts/` with version tags.
- Easier A/B tests and safe prompt updates.

6. Harden Tavily guard + SQL prompt outputs  
- Add unit tests for `REJECTED_DOMAIN` edge cases.
- Add SQL generation golden tests for common business questions.

## Low Priority

7. Improve migration script safety  
- Replace hardcoded paths with CLI args/env vars.
- Upsert with idempotent keys instead of delete+insert.
- Add dry-run mode and resumable checkpoints.

8. Clean dead helpers / comments  
- Remove unused `_inject_system_prefix` path if no longer needed.
- Sync file docstrings with current behavior to reduce onboarding confusion.

---

## 8) Suggested Next Action Plan (Concrete)

1. Decide desired runtime mode:
   - keep classifier bypassed for cost
   - or re-enable classifier with feature flag
2. Update docs + tests in same PR (to prevent future drift)
3. Add a lightweight "agent trace event schema" for observability

If you want, I can do the next step directly: generate a follow-up patch that (a) adds `ENABLE_CLASSIFIER`, (b) reconnects classifier cleanly, and (c) updates `README.md` + `WORKFLOW.md` + tests to match the real flow.
