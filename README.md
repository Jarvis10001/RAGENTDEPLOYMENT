# E-commerce Intelligence Agent

A conversational multi-agent system that lets business analysts ask natural-language questions about e-commerce operations and receive deep, synthesised insights combining hard metrics with qualitative customer signals.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Analyst Question                             │
│         "Why did our net profit margin drop by 12%?"                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    QUERY ROUTER AGENT                               │
│              (Senior Analytics Query Classifier)                    │
│                                                                      │
│  • Parses intent → QueryIntent (Pydantic)                           │
│  • Extracts: campaign_id, product_sku, date range, focus metric     │
│  • Decides: needs_sql? needs_rag? needs_synthesis?                  │
│  • Model: Mistral Small                                              │
└────────────┬─────────────────────────────────┬──────────────────────┘
             │                                 │
     ┌───────▼───────┐                 ┌───────▼───────┐
     │  SQL ANALYST   │                 │ RAG RETRIEVAL  │
     │    AGENT       │                 │    AGENT       │
     │                │                 │                │
     │ • Parameterised│                 │ • pgvector     │
     │   Supabase SQL │                 │   cosine search│
     │ • Campaign ROI │                 │ • Cross-encoder│
     │ • Split rates  │                 │   reranking    │
     │ • CLV cohorts  │                 │ • Sentiment    │
     │                │                 │ • Themes       │
     │ Model: Mistral │                 │ Model: Mistral │
     │ Small          │                 │ Small          │
     └───────┬────────┘                 └───────┬────────┘
             │ SQLAnalysisResult                │ RAGResult
             └───────────────┬──────────────────┘
                             │
                             ▼
     ┌───────────────────────────────────────────────────┐
     │               SYNTHESIS AGENT                      │
     │       (Chief Revenue Intelligence Officer)         │
     │                                                     │
     │  • Merges SQL + RAG evidence                       │
     │  • Root-cause analysis with citations               │
     │  • Revenue impact estimation                        │
     │  • Prioritised action items                         │
     │  • Model: Mistral Small                             │
     └───────────────────────┬───────────────────────────┘
                             │
                             ▼
     ┌───────────────────────────────────────────────────┐
     │              DIAGNOSTIC REPORT                     │
     │                                                     │
     │  • executive_summary                                │
     │  • confirmed_root_cause (with evidence)             │
     │  • contributing_factors                             │
     │  • revenue_impact_estimate                          │
     │  • urgency_score (1-10)                             │
     │  • confidence_score (1-10)                          │
     │  • action_items [{action, owner, priority}]         │
     │  • data_gaps                                        │
     └───────────────────────────────────────────────────┘
```

## Tech Stack

| Component       | Technology                                      |
|-----------------|------------------------------------------------|
| Database        | Supabase (PostgreSQL + pgvector)                |
| Agent Framework | CrewAI (multi-agent orchestration)               |
| LLM             | Mistral Small (via Mistral AI API)               |
| Embeddings      | sentence-transformers/all-MiniLM-L6-v2 (384d)   |
| Reranking       | cross-encoder/ms-marco-MiniLM-L-6-v2 (local)    |
| RAG             | LangChain + Supabase RPC (pgvector)              |
| Validation      | Pydantic v2                                      |
| Observability   | Arize Phoenix (OSS)                              |
| Memory          | LangChain ConversationSummaryBufferMemory        |

## Setup

### 1. Prerequisites

- Python 3.11+
- A Supabase project with the schema already provisioned
- A Mistral AI API key

### 2. Clone & Install

```bash
git clone <repo-url>
cd ecommerce-intelligence-agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Supabase RPC Functions

Run these in the Supabase SQL Editor to create the vector search RPC functions:

```sql
-- Omnichannel vector search
CREATE OR REPLACE FUNCTION match_omnichannel_vectors(
    query_embedding VECTOR(384),
    match_count INT DEFAULT 20,
    filter_order_id UUID DEFAULT NULL
)
RETURNS TABLE (id BIGINT, text_content TEXT, order_id UUID, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT v.id, v.text_content, v.order_id,
         1 - (v.embedding <=> query_embedding) AS similarity
  FROM omnichannel_vectors v
  WHERE (filter_order_id IS NULL OR v.order_id = filter_order_id)
  ORDER BY v.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Marketing vector search
CREATE OR REPLACE FUNCTION match_marketing_vectors(
    query_embedding VECTOR(384),
    match_count INT DEFAULT 20,
    filter_campaign_id TEXT DEFAULT NULL
)
RETURNS TABLE (id BIGINT, text_content TEXT, campaign_id TEXT, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT v.id, v.text_content, v.campaign_id,
         1 - (v.embedding <=> query_embedding) AS similarity
  FROM marketing_vectors v
  WHERE (filter_campaign_id IS NULL OR v.campaign_id = filter_campaign_id)
  ORDER BY v.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

### 5. Run Tests

```bash
pytest tests/ -v
```

### 6. Start Arize Phoenix (optional)

```bash
python -m phoenix.server.main serve
# Dashboard at http://localhost:6006
```

## Environment Variables (.env.example)

| Variable                | Description                                  | Required |
|------------------------|----------------------------------------------|----------|
| `SUPABASE_URL`         | Supabase project URL                         | ✅       |
| `SUPABASE_SERVICE_KEY`  | Supabase service-role key                    | ✅       |
| `MISTRAL_API_KEY`      | Mistral AI API key                           | ✅       |
| `ROUTER_MODEL_NAME`    | Model for query router (default: mistral-small-latest) | ❌ |
| `ANALYST_MODEL_NAME`   | Model for SQL analyst (default: mistral-small-latest)  | ❌ |
| `RAG_MODEL_NAME`       | Model for RAG agent (default: mistral-small-latest)    | ❌ |
| `SYNTHESIS_MODEL_NAME` | Model for synthesis (default: mistral-small-latest)    | ❌ |
| `EMBEDDING_MODEL_NAME` | Embedding model (default: all-MiniLM-L6-v2)           | ❌ |
| `RERANKER_MODEL_NAME`  | Reranker model (default: ms-marco-MiniLM-L-6-v2)      | ❌ |
| `VECTOR_SEARCH_TOP_K`  | Vector candidates to retrieve (default: 20)            | ❌ |
| `RERANKER_TOP_K`       | Results to keep after reranking (default: 5)           | ❌ |
| `PHOENIX_ENABLED`      | Enable Arize Phoenix telemetry (default: true)         | ❌ |
| `PHOENIX_ENDPOINT`     | Phoenix collector URL (default: localhost:6006)        | ❌ |
| `MEMORY_MAX_TOKEN_LIMIT` | Session memory token budget (default: 2000)          | ❌ |
| `LOG_LEVEL`            | Logging level (default: INFO)                          | ❌ |
| `DEBUG`                | Verbose debug output (default: false)                  | ❌ |

## Example Queries & Routing

### 1. Full Pipeline (SQL + RAG + Synthesis)

```
"Why did our net profit margin drop by 12% last month despite a 20% increase in orders?"
```
**Routing:** `needs_sql=True` `needs_rag=True` `needs_synthesis=True`
**Rationale:** Requires quantitative margin/order analysis AND qualitative feedback to diagnose root cause.

### 2. SQL Only

```
"Which marketing campaigns have a CAC above $80 and a click-through rate below 2%?"
```
**Routing:** `needs_sql=True` `needs_rag=False` `needs_synthesis=False`
**Rationale:** Pure quantitative question answered entirely from `marketing_campaigns` table.

### 3. RAG Only

```
"What are customers saying about our packaging quality in the last 30 days?"
```
**Routing:** `needs_sql=False` `needs_rag=True` `needs_synthesis=False`
**Rationale:** Pure qualitative question requiring vector search on customer feedback.

### 4. SQL + RAG + Synthesis

```
"We're seeing high split shipment rates on SKU-4421 — is this causing customer complaints?"
```
**Routing:** `needs_sql=True` `needs_rag=True` `needs_synthesis=True`
**Rationale:** Requires split shipment rate data from `orders`/`shipments` AND customer feedback about the experience.

### 5. Trend + Synthesis

```
"Which customer acquisition channels are producing the highest 90-day CLV?"
```
**Routing:** `needs_sql=True` `needs_rag=False` `needs_synthesis=False`
**Rationale:** Quantitative CLV analysis joining `customers` with `marketing_campaigns` via `orders`.

## Usage

```python
from src.crews.diagnostic_crew import DiagnosticCrew

crew = DiagnosticCrew(verbose=True)
report = crew.run("Why did our net profit margin drop by 12% last month?")

print(report.executive_summary)
print(f"Root cause: {report.confirmed_root_cause}")
print(f"Urgency: {report.urgency_score}/10")
print(f"Confidence: {report.confidence_score}/10")

for action in report.action_items:
    print(f"  [{action.priority}] {action.action} → {action.owner}")
```

## Project Structure

```
ecommerce-intelligence-agent/
├── src/
│   ├── agents/          # CrewAI agent definitions
│   ├── crews/           # Crew orchestration wiring
│   ├── tools/           # LangChain-compatible tools (SQL, vector, reranker)
│   ├── models/          # Pydantic v2 models for all I/O
│   ├── db/              # Supabase client singleton
│   ├── ingestion/       # Text chunking + embedding upsert
│   ├── memory/          # Session conversation memory
│   └── config.py        # pydantic-settings configuration
├── tests/
│   ├── unit/            # Unit tests (router, SQL tool, chunking)
│   ├── integration/     # Full pipeline integration test
│   └── conftest.py      # Shared fixtures
├── assets/
│   └── sample_data/     # Sample CSV and JSON for development
├── .env.example
├── requirements.txt
└── README.md
```

## Code Quality

- **Type hints** on every function signature
- **Google-style docstrings** with Args/Returns/Raises on every function
- **Black** formatter for consistent code style
- **Pydantic v2** validation on all agent inputs and outputs
- **Parameterised queries** — zero string-interpolated SQL
- **No magic numbers** — all constants are named and configurable

## License

MIT
