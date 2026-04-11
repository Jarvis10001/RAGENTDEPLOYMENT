"""Centralized configuration loaded from environment variables via pydantic-settings.

All secrets and tunables are read from a ``.env`` file (or real env vars).
Nothing is hard-coded.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application-wide settings backed by ``.env`` and environment variables.

    Attributes:
        supabase_url: Full URL to the Supabase project (e.g. https://xyz.supabase.co).
        supabase_service_key: Supabase service-role key for server-side access.
        groq_api_key: API key for Groq (replaces Mistral — faster, higher rate limits).
        router_model_name: Model used by the query-router agent (fast 8B).
        analyst_model_name: Model used by the SQL analyst agent (70B reasoning).
        rag_model_name: Model used by the RAG retrieval agent.
        synthesis_model_name: Model used by the synthesis agent.
        embedding_model_name: HuggingFace model ID for generating embeddings.
        embedding_dimension: Dimensionality of the embedding vectors.
        reranker_model_name: HuggingFace model ID for cross-encoder reranking.
        vector_search_top_k: Number of candidates returned by pgvector search.
        reranker_top_k: Number of results kept after reranking.
        max_sql_rows: Maximum rows returned by the SQL tool per query.
        chunk_size: Maximum number of characters per text chunk.
        chunk_overlap: Overlap in characters between adjacent chunks.
        phoenix_endpoint: URL of the Arize Phoenix collector.
        phoenix_enabled: Whether to send telemetry to Phoenix.
        memory_max_token_limit: Token budget for conversation summary memory.
        log_level: Application log level.
        debug: Enables verbose debug output.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ─────────────────────────────────────────
    supabase_url: str = Field(
        ...,
        description="Full URL to the Supabase project.",
    )
    supabase_service_key: str = Field(
        ...,
        description="Supabase service-role key.",
    )

    # ── LLM ──────────────────────────────────────────────
    groq_api_key: str = Field(
        ...,
        description="API key for Groq (free at console.groq.com).",
    )

    # ── Model Selection ──────────────────────────────────
    # LiteLLM prefix "groq/" is mandatory — CrewAI routes through LiteLLM.
    # 8B for fast classification, 70B for reasoning-heavy agents.
    router_model_name: str = Field(
        default="groq/llama-3.1-8b-instant",
        description="Model for the query-router agent (fast, cheap).",
    )
    analyst_model_name: str = Field(
        default="groq/llama-3.3-70b-versatile",
        description="Model for the SQL analyst agent (best reasoning).",
    )
    rag_model_name: str = Field(
        default="groq/llama-3.3-70b-versatile",
        description="Model for the RAG retrieval agent.",
    )
    synthesis_model_name: str = Field(
        default="groq/llama-3.3-70b-versatile",
        description="Model for the synthesis agent.",
    )

    # ── Embeddings ───────────────────────────────────────
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model ID for embeddings.",
    )
    embedding_dimension: int = Field(
        default=384,
        description="Dimensionality of embedding vectors.",
    )

    # ── Reranker ─────────────────────────────────────────
    reranker_model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="HuggingFace model ID for cross-encoder reranking.",
    )

    # ── RAG Settings ─────────────────────────────────────
    vector_search_top_k: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Candidates returned by pgvector similarity search.",
    )
    reranker_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Results kept after cross-encoder reranking.",
    )

    # ── SQL Tool ─────────────────────────────────────────
    max_sql_rows: int = Field(
        default=15,
        ge=1,
        le=100,
        description="Maximum rows returned by the SQL tool per query.",
    )

    # ── Chunking ─────────────────────────────────────────
    chunk_size: int = Field(
        default=512,
        ge=64,
        description="Max characters per text chunk.",
    )
    chunk_overlap: int = Field(
        default=64,
        ge=0,
        description="Character overlap between adjacent chunks.",
    )

    # ── Observability ────────────────────────────────────
    phoenix_endpoint: str = Field(
        default="http://localhost:6006",
        description="Arize Phoenix collector URL.",
    )
    phoenix_enabled: bool = Field(
        default=True,
        description="Whether to send telemetry to Phoenix.",
    )

    # ── Memory ───────────────────────────────────────────
    memory_max_token_limit: int = Field(
        default=2000,
        ge=256,
        description="Token budget for conversation summary memory.",
    )

    # ── Application ──────────────────────────────────────
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Application log level.",
    )
    debug: bool = Field(
        default=False,
        description="Enable verbose debug output.",
    )

    @field_validator("supabase_url")
    @classmethod
    def _validate_supabase_url(cls, value: str) -> str:
        """Ensure the Supabase URL looks like a valid HTTPS endpoint.

        Args:
            value: Raw URL string from the environment.

        Returns:
            The validated URL string (trailing slash stripped).

        Raises:
            ValueError: If the URL does not start with ``https://``.
        """
        value = value.strip().rstrip("/")
        if not value.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with https://")
        return value


def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    The first call reads from ``.env`` / environment; subsequent calls
    return the same object.

    Returns:
        A fully-validated :class:`Settings` instance.
    """
    return Settings()  # type: ignore[call-arg]
