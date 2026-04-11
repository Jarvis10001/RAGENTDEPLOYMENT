# E-commerce Intelligence Agent

A production-quality multi-agent system that lets business analysts ask
natural-language questions about their e-commerce operations and receive
synthesised insights combining structured metrics with qualitative customer
signals.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       STREAMLIT UI LAYER                            │
│         Chat interface with streaming + session history              │
│         Tool activity panel + token usage sidebar                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ user question
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PRIMARY AGENT (Orchestrator)                     │
│                                                                      │
│  LangChain AgentExecutor (LCEL ReAct pattern) with:                 │
│  • ConversationSummaryBufferMemory (persists across tool calls)      │
│  • Structured tool routing via tool descriptions                     │
│  • Model: gemini-2.5-flash-lite (primary orchestrator)            │
│  • Sub-agent model: gemini-2.5-flash-lite (SQL gen/classification)  │
│                                                                      │
│  The primary agent NEVER answers from its own parametric knowledge.  │
│  It ALWAYS delegates to one or more tools, then synthesises.        │
└─────┬──────────────────┬──────────────────────┬────────────────────┘
      │                  │                       │
      ▼                  ▼                       ▼
┌──────────┐    ┌─────────────────┐    ┌──────────────────┐
│  RAG     │    │   SQL AGENT     │    │  TAVILY SEARCH   │
│  TOOLS   │    │   TOOLS         │    │  TOOL            │
│          │    │                 │    │                  │
│ Tool 1:  │    │ Tool 3:         │    │ Tool 5:          │
│ Omni-    │    │ ecommerce_sql_  │    │ web_market_      │
│ channel  │    │ query           │    │ search           │
│ Feedback │    │ (row-level      │    │ (live web data,  │
│ Search   │    │  lookups)       │    │  benchmarks,     │
│          │    │                 │    │  competitors)    │
│ Tool 2:  │    │ Tool 4:         │    │                  │
│ Marketing│    │ ecommerce_      │    │ Gemini Flash     │
│ Content  │    │ analytics_query │    │ for query        │
│ Search   │    │ (aggregations,  │    │ reformulation    │
│          │    │  cohorts, ROI)  │    │                  │
│ Gemini   │    │ Gemini Flash    │    └──────────────────┘
│ Flash +  │    │ for SQL gen +   │
│ local    │    │ local reranker  │
│ reranker │    │                 │
└──────────┘    └─────────────────┘
      │                  │                       │
      └──────────────────┴───────────────────────┘
                         │ all tool results
                         ▼
              Primary agent (Gemini Flash Lite) synthesises
              all tool outputs into final answer
                         │
                         ▼
              Streamlit streams answer to UI
              Memory updated with Q+A pair
```

## Tech Stack

| Component          | Technology                                      |
|--------------------|------------------------------------------------|
| UI                 | Streamlit 1.39+ (st.chat_message + streaming)  |
| Primary Agent      | LangChain AgentExecutor (LCEL ReAct pattern)   |
| Tools              | LangChain @tool decorated functions            |
| Memory             | ConversationSummaryBufferMemory (LangChain)    |
| Primary LLM        | Google Gemini — gemini-2.5-flash-lite          |
| Sub-agent LLM      | Google Gemini — gemini-2.5-flash-lite          |
| LLM Class          | ChatGoogleGenerativeAI (langchain-google-genai)|
| Embeddings         | sentence-transformers all-MiniLM-L6-v2 (local) |
| Reranker           | cross-encoder/ms-marco-MiniLM-L-6-v2 (local)  |
| Vector Search      | Supabase pgvector via RPC functions            |
| Structured Queries | Supabase Python client (parameterised only)    |
| Web Search         | Tavily Search API                              |
| Validation         | Pydantic v2 on all tool inputs and outputs     |
| Config             | pydantic-settings + .env file                  |
| Caching            | diskcache (disk-backed, no Redis needed)       |

## Prerequisites

1. **Python 3.10+** installed
2. **Supabase project** with the schema and RPC functions set up
3. **Google Gemini API key** — free at https://aistudio.google.com/app/apikey
4. **Tavily API key** — free tier at https://app.tavily.com

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd natwest-hackathon
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
# Edit .env with your actual API keys
```

### 3. Run the Streamlit interface

```bash
streamlit run ui/streamlit_app.py
```

The app will open at http://localhost:8501.

### 4. Run tests

```bash
python -m pytest tests/ -v --tb=short
```

## Environment Variables Reference

| Variable                 | Required | Default                              | Description                                |
|--------------------------|----------|--------------------------------------|--------------------------------------------|
| `SUPABASE_URL`           | ✅       | —                                    | Supabase project URL                       |
| `SUPABASE_SERVICE_KEY`   | ✅       | —                                    | Supabase service-role key                  |
| `GOOGLE_API_KEY`         | ✅       | —                                    | Google Gemini API key                      |
| `TAVILY_API_KEY`         | ✅       | —                                    | Tavily web search API key                  |
| `PRIMARY_MODEL`          | ❌       | `gemini-3.1-flash-lite-preview`              | Primary orchestrator model                 |
| `SUB_AGENT_MODEL`        | ❌       | `gemini-3.1-flash-lite-preview`              | Sub-agent model (SQL gen, summarisation)   |
| `PRIMARY_MAX_TOKENS`     | ❌       | `2048`                               | Max output tokens for primary model        |
| `SUB_AGENT_MAX_TOKENS`   | ❌       | `600`                                | Max output tokens for sub-agent model      |
| `EMBEDDING_MODEL`        | ❌       | `all-MiniLM-L6-v2`                  | SentenceTransformer model for embeddings   |
| `RERANKER_MODEL`         | ❌       | `cross-encoder/ms-marco-MiniLM-L-6-v2` | CrossEncoder model for reranking        |
| `RAG_RETRIEVE_K`         | ❌       | `20`                                 | Candidates from pgvector search            |
| `RAG_RERANK_K`           | ❌       | `5`                                  | Results after reranking                    |
| `MAX_SQL_ROWS`           | ❌       | `10`                                 | Max rows from SQL queries                  |
| `TAVILY_SEARCH_DEPTH`    | ❌       | `advanced`                           | Tavily depth: `basic` or `advanced`        |
| `TAVILY_MAX_RESULTS`     | ❌       | `5`                                  | Max web search results                     |
| `CACHE_ENABLED`          | ❌       | `true`                               | Enable/disable disk cache                  |
| `CACHE_DIR`              | ❌       | `.cache/responses`                   | Cache directory path                       |
| `CACHE_TTL_SECONDS`      | ❌       | `3600`                               | Default cache TTL (1 hour)                 |
| `TAVILY_CACHE_TTL_SECONDS`| ❌      | `1800`                               | Web search cache TTL (30 min)              |
| `MEMORY_MAX_TOKEN_LIMIT` | ❌       | `2000`                               | Conversation memory token budget           |
| `PHOENIX_ENABLED`        | ❌       | `false`                              | Arize Phoenix observability                |
| `LOG_LEVEL`              | ❌       | `INFO`                               | Logging level                              |
| `DEBUG`                  | ❌       | `false`                              | Verbose debug output                       |

## Example Queries and Expected Tool Routing

| # | Query | Tools Called |
|---|-------|-------------|
| 1 | "Why did our net profit margin drop 12% last month despite 20% more orders?" | `ecommerce_sql_query` + `omnichannel_feedback_search` |
| 2 | "Which marketing campaigns have CAC above $80 and CTR below 2%?" | `ecommerce_analytics_query` |
| 3 | "What are customers saying about our packaging in the last 30 days?" | `omnichannel_feedback_search` |
| 4 | "Compare split shipment rates and freight costs across warehouses" | `ecommerce_analytics_query` |
| 5 | "Is our SUMMER_SALE campaign messaging aligned with what customers say?" | `marketing_content_search` + `omnichannel_feedback_search` |
| 6 | "What is the industry average return rate for e-commerce in 2024?" | `web_market_search` |
| 7 | "Which customers acquired via Instagram have the highest 90-day CLV?" | `ecommerce_analytics_query` |
| 8 | "High freight costs on SKU-4421 — are customers complaining about it?" | `ecommerce_sql_query` + `omnichannel_feedback_search` |

## Gemini Free Tier Limits and Caching

The Google Gemini free tier has rate limits:
- **gemini-2.5-flash-lite**: 15 RPM, 1M TPM

**How caching mitigates these:**
- All tool results are cached to disk via `diskcache` with configurable TTLs
- Repeated identical queries hit the cache and make **zero** LLM/API calls
- RAG and SQL caches default to 1-hour TTL; web search to 30-minute TTL
- Cache is disk-backed and survives server restarts
- Disable caching by setting `CACHE_ENABLED=false` in `.env`

## Troubleshooting

### Supabase PGRST202 Schema Cache Error

If you see `PGRST202` errors, your Supabase schema cache is stale:

1. Go to **Supabase Dashboard → Settings → API**
2. Click **Reload schema cache**
3. Or restart the PostgREST service

### Gemini Quota Exhaustion

If you hit rate limits:

1. Wait 60 seconds and retry
2. Use narrower filters (specific campaign, date range, SKU) to reduce token usage
3. Enable caching (`CACHE_ENABLED=true`) to avoid repeated calls
4. Consider upgrading to a paid Gemini plan for higher limits

### Embedding Model First-Run Download

On first startup, `sentence-transformers` downloads the embedding (~22 MB)
and reranker (~22 MB) models. This requires internet access and may take
1-2 minutes. Subsequent starts load from cache (~5 seconds).

### Port Already In Use

If Streamlit says port 8501 is in use:

```bash
streamlit run ui/streamlit_app.py --server.port 8502
```

## Project Structure

```
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   └── primary_agent.py        # AgentExecutor + memory wiring
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── rag_tools.py            # Tool 1 + Tool 2 (vector search)
│   │   ├── sql_tools.py            # Tool 3 + Tool 4 (SQL queries)
│   │   └── tavily_tool.py          # Tool 5 (web search)
│   ├── memory/
│   │   ├── __init__.py
│   │   └── session_memory.py       # ConversationSummaryBufferMemory factory
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase_client.py      # Singleton Supabase client
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── encoder.py              # SentenceTransformer singleton
│   │   └── reranker.py             # CrossEncoder singleton
│   ├── cache/
│   │   ├── __init__.py
│   │   └── response_cache.py       # diskcache wrapper
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tool_inputs.py          # Pydantic v2 input models
│   │   └── tool_outputs.py         # Pydantic v2 output models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── token_budget.py         # compress_sql_rows, compress_rag_chunks
│   │   └── retry.py                # exponential_backoff decorator
│   └── config.py                   # pydantic-settings Settings class
├── ui/
│   ├── __init__.py
│   └── streamlit_app.py            # Main Streamlit chat interface
├── tests/
│   ├── unit/
│   │   ├── test_rag_tools.py
│   │   ├── test_sql_tools.py
│   │   ├── test_tavily_tool.py
│   │   └── test_token_budget.py
│   ├── integration/
│   │   └── test_primary_agent.py
│   └── conftest.py
├── assets/
│   └── sample_data/
│       ├── feedback_sample.json
│       └── orders_sample.csv
├── .env.example
├── requirements.txt
└── README.md
```
