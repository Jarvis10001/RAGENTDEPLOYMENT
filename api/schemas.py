"""Pydantic v2 request/response schemas for the Revenue Intelligence API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    """A single message in a conversation history."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Body for POST /api/chat."""

    message: str = Field(..., min_length=1, description="The user's message.")
    session_id: str = Field(..., description="UUID identifying the browser session.")
    history: list[HistoryItem] = Field(
        default_factory=list,
        description="Recent conversation history for context.",
    )


class HealthResponse(BaseModel):
    """Response for GET /api/health."""

    status: str
    version: str


class ClearResponse(BaseModel):
    """Response for DELETE /api/session/{session_id}."""

    cleared: bool
