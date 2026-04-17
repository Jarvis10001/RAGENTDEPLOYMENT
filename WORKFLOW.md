# RAGENT — E-commerce Intelligence Agent: Complete System Workflow

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Startup Flow](#startup-flow)
4. [Query Processing Pipeline](#query-processing-pipeline)
5. [Query Classifier (Deterministic Pre-Processing)](#query-classifier)
6. [Clarification Mechanism](#clarification-mechanism)
7. [ReAct Agent Loop](#react-agent-loop)
8. [Tool Details](#tool-details)
9. [Caching Architecture](#caching-architecture)
10. [Memory System](#memory-system)
11. [Module Dependency Map](#module-dependency-map)
12. [Configuration Reference](#configuration-reference)

---

## System Overview

RAGENT is a multi-tool E-commerce Intelligence Agent that answers natural-language business questions by orchestrating five specialised tools:

| Tool | Function | Data Source |
|------|----------|-------------|
| `ecommerce_sql_query` | Row-level lookups (individual orders, customer records) | Supabase PostgreSQL |
| `ecommerce_analytics_query` | Aggregations, trends, cohort comparisons | Supabase PostgreSQL |
| `omnichannel_feedback_search` | Customer sentiment, reviews, support tickets | Supabase pgvector (RAG) |
| `marketing_content_search` | Campaign ad copy, briefs, brand positioning | Supabase pgvector (RAG) |
| `web_market_search` | Industry benchmarks, competitor data, market trends | Tavily Web Search API |

**Key design principles:**
- **Deterministic (toggleable)**: The query classifier can pre-process each question into a structured intent before the agent runs (`ENABLE_CLASSIFIER=true`), or be bypassed (`ENABLE_CLASSIFIER=false`).
- **Clarification-aware**: When a query is ambiguous, the system asks the user for clarification instead of guessing.
- **Cached**: Multi-layer caching (tool-level + response-level) eliminates redundant API calls.
- **Safe**: All SQL is validated against a DML/DDL blocklist and executed via a read-only Postgres RPC.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          STREAMLIT UI                                │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │  Chat Area   │  │  Tool Activity   │  │   Query Intent Panel  │  │
│  │  (left col)  │  │  (right col)     │  │   (right col)         │  │
│  └──────┬───────┘  └──────────────────┘  └───────────────────────┘  │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              run_with_classifier()                            │    │
│  │  question ───► classify_query() ───► needs_clarification?    │    │
│  │                     │                    │                    │    │
│  │                     │ YES                │ NO                 │    │
│  │                     ▼                    ▼                    │    │
│  │          Return clarifying        build_enhanced_input()     │    │
│  │          question to user         + tool guidance             │    │
│  │                                         │                    │    │
│  │                                         ▼                    │    │
│  │                               AgentExecutor.invoke()          │    │
│  │                               (ReAct loop with tools)         │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       TOOL LAYER                                     │
│                                                                      │
│  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ SQL Query │ │ Analytics │ │Omnichan. │ │Marketing │ │  Web    │ │
│  │   Tool    │ │   Tool    │ │  RAG     │ │   RAG    │ │ Search  │ │
│  └─────┬─────┘ └─────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ │
│        │              │            │             │            │      │
│        ▼              ▼            ▼             ▼            ▼      │
│   ┌─────────┐   ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐ │
│   │Gemini   │   │Gemini   │  │Encoder │  │Encoder │  │Gemini    │ │
│   │Flash    │   │Flash    │  │+Rerank │  │+Rerank │  │Flash     │ │
│   │SQL Gen  │   │SQL Gen  │  │        │  │        │  │Query     │ │
│   └────┬────┘   └────┬────┘  └───┬────┘  └───┬────┘  │Rewrite  │ │
│        │              │          │            │       └────┬─────┘ │
│        ▼              ▼          ▼            ▼            ▼      │
│   ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────┐ │
│   │   Supabase RPC       │  │   Supabase pgvector  │  │ Tavily  │ │
│   │ execute_readonly_sql │  │ match_*_vectors      │  │   API   │ │
│   └──────────────────────┘  └──────────────────────┘  └─────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SHARED INFRASTRUCTURE                            │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  src/llm.py  │  │  diskcache   │  │  ConversationSummary     │   │
│  │  Shared LLM  │  │  Response    │  │  BufferMemory            │   │
│  │  Singleton   │  │  Cache       │  │  (rolling summary)       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Startup Flow

**What happens when you run `streamlit run ui/streamlit_app.py`:**

```
1. streamlit_app.py executes top-level code
   │
   ├─ st.set_page_config()                     # Must be first Streamlit call
   │
   ├─ import src.agent.primary_agent            # Triggers chain of imports:
   │   ├─ import src.config (Settings)          #   → loads .env → validates all keys
   │   ├─ import src.cache.response_cache       #   → creates .cache/responses dir
   │   ├─ import src.tools.sql_tools            #   → registers @tool decorators
   │   ├─ import src.tools.rag_tools            #   → registers @tool decorators
   │   ├─ import src.tools.tavily_tool          #   → registers @tool decorators
   │   └─ import src.agent.query_classifier     #   → loads classifier prompt
   │
   ├─ Session state init (first visit only):
   │   │
   │   └─ get_agent_executor()
   │       ├─ health_check()                    # Lightweight SELECT on customers table
   │       ├─ ChatGoogleGenerativeAI(primary)   # Create primary LLM (Gemini Pro)
   │       ├─ create_memory()                   # ConversationSummaryBufferMemory
   │       │   └─ get_sub_llm()                 # First call → creates shared singleton
   │       ├─ hub.pull("hwchase17/react-chat")  # Fetch ReAct prompt (network call)
   │       ├─ _inject_system_prefix()           # Prepend system instructions
   │       └─ AgentExecutor(agent, tools, mem)  # Wire everything together
   │
   └─ Render UI layout (left chat + right sidebar)
```

**Critical note:** All `get_sub_llm()`, `get_supabase_client()`, `get_encoder()`, `get_reranker()` are **lazy singletons**. They are NOT created at import time — only on first actual use. This keeps startup fast.

---

## Query Processing Pipeline

**Full lifecycle of a user question (e.g. "Why did profit margins drop?"):**

```
Step 1: User types question in st.chat_input()
   │
Step 2: Check pending_clarification in session state
   │     If pending → combine original question + user's clarification answer
   │     If not → build chat_context from last 3 message exchanges
   │
Step 3: run_with_classifier(executor, question, chat_context)
   │
   ├─ 3a. classify_query(question, chat_context)
   │       ├─ If ENABLE_CLASSIFIER=false → bypass classifier and use _bypass_classifier(question)
   │       │   (skips classifier cache and classifier LLM call)
   │       └─ If ENABLE_CLASSIFIER=true:
   │       ├─ Check classifier cache (keyed on question + context[:200])
   │       ├─ If miss → invoke sub-LLM with classification prompt
   │       │   ├─ Prompt includes: database schema, available tools, rules
   │       │   └─ Returns JSON → parsed into QueryIntent Pydantic model
   │       └─ Cache the classification result
   │
   ├─ 3b. needs_clarification(intent)?
   │       ├─ YES → return {"output": clarifying_question, "needs_clarification": True}
   │       │        → UI stores original question in pending_clarification
   │       │        → UI shows "🤔 Which metric do you want to rank by?"
   │       │        → PIPELINE STOPS HERE — waits for user follow-up
   │       │
   │       └─ NO → continue to step 3c
   │
   ├─ 3c. build_enhanced_input(question, intent)
   │       → "QUESTION: <rewritten_query>\n
   │          TOOL GUIDANCE: Call these tools in this order: tool1, tool2\n
   │          PRIMARY METRIC: Focus on revenue"
   │
   ├─ 3d. Check response-level cache
   │       Key = hash(rewritten_query + tools + metric + context_hash)
   │       ├─ HIT → return cached response immediately (no tool calls)
   │       └─ MISS → continue to step 3e
   │
   ├─ 3e. executor.invoke({"input": enhanced_input})
   │       └─ ReAct loop begins (see next section)
   │
   ├─ 3f. Cache the final response
   │
   └─ 3g. Return {"output": answer, "intent": intent, "intermediate_steps": [...]}

Step 4: UI renders the answer + updates tool activity panel
Step 5: st.rerun() to refresh the sidebar with latest tool/intent state
```

---

## Query Classifier

**File:** `src/agent/query_classifier.py`

The classifier runs BEFORE the ReAct agent to produce a deterministic execution plan. It uses the sub-agent LLM (Gemini Flash) at temperature=0.

### QueryIntent Schema

```python
class QueryIntent:
    intent_type: str        # sql_lookup | sql_analytics | rag_feedback |
                            # rag_marketing | web_search | multi_tool |
                            # clarification_needed
    primary_metric: str     # revenue | roi | clv | cac | margin | freight_cost | null
    required_tools: list    # ["ecommerce_analytics_query", "omnichannel_feedback_search"]
    missing_params: list    # ["metric", "date_range"] — what's ambiguous
    clarifying_question: str # "Which metric do you want to rank by?" or null
    rewritten_query: str    # Precise, unambiguous version of user's question
    confidence: str         # high | medium | low
```

### Classification Rules (Key Examples)

| User Query | Intent Type | Tools | Clarify? |
|---|---|---|---|
| "Total revenue by campaign" | sql_analytics | [ecommerce_analytics_query] | No |
| "Best campaigns" (no metric) | clarification_needed | [] | Yes: "Which metric?" |
| "Why did margins drop?" | multi_tool | [ecommerce_analytics_query, omnichannel_feedback_search] | No |
| "What are customers saying?" | rag_feedback | [omnichannel_feedback_search] | No |
| "Industry return rate benchmarks" | web_search | [web_market_search] | No |
| "Is SUMMER_SALE messaging aligned?" | multi_tool | [marketing_content_search, omnichannel_feedback_search] | No |

---

## Clarification Mechanism

**How it works end-to-end:**

```
Turn 1: User asks "Which campaigns are performing best?"
   │
   ├─ Classifier detects "best" without a metric
   ├─ Returns: intent_type="clarification_needed"
   │           clarifying_question="Which metric do you want to rank by?
   │                                Revenue, ROI, CLV, or click-through rate?"
   ├─ UI shows: "🤔 Which metric do you want to rank by?"
   └─ Session state: pending_clarification = "Which campaigns are performing best?"

Turn 2: User responds "ROI"
   │
   ├─ UI detects pending_clarification is set
   ├─ Builds effective_question:
   │   "Which campaigns are performing best?
   │    User clarification: ROI"
   ├─ chat_context = "Original question: Which campaigns are performing best?"
   ├─ Clears pending_clarification = None
   │
   ├─ Re-classifies with the combined question
   │   → intent_type="sql_analytics", primary_metric="roi"
   │   → required_tools=["ecommerce_analytics_query"]
   │   → rewritten_query="Rank all campaigns by ROI (revenue / spend)"
   │
   └─ Agent executes normally with full context
```

---

## ReAct Agent Loop

**File:** `src/agent/primary_agent.py`

The agent uses the `hwchase17/react-chat` prompt pattern:

```
Thought: I need to find campaign ROI data.
Action: ecommerce_analytics_query
Action Input: {"question": "Rank campaigns by ROI (total revenue / total spend)"}
Observation: [SQL results table]
Thought: I have the data. Let me format the answer.
Final Answer: **Finding** → ... **Evidence** → ... **Recommended Action** → ...
```

### What the ReAct agent has access to:

| Resource | Details |
|---|---|
| **Primary LLM** | Gemini Pro (temperature=0, max_tokens=2048) |
| **5 Tools** | See Tool Details below |
| **System Prompt** | `_SYSTEM_PREFIX` — enforces tool-first behaviour & deterministic execution |
| **Memory** | ConversationSummaryBufferMemory (2000 token budget) |
| **Max Iterations** | 8 (prevents infinite loops) |
| **Parsing Error Handling** | `handle_parsing_errors=True` — auto-recovers from malformed output |

### Execution constraints from the system prompt:

1. **MUST use tools** — never answer from training knowledge alone
2. **Follow TOOL GUIDANCE order** when classifier provides it
3. **Focus on PRIMARY METRIC** when classifier specifies one
4. **Root-cause questions** → always call SQL + feedback tools
5. **Structure every answer** as: Finding → Evidence → Recommended Action

---

## Tool Details

### Tool 1: `omnichannel_feedback_search` (RAG)

**Pipeline:**
```
query → cache check → encode(query) → Supabase RPC match_omnichannel_vectors
      → retrieve K=20 candidates → cross-encoder rerank → keep top K=5
      → format with scores → cache write → return
```

**What it searches:** Customer reviews, support tickets, complaints, feedback stored as 384-dim embeddings in `omnichannel_vectors`.

**Input params:** `query` (required), `filter_order_id` (optional UUID), `top_k_retrieve` (default 20), `top_k_rerank` (default 5).

---

### Tool 2: `marketing_content_search` (RAG)

**Pipeline:** Same as Tool 1 but calls `match_marketing_vectors` RPC.

**What it searches:** Campaign ad copy, briefs, promotional materials in `marketing_vectors`.

**Input params:** `query` (required), `filter_campaign_id` (optional), `top_k_retrieve`, `top_k_rerank`.

---

### Tool 3: `ecommerce_sql_query` (SQL)

**Pipeline:**
```
question → cache check → Gemini Flash generates SELECT SQL
         → security validation (_validate_sql: no DML/DDL keywords)
         → Supabase RPC execute_readonly_sql → compress to 5 rows
         → format → cache write → return
```

**What it queries:** Row-level lookups — individual orders, customer records, campaign spend, shipment details.

**Database tables accessible:**
- `customers` (customer_id, clv, acquisition_date, status)
- `marketing_campaigns` (campaign_id, campaign_name, channel, daily_spend, impressions, clicks, cac)
- `campaign_products` (campaign_id, product_sku)
- `orders` (order_id, customer_id, campaign_id, dynamic_price_paid, is_split_shipment, net_profit_margin, order_date)
- `shipments` (shipment_id, order_id, product_sku, warehouse_shipped_from, freight_cost, dispatch_date, delivery_status)
- `events_log` (event_id, customer_id, campaign_id, event_type, event_timestamp)

**Security:** Only `SELECT`/`WITH` allowed. Forbidden keywords: INSERT, UPDATE, DELETE, DROP, TRUNCATE, CREATE, ALTER, GRANT, REVOKE, EXECUTE, COPY. Filter inputs validated with regex (`^[a-zA-Z0-9_-]+$` for IDs, `^\d{4}-\d{2}-\d{2}$` for dates).

---

### Tool 4: `ecommerce_analytics_query` (SQL)

**Pipeline:** Same as Tool 3 but with additional analytics guidance in the prompt (GROUP BY, DATE_TRUNC, window functions, CTEs, deterministic defaults for "best"/"top" queries).

**Deterministic defaults:** When user asks for "best" campaigns without a metric, always calculates BOTH `total_revenue` AND `roi`, ordered by `total_revenue DESC`.

---

### Tool 5: `web_market_search` (Web)

**Pipeline:**
```
query → cache check → Gemini Flash rewrites query (≤12 words)
      → Tavily search (advanced depth, 5 results)
      → format with URLs → cache write (30min TTL) → return
```

**What it searches:** Live internet — industry benchmarks, competitor data, current market trends.

---

## Caching Architecture

### Layer 1: Classifier Cache
- **Key:** `hash("classifier", question, context[:200])`
- **TTL:** 3600s (1 hour)
- **Purpose:** Avoid re-classifying the same question

### Layer 2: Tool-Level Cache  
- **Key:** `hash(namespace, question, filters, params)`
- **TTL:** 3600s for SQL/RAG, 1800s (30min) for web search
- **Purpose:** Avoid redundant DB/API calls for identical queries
- **Namespaces:** `"sql"`, `"analytics"`, `"omnichannel"`, `"marketing"`, `"tavily"`

### Layer 3: Response-Level Cache
- **Key:** `hash("agent_response", rewritten_query, tools, metric, context_hash)`
- **TTL:** 3600s (1 hour)
- **Purpose:** Return identical answers for semantically equivalent questions
- **Context-aware:** Includes a hash of the first 500 chars of chat context, so "what about last month?" in different conversations gets different answers

### Cache bypass:
- Clarification queries **never** hit the response cache
- Cache is disabled in test mode (`CACHE_ENABLED=false`)
- All cache operations are non-fatal — failures fall through to live execution

**Storage:** `diskcache` (SQLite-backed, 512 MiB limit) at `.cache/responses/`

---

## Memory System

**Type:** `ConversationSummaryBufferMemory`

**How it works:**
- Recent messages are kept **verbatim** in memory
- When the token budget (2000 tokens) is exceeded, older messages are **summarised** by Gemini Flash into a condensed rolling summary
- The memory auto-loads into the agent via `memory_key="chat_history"`
- On "Clear conversation", both the message buffer and summary are wiped

**Why this matters:** The agent can reference earlier questions in the conversation without consuming the entire context window. For example, if the user asks about Campaign A in turn 1, then "what about Campaign B?" in turn 3, the memory retains the context.

---

## Module Dependency Map

```
ui/streamlit_app.py
  └─ src/agent/primary_agent.py
       ├─ src/agent/query_classifier.py
       │    ├─ src/llm.py (shared sub-LLM)
       │    ├─ src/cache/response_cache.py
       │    └─ src/config.py (settings)
       │
       ├─ src/memory/session_memory.py
       │    └─ src/llm.py (shared sub-LLM)
       │
       ├─ src/tools/sql_tools.py
       │    ├─ src/llm.py (shared sub-LLM)
       │    ├─ src/db/supabase_client.py
       │    ├─ src/cache/response_cache.py
       │    ├─ src/models/tool_inputs.py
       │    └─ src/utils/{retry.py, token_budget.py}
       │
       ├─ src/tools/rag_tools.py
       │    ├─ src/embeddings/encoder.py (SentenceTransformer)
       │    ├─ src/embeddings/reranker.py (CrossEncoder)
       │    ├─ src/db/supabase_client.py
       │    ├─ src/cache/response_cache.py
       │    ├─ src/models/tool_inputs.py
       │    └─ src/utils/retry.py
       │
       ├─ src/tools/tavily_tool.py
       │    ├─ src/llm.py (shared sub-LLM)
       │    ├─ src/cache/response_cache.py
       │    ├─ src/models/tool_inputs.py
       │    ├─ src/utils/retry.py
       │    └─ tavily (external SDK)
       │
       ├─ src/db/supabase_client.py
       │    └─ src/config.py
       │
       └─ src/cache/response_cache.py
            ├─ diskcache (external)
            └─ src/config.py

src/ingestion/ (standalone — not used at runtime)
  ├─ chunking.py → src/config.py
  └─ embed_and_upsert.py → src/embeddings/encoder.py, src/db/supabase_client.py
```

---

## Configuration Reference

All settings are loaded from `.env` via `pydantic-settings`:

| Variable | Default | Description |
|---|---|---|
| `SUPABASE_URL` | *required* | Full HTTPS URL to Supabase project |
| `SUPABASE_SERVICE_KEY` | *required* | Service-role key (bypasses RLS) |
| `GOOGLE_API_KEY` | *required* | Google AI Studio API key |
| `TAVILY_API_KEY` | *required* | Tavily web search API key |
| `PRIMARY_MODEL` | gemini-3.1-flash-lite-preview | Model for ReAct orchestrator |
| `SUB_AGENT_MODEL` | gemini-3.1-flash-lite-preview | Model for SQL gen, classification, summary |
| `PRIMARY_MAX_TOKENS` | 2048 | Max output tokens for primary model |
| `SUB_AGENT_MAX_TOKENS` | 600 | Max output tokens for sub-agent |
| `ENABLE_CLASSIFIER` | true | Enable deterministic classifier before agent loop (`false` bypasses classifier) |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | SentenceTransformer model (384-dim) |
| `RERANKER_MODEL` | cross-encoder/ms-marco-MiniLM-L-6-v2 | CrossEncoder for reranking |
| `RAG_RETRIEVE_K` | 20 | Candidates from pgvector search |
| `RAG_RERANK_K` | 5 | Results after cross-encoder reranking |
| `MAX_SQL_ROWS` | 10 | Maximum rows returned per SQL query |
| `CHUNK_SIZE` | 1000 | Characters per chunk (ingestion) |
| `CHUNK_OVERLAP` | 200 | Overlap between chunks (ingestion) |
| `TAVILY_SEARCH_DEPTH` | advanced | basic or advanced |
| `TAVILY_MAX_RESULTS` | 5 | Web search results per query |
| `CACHE_ENABLED` | true | Enable/disable disk cache |
| `CACHE_TTL_SECONDS` | 3600 | Default cache TTL (1 hour) |
| `TAVILY_CACHE_TTL_SECONDS` | 1800 | Web search cache TTL (30 min) |
| `MEMORY_MAX_TOKEN_LIMIT` | 2000 | Token budget for conversation memory |
| `LOG_LEVEL` | INFO | Root logger level |
| `DEBUG` | false | Enable verbose AgentExecutor output |

---

## File Inventory

```
RAGENT/
├── main.py                          # Smoke-test entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Secrets + configuration
│
├── ui/
│   └── streamlit_app.py             # Chat UI (Streamlit)
│
├── src/
│   ├── config.py                    # Pydantic Settings (singleton)
│   ├── llm.py                       # Shared sub-agent LLM singleton
│   │
│   ├── agent/
│   │   ├── primary_agent.py         # AgentExecutor + run_with_classifier
│   │   └── query_classifier.py      # Deterministic intent classification
│   │
│   ├── tools/
│   │   ├── sql_tools.py             # Tools 3+4: SQL query + analytics
│   │   ├── rag_tools.py             # Tools 1+2: RAG feedback + marketing
│   │   └── tavily_tool.py           # Tool 5: Web search
│   │
│   ├── models/
│   │   └── tool_inputs.py           # Pydantic schemas for tool args
│   │
│   ├── db/
│   │   └── supabase_client.py       # Singleton Supabase client
│   │
│   ├── embeddings/
│   │   ├── encoder.py               # SentenceTransformer singleton
│   │   └── reranker.py              # CrossEncoder singleton
│   │
│   ├── memory/
│   │   └── session_memory.py        # Memory factory
│   │
│   ├── cache/
│   │   └── response_cache.py        # diskcache wrapper
│   │
│   ├── utils/
│   │   ├── retry.py                 # Exponential backoff decorator
│   │   └── token_budget.py          # Row/chunk compression
│   │
│   └── ingestion/
│       ├── chunking.py              # Text chunking strategies
│       └── embed_and_upsert.py      # Vectorise + store in Supabase
│
└── tests/
    ├── conftest.py                  # Shared fixtures + mock env
    ├── unit/                        # Unit tests per tool
    └── integration/                 # End-to-end agent tests
```
