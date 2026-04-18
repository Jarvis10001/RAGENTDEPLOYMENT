"""FastAPI application — SSE bridge to the LangChain agent.

Run with::

    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from typing import AsyncGenerator

# Suppress noisy LangChain tracer warnings (benign "No indexed run ID" errors)
logging.getLogger("langchain_core.callbacks.manager").setLevel(logging.ERROR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from api.schemas import ChatRequest, ClearResponse, HealthResponse, HistoryItem
from api.session_manager import session_manager
from src.agent.primary_agent import run_with_classifier, stream_with_classifier
from src.agent.visualization_agent import generate_chart_spec

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Revenue Intelligence API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────
import os

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

# Add production frontend URLs from environment (comma-separated)
frontend_urls = os.getenv("FRONTEND_URL", "")
if frontend_urls:
    allowed_origins.extend([url.strip() for url in frontend_urls.split(",") if url.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse_event(data: dict[str, object]) -> str:
    """Format a dict as an SSE `data:` line."""
    return f"data: {json.dumps(data)}\n\n"


def _extract_text(output: object) -> str:
    """Normalize Gemini output to a plain string.

    With ``include_thoughts=True`` the model wraps its answer in a list of
    content-block dicts::

        [{'type': 'text', 'text': '...', 'index': 0, 'extras': {'signature': '...'}}]

    Gemini 2.5+ may also append plain strings as continuation fragments
    after the initial dict block.  This helper captures both forms.
    """
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        parts = []
        for block in output:
            if isinstance(block, dict):
                # Skip thinking blocks, keep text blocks
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        parts.append(text)
            elif isinstance(block, str):
                # Plain string continuation fragment
                if block.strip():
                    parts.append(block)
        return "".join(parts).strip() or "No response generated."
    return str(output)


async def _stream_chat(
    message: str,
    session_id: str,
    history_context: str,
    raw_history: list[HistoryItem] = None,
    mode: str = "fast",
) -> AsyncGenerator[str, None]:
    """Run the agent in a thread and yield SSE events.

    Phases:
    1. Run ``run_with_classifier`` to completion in a thread pool.
    2. Emit ``tool_start`` / ``tool_end`` events from intermediate_steps.
    3. Stream the final answer word-by-word as ``token`` events.
    4. Emit ``done``.
    """
    start_ts = time.perf_counter()

    try:
        executor = session_manager.get_or_create(session_id, mode=mode)

        # Emit mode so frontend can display it
        yield _sse_event({"type": "mode", "mode": mode})

        # Restore memory from frontend if backend restarted
        if getattr(executor, "memory", None) is not None and raw_history:
            memory_vars = executor.memory.load_memory_variables({})
            if not memory_vars.get("chat_history"):
                logger.info("Restoring agent memory from frontend history.")
                for i in range(0, len(raw_history) - 1, 2):
                    u_msg = raw_history[i]
                    a_msg = raw_history[i+1]
                    if u_msg.role == "user" and a_msg.role == "assistant":
                        executor.memory.save_context(
                            {"input": u_msg.content}, {"output": a_msg.content}
                        )

        # ── Stream live background events ─────────────────────────────
        def get_background_gen():
            return stream_with_classifier(executor, message, history_context)

        gen = await asyncio.to_thread(get_background_gen)
        tool_start_times = {}
        collected_tool_outputs: list[dict[str, str]] = []

        while True:
            try:
                # Next chunk off the main event loop
                msg = await asyncio.to_thread(next, gen)
            except StopIteration:
                break
                
            msg_type = msg.get("type")
            
            if msg_type in ("clarification", "cache_hit"):
                output = _extract_text(msg.get("output", ""))
                words = output.split(" ")
                for i, word in enumerate(words):
                    token = word if i == len(words) - 1 else word + " "
                    yield _sse_event({"type": "token", "content": token})
                    await asyncio.sleep(0.018)
                yield _sse_event({"type": "done", "full_response": output})
                return
                
            elif msg_type == "stream_chunk":
                chunk = msg.get("chunk", {})
                
                if "actions" in chunk:
                    # Tool starts
                    for action in chunk["actions"]:
                        tool_name = getattr(action, "tool", "unknown_tool")
                        tool_input = getattr(action, "tool_input", "")
                        tool_start_times[tool_name] = time.perf_counter()
                        
                        yield _sse_event({
                            "type": "tool_start",
                            "tool": tool_name,
                            "input": str(tool_input)[:500],
                        })
                        
                elif "steps" in chunk:
                    # Tool ends — steps are AgentStep objects with
                    # .action and .observation attributes (NOT tuples)
                    for step in chunk["steps"]:
                        # Support both AgentStep objects and plain tuples
                        if hasattr(step, "action") and hasattr(step, "observation"):
                            action = step.action
                            observation = step.observation
                        elif isinstance(step, (tuple, list)) and len(step) >= 2:
                            action, observation = step[0], step[1]
                        else:
                            continue
                        tool_name = getattr(action, "tool", "unknown_tool")
                        
                        # Calculate exact duration
                        start_time = tool_start_times.get(tool_name, time.perf_counter() - 1.0)
                        duration_ms = int((time.perf_counter() - start_time) * 1000)
                        
                        tool_output_str = str(observation)[:2000]
                        collected_tool_outputs.append({
                            "tool": tool_name,
                            "output": tool_output_str,
                        })
                        yield _sse_event({
                            "type": "tool_end",
                            "tool": tool_name,
                            "output": tool_output_str,
                            "duration_ms": duration_ms,
                        })
                        
                elif "output" in chunk:
                    # Final response token stream
                    output = _extract_text(chunk.get("output", "No response generated."))
                    words = output.split(" ")
                    for i, word in enumerate(words):
                        token = word if i == len(words) - 1 else word + " "
                        yield _sse_event({"type": "token", "content": token})
                        await asyncio.sleep(0.018)

                    # Generate chart visualization if applicable
                    if collected_tool_outputs:
                        try:
                            chart_spec = await asyncio.to_thread(
                                generate_chart_spec, collected_tool_outputs
                            )
                            if chart_spec:
                                logger.info("Chart generated: %s", chart_spec.get("chart_type"))
                                yield _sse_event({
                                    "type": "chart",
                                    "spec": chart_spec,
                                })
                            else:
                                logger.info("Visualization Agent returned NO_CHART.")
                        except Exception as chart_exc:
                            logger.error("Chart generation failed: %s", chart_exc)

                    yield _sse_event({"type": "done", "full_response": output})
                    return

    except Exception as exc:
        logger.error("Chat stream error: %s\n%s", exc, traceback.format_exc())
        yield _sse_event({
            "type": "error",
            "message": f"{type(exc).__name__}: {str(exc)}",
        })


# ── Endpoints ─────────────────────────────────────────────────────────


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream a chat response via Server-Sent Events."""
    # Build classifier context from history
    history_lines: list[str] = []
    for item in request.history[-6:]:
        history_lines.append(f"{item.role}: {item.content[:200]}")
    history_context = "\n".join(history_lines)

    return StreamingResponse(
        _stream_chat(
            request.message,
            request.session_id,
            history_context,
            request.history,
            mode=request.mode,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version="1.0.0")


@app.delete("/api/session/{session_id}", response_model=ClearResponse)
async def clear_session(session_id: str) -> ClearResponse:
    """Clear an agent session and its memory."""
    session_manager.clear(session_id)
    return ClearResponse(cleared=True)


@app.get("/api/sessions/count")
async def session_count() -> dict[str, int]:
    """Return the number of active sessions (debug only)."""
    return {"count": session_manager.active_count}
