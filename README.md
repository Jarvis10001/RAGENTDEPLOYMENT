# E-Commerce Intelligence Agent

## i. Overview
**What it does:** This project is a multi-agent system that allows business analysts to ask natural-language questions about their e-commerce operations, generating synthesized insights by intelligently routing queries to a SQL database or the live web.
**Problem solved:** Modern e-commerce platforms struggle with siloed data, forcing analysts to manually query SQL for sales metrics and then separately scour Google for industry benchmarks. This agent unifies internal querying and external market research into a single conversational interface.
**Intended users:** E-Commerce Business Analysts, Revenue Operations Teams, and Product Managers.

## ii. Features
- **Conversational Memory:** Preserves multi-turn conversation context, allowing users to ask follow-up questions or clarify previous ambiguous queries without losing the thread.
- **Autonomous Tool Routing:** The agent classifies queries and automatically invokes either the `ecommerce_sql_query` tool (for internal metrics) or the `web_market_search` tool (for external data).
- **Domain Constraint System:** Web Search requests are strictly restricted; non-business or non-ecommerce queries are automatically rejected by a sub-agent.
- **Real-Time Streaming:** Built with FastAPI SSE streaming,     allowing the user to watch the detailed thinking steps, tool invocations, and text generation natively in real-time.
- **Dynamic Right-Panel Analysis:** Saves execution snapshots, so users can seamlessly swap between historic conversation logs and see exactly what SQL query or Web Search was run for that specific question.

## iii. Install and run instructions

**Prerequisites:** Python 3.11+, Node 18+

**1. Clone the repository and configure environments**
Copy the `.env.example` file to create your own `.env` configuration.
```bash
cp .env.example .env
```

**2. Obtain Required Credentials**
You will need to fill out the following inside your `.env` file:
- `GOOGLE_API_KEY`: Get a free key from [Google AI Studio](https://aistudio.google.com/app/apikey).
- `TAVILY_API_KEY`: Get a free key from [Tavily](https://app.tavily.com/).
- `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`: From your Supabase project settings.

*Note on Embeddings:* We use `all-MiniLM-L6-v2` locally for document embeddings and reranking. You do not need an API key for this, but the very first time you run the backend, it will download the model files to your machine. This may take a few minutes depending on your internet connection.

**3. Start the Backend (FastAPI)**
Install python dependencies and launch the Uvicorn server:
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

**4. Start the Frontend (React/Vite)**
In a new terminal, navigate to the `frontend` folder to start the UI:
```bash
cd frontend
npm install
npm run dev
```

The application will be running at `http://localhost:5173`.

## iv. Tech Stack
- **Frontend Framework:** React 18 with Vite, Framer Motion for animations
- **Backend Framework:** Python FastAPI (using Server-Sent Events)
- **AI/ML Orchestration:** LangChain (AgentExecutor, ConversationSummaryBufferMemory)
- **LLM Models:** Google `gemini-3.1-flash-lite-preview`
- **Database:** Supabase (PostgreSQL)
- **External APIs:** Tavily Web Search API

## v. Usage Examples

**1. Asking for internal metrics:**
> **Prompt:** "What was our highest selling product category last month?"
> **Agent Action:** Automatically writes and executes a PostgreSQL query against the Supabase `orders` and `products` tables.
> **Output:** Shows the exact sales volume and revenue by category.

**2. Asking for external competitor benchmarks:**
> **Prompt:** "What are the average shipping costs for online retailers in 2025?"
> **Agent Action:** Bypasses SQL and uses Tavily to search the live web.
> **Output:** Synthesizes the search results, citing exactly where the data came from with numbered URLs in the Detailed Thinking panel.

## vi. Architecture Notes & Future Improvements

**Architecture Notes:**
Our system uses a dual-layer architecture. A React frontend interacts with the FastAPI backend via an asynchronous Server-Sent Event (SSE) stream. Inside FastAPI, questions are pre-processed by a "Classifier Sub-Agent". If the user's intent is clear, it is passed to the Primary LangChain Orchestrator, which uses the ReAct (Reasoning and Acting) framework to choose whether to invoke SQL or Web search tools using LangChain decorators.

**Limitations:**
- The SQL tool currently relies on a relatively rigid understanding of the Supabase schema context injected in the prompt, which may struggle with highly complex multi-table joins.
- The user session history is saved in the browser's `localStorage`; switching browsers or devices will reset the conversation thread.

**Future Improvements:**
- Integrate Supabase Authentication to allow for cross-device, persistent conversation storage.
- Expand the RAG (Retrieval-Augmented Generation) ingestion scripts to automatically index internal PDF reports for broader context support.
