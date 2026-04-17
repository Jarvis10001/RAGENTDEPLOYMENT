# Project Context and Instructions: E-Commerce Intelligence Agent

You are working on the "E-Commerce Intelligence Agent" project, a multi-agent system designed for e-commerce business analysts. The system allows natural-language queries about e-commerce operations by intelligently routing queries to internal SQL databases or external web searches.

## Tech Stack
### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI (using Uvicorn for server)
- **AI/Agents**: LangChain, LangGraph, Pydantic AI, Gemini (via Google AI Studio)
- **Web Search**: Tavily API
- **Database**: Supabase (PostgreSQL)
- **Embeddings**: Local `all-MiniLM-L6-v2` for document embeddings and reranking.

### Frontend
- **Language**: TypeScript
- **Framework**: React via Vite
- **Styling**: Tailwind CSS
- **Features**: Real-time SSE streaming for observing agent thinking and tool invocations, dynamic right-panel analysis for execution snapshots.

## Architecture
- **API**: Found in `/api/` (main.py, schemas.py, session_manager.py)
- **Agent Core**: Found in `/src/agent/` (Primary agent, Query classifier)
- **Tools**: Found in `/src/tools/` (RAG, SQL, Tavily)
- **Memory & Ingestion**: Found in `/src/memory/` and `/src/ingestion/`
- **UI**: Found in `/frontend/`

## Coding Guidelines and Rules
1. **Python / Backend**: 
   - Follow strict PEP-8 standards. Use type hints extensively (e.g., using `pydantic` schemas from `api/schemas.py`).
   - Use asynchronous programming (`async def`) wherever doing I/O operations (HTTP calls, DB queries).
   - All server-sent events (SSE) streaming must be handled cleanly to ensure real-time UI updates.
2. **React / Frontend**: 
   - Write functional React components using hooks.
   - Use TypeScript for all components and utilities. 
   - Tailwind CSS should be used for styling. Avoid standalone CSS files unless necessary.
   - Components should handle streaming responses properly and maintain the dynamic right-panel execution snapshots.
3. **Agent Rules**:
   - Classify queries rigorously: Internal metrics go to `ecommerce_sql_query`, external market data goes to `web_market_search`.
   - Maintain the Domain Constraint System: Reject non-business or non-ecommerce queries.
   - Retain conversational memory for follow-up questions and context preservation.

## Development Workflow
- **Backend**: Runs on `localhost:8000` via `uvicorn api.main:app --reload`. Make sure the `.env` file at the root contains your API keys (Google API, Supabase, etc.) and sets `FRONTEND_URL=http://localhost:5173`.
- **Frontend**: Runs on `localhost:5173` via Vite (`npm run dev`). Make sure the `.env` file in the `/frontend/` folder contains `VITE_API_URL=http://localhost:8000`.
- Ensure environment variables are properly loaded so that the application points to your local setup instead of the hosted backend.

## AI Agent Rules
- **Tool Usage**: Do not use scripts or terminal commands to explore or modify code. Perform all file analyses, edits, and changes directly yourself using the configured file editing tools.
