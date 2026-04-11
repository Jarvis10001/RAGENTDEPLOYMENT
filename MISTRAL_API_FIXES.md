# Mistral → Groq Migration & Pipeline Stability Fixes

This document records all modifications made to achieve a stable, production-ready
diagnostic pipeline. The original system used Mistral AI but suffered from chronic
free-tier rate-limiting, proxy overflow crashes, and JSON truncation. The migration
to Groq eliminates all three classes of issues simultaneously.

---

## Root Diagnosis

Mistral's free tier was not designed for agentic multi-step pipelines. A CrewAI crew
with 4 agents makes 6–10 sequential LLM calls per query. At a hard limit of ~1 req/sec,
that's a 10-second minimum pipeline — and any retry causes an overflow cascade. The
JSON truncation was a downstream symptom: staying small enough to avoid the rate limiter
forced aggressive token limits which cut off output mid-JSON.

**The single highest-leverage change was switching to Groq** (30 req/min free tier,
no proxy overflow, direct API).

---

## Fix 1 — Switch to Groq (eliminates overflow, rate-limits, and provider routing)

**Problem:** `MistralException - upstream connect error or disconnect/reset before headers. reset reason: overflow`

**Root Cause:** Mistral's free-tier Envoy proxy trips its circuit breaker when rapid
sequential requests (from multi-agent orchestration) or large payloads overflow the
per-connection queue.

**Solution:**
- Replaced `MISTRAL_API_KEY` with `GROQ_API_KEY` in `src/config.py`
- All model defaults now use `groq/` prefix (e.g., `groq/llama-3.1-70b-versatile`)
- LiteLLM natively supports `groq/` — same routing mechanism, zero code changes needed
- Router uses the fast `llama-3.1-8b-instant` (classification doesn't need 70B)
- Reasoning agents use `llama-3.1-70b-versatile`

**Files changed:** `src/config.py`, `.env`, `.env.example`, `requirements.txt`

---

## Fix 2 — Agent LLM Instantiation (simplified, no manual prefix logic)

**Problem:** All agents had manual `if not model_name.startswith("mistral/")` prefix
logic and passed `api_key=settings.mistral_api_key` explicitly.

**Solution:**
- Removed all `mistral/` prefix boilerplate — model names in config already include
  the `groq/` prefix
- Removed `api_key=` parameter from LLM constructors — `GROQ_API_KEY` is set in
  `os.environ` via `main.py` and LiteLLM auto-discovers it
- Tuned `max_tokens` per agent role:
  - Router: 512 (intent JSON is small)
  - SQL Analyst: 1024
  - RAG Retrieval: 1024
  - Synthesis: 2048 (needs room for full report)

**Files changed:** All 4 agent files in `src/agents/`

---

## Fix 3 — JSON Truncation (Pydantic structured output)

**Problem:** SQL Analyst output was truncated mid-JSON (e.g., `"daily_spen...`)
because the LLM tried to serialise 30+ rows and a multi-paragraph analysis_summary,
exceeding the token ceiling.

**Root Cause:** Asking the LLM to "generate JSON as free text" means it serialises
the whole payload in one shot and gets cut off by `max_tokens`.

**Solution:**
- Added `output_pydantic=SQLAnalysisResult` to the CrewAI Task — CrewAI validates
  against the Pydantic schema and auto-retries if parsing fails
- Tightened `raw_rows` to `max_length=5` in the Pydantic model
- Changed `analysis_summary` description to "2-3 sentences MAX"
- `key_metrics` capped at 8 entries in the prompt
- Added explicit PostgREST limitation warnings in the prompt (no COUNT/SUM/AVG)

**Files changed:** `src/models/sql_result.py`, `src/agents/sql_analyst_agent.py`

---

## Fix 4 — PostgREST Aggregate Function Rejection

**Problem:** The LLM kept trying to use `COUNT(*)`, `SUM()`, `AVG()` in the `select`
field, causing `Could not find a relationship between 'orders' and 'COUNT'` errors.

**Root Cause:** Supabase uses PostgREST which doesn't support SQL aggregate functions
in the select clause.

**Solution:**
- Added aggregate keyword detection in `SupabaseSQLTool._run()` — rejects queries
  with COUNT/SUM/AVG/MIN/MAX/GROUP BY before they hit the API
- Added explicit warning in the agent prompt and tool description
- Agent is told to "compute aggregations yourself from the returned rows"

**Files changed:** `src/tools/supabase_sql_tool.py`, `src/agents/sql_analyst_agent.py`

---

## Fix 5 — Operator Alias Mapping

**Problem:** The LLM frequently generated SQL-style operators (`>=`, `<=`, `!=`)
which were silently skipped by the filter system, causing incorrect query results.

**Solution:**
- Extended `_apply_filters()` operator map with SQL-style aliases:
  `>=` → `gte`, `<=` → `lte`, `>` → `gt`, `<` → `lt`, `!=` → `neq`, `=` → `eq`

**Files changed:** `src/tools/supabase_sql_tool.py`

---

## Fix 6 — Exponential Backoff Retry

**Problem:** Transient API failures (429, 5xx, overflow) crashed the pipeline
immediately with no retry.

**Solution:**
- Created `src/tools/retry_mixin.py` with a `@with_exponential_backoff` decorator
- Applied to `SupabaseSQLTool._run()` with `max_retries=3, base_delay=2.0s`
- Retries on: rate limits (429), server errors (5xx), overflow/upstream errors
- Non-retryable errors (400, 422, etc.) bubble up immediately

**Files changed:** `src/tools/retry_mixin.py` (new), `src/tools/supabase_sql_tool.py`

---

## Fix 7 — Telemetry Suppression (consolidated)

**Problem:** CrewAI OTEL auto-instruments before env vars are set, flooding the
console with red traceblocks from failed telemetry connections.

**Solution:**
- Set `OTEL_SDK_DISABLED=true` and `CREWAI_DISABLE_TELEMETRY=true` at the very
  top of `main.py`, before any imports
- Added `LiteLLM` to the noisy logger suppression list
- Pushed `GROQ_API_KEY` into `os.environ` before CrewAI imports

**Files changed:** `main.py`

---

## Fix 8 — Session Memory (Mistral dependency removed)

**Problem:** `session_memory.py` imported `ChatMistralAI` directly, creating a
hard dependency on `langchain-mistralai`.

**Solution:**
- Replaced `ChatMistralAI` with `ChatLiteLLM` from `langchain-community`
- Routes through the same Groq provider as all other agents
- Uses the fast 8B model for conversation summarisation

**Files changed:** `src/memory/session_memory.py`, `requirements.txt`

---

## Summary of Changes

| Issue | Root cause | Fix |
|---|---|---|
| Proxy overflow crashes | Mistral free tier = 1 req/sec | Switch to Groq (30 req/min) |
| LiteLLM provider routing | No provider prefix | Model names include `groq/` prefix in config |
| JSON truncation | LLM generates JSON as free text hitting token ceiling | `output_pydantic=` + tighter field constraints |
| PostgREST aggregate errors | LLM uses COUNT/SUM in select | Aggregate rejection + explicit prompt warning |
| Operator mapping failures | LLM uses SQL-style `>=`/`<=` | Added alias mapping in filter system |
| No transient error recovery | Single-shot tool calls | `@with_exponential_backoff` on tools |
| Telemetry spam | OTEL env vars set after import | Set before any imports in main.py |
| 70B model wasted on classification | Same model for all agents | Router = 8B, reasoning = 70B |
| Mistral hard dependency | `langchain-mistralai` in session memory | Replaced with `ChatLiteLLM` |
