# Groq Rate Limit & Pydantic Parsing Fixes

This document records the modifications made to resolve the latest issues with the `DiagnosticCrew` pipeline crashing due to Pydantic parsing behavior, an unexpected Groq model deprecation, and Groq rate limits.

---

## 1. CrewAI Native Pydantic Output Fix
**Problem:** `Router output is not valid JSON. Falling back to defaults.` And similarly for `sql_analyst_agent.py`, `rag_retrieval_agent.py`, and `synthesis_agent.py`.
When `output_pydantic` was introduced to CrewAI Agents, CrewAI stopped passing a Raw JSON string backwards to the pipeline. Instead, it successfully captured and validated the JSON directly via LiteLLM and instantiated a Python Pydantic Class immediately under `.pydantic`. Because the code expected a string via `str(result)` and then repeatedly attempted up to `json.loads(stringIFIED_Class)`, it threw an exception and fell backward to default errors.

**Solution:**
- Updated all 4 parsing functions (`parse_router_output`, `parse_sql_analyst_output`, `parse_rag_retrieval_output`, `parse_synthesis_output`) to inspect the class instance:
```python
if hasattr(raw_output, "pydantic") and raw_output.pydantic:
    return raw_output.pydantic
```
- Completely bypassed `str(result)` stringifying in `src/crews/diagnostic_crew.py`.

**Files Changed:**
- `src/crews/diagnostic_crew.py`
- `src/agents/query_router_agent.py`
- `src/agents/sql_analyst_agent.py`
- `src/agents/rag_retrieval_agent.py`
- `src/agents/synthesis_agent.py`

---

## 2. Groq Rate Limit Exceeded
**Problem:** `litellm.RateLimitError: Rate limit reached for model llama-3.3-70b-versatile in organization ... Limit 12000, Used 10575, Requested 2152. Please try again in 3.635s.`
When generating lengthy reasoning via 70B parameters, it frequently exceeded the Free Tier Groq token limits per minute (12000 TPM limit). CrewAI failed entirely instead of retrying gracefully.

**Solution:**
- Injected specific `os.environ` fallback commands directly into `main.py` explicitly for LiteLLM. LiteLLM dynamically executes up to 5 retries automatically catching specifically 429 Status headers, and backs down linearly for 30 Seconds.
```python
# Configure LiteLLM Rate Limit Auto-Retries
os.environ["LITELLM_NUM_RETRIES"] = "5"
os.environ["LITELLM_MAX_BACKOFF"] = "30"
```

**Files Changed:**
- `main.py`

---

## 3. Groq Decommissioned Model Error
**Problem:** Groq fully deprecated `llama-3.1-70b-versatile` out of active development.

**Solution:**
- Migrated default model routing variables natively to the active version `llama-3.3-70b-versatile`.

**Files Changed:**
- `.env`
- `.env.example`
- `src/config.py`

---

## 4. PGRST202 Cache Error (Supabase)
**Problem:** `Could not find the function public.match_omnichannel_vectors... in the schema cache, code: PGRST202.` 
This is a Supabase Postgres bug that happens dynamically when SQL custom functions are made before `PostgREST` updates natively. 

**Solution Action Required:** 
Run `NOTIFY pgrst, reload schema;` manually inside the Supabase SQL Editor GUI Dashboard to flush vector schemas.
