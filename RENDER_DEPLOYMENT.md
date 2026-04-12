# Render Deployment Guide

## Backend Deployment (Render.com)

### 1. Create a New Web Service on Render
- Connect your GitHub repository + deployment branch
- Choose **Python** as the runtime
- Set build command: `pip install -r requirements.txt`
- Set start command: `gunicorn -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:$PORT`

### 2. Required Environment Variables
Add these to Render's Environment Variables dashboard:

```
# Database & Auth
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# AI/LLM APIs
GOOGLE_API_KEY=your-google-gemini-api-key
TAVILY_API_KEY=your-tavily-api-key
COHERE_API_KEY=your-cohere-rerank-api-key

# Frontend URL (from Vercel deployment)
FRONTEND_URL=https://ragentdeployment-xxxxx.vercel.app

# Cache (disable for ephemeral filesystem)
CACHE_ENABLED=false

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

### 3. Performance Tuning
For free tier Render, consider:
- Use `CACHE_ENABLED=false` (Render's filesystem is ephemeral)
- Set `TAVILY_SEARCH_DEPTH=basic` to reduce API calls
- Keep `PRIMARY_MAX_TOKENS=1024` and `SUB_AGENT_MAX_TOKENS=512`

---

## Frontend Deployment (Vercel - Already Done!)

Your frontend is already deployed at: `https://ragentdeployment-c44ox06o9.vercel.app/`

### To Update Frontend API Endpoint:
1. Go to Vercel Dashboard → Project Settings → Environment Variables
2. Add: `VITE_API_URL=https://your-render-backend-url.onrender.com`
3. Redeploy from Git

---

## PostgreSQL Migration on Render

If you need to migrate your Supabase pgvector columns to match the new 768-dimensional embeddings:

```sql
-- Alter vector columns to accept 768 dimensions
ALTER TABLE omnichannel_vectors ALTER COLUMN embedding TYPE vector(768);
ALTER TABLE marketing_vectors ALTER COLUMN embedding TYPE vector(768);
```

---

## Health Check
Test the backend once deployed:
```bash
curl https://your-render-backend-url.onrender.com/api/health
# Expected response: {"status":"ok","version":"1.0.0"}
```

---

## Troubleshooting

### CORS Errors
- Ensure `FRONTEND_URL` env var matches your Vercel URL exactly
- Check that the backend includes the Vercel URL in CORS allow_origins

### 429 Quota Errors  
- Google Embedding API free tier: 1000 requests/day
- Tavily API rate limits: check `TAVILY_SEARCH_DEPTH`
- Cohere Rerank: 1000 requests/minute on free tier

### Cache Errors on Render
- Always set `CACHE_ENABLED=false` on Render (ephemeral filesystem)
- Cache will work fine locally for development
