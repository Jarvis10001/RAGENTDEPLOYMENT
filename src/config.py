"""Centralised configuration loaded from environment variables via pydantic-settings.

All secrets and tunables are read from a ``.env`` file (or real environment
variables in production). Nothing is hard-coded. Every other module imports
the module-level ``settings`` singleton from here.

Validation
----------
* ``SUPABASE_URL`` must begin with ``https://``.
* ``TAVILY_SEARCH_DEPTH`` must be ``basic`` or ``advanced``.
* ``LOG_LEVEL`` must be a valid Python log level name.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Force load .env into os.environ so external libraries (like LangSmith/LangChain) 
# can read variables like LANGCHAIN_API_KEY that aren't defined in the Settings model.
load_dotenv(".env")


class Settings(BaseSettings):
    """Application-wide settings backed by ``.env`` and environment variables.

    All fields without a default are **required** — the application will
    refuse to start if they are absent.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database (required) ──────────────────────────────────────────
    supabase_url: str = Field(
        ...,
        description="Full HTTPS URL to the Supabase project.",
    )
    supabase_service_key: str = Field(
        ...,
        description="Supabase service-role key (bypasses RLS for server use).",
    )

    # ── LLM — Google Gemini (required) ───────────────────────────────
    google_api_key: str = Field(
        ...,
        description="Google AI Studio API key for Gemini models.",
    )

    # ── Model names ──────────────────────────────────────────────────
    primary_model: str = Field(
        default="gemini-3.1-flash-lite-preview",
        description="Model name for the primary orchestrator agent.",
    )
    sub_agent_model: str = Field(
        default="gemini-3.1-flash-lite-preview",
        description="Model name for sub-agent tasks (SQL gen, summarisation).",
    )

    # ── Token budgets ────────────────────────────────────────────────
    primary_max_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="Max output tokens for the primary model.",
    )
    sub_agent_max_tokens: int = Field(
        default=600,
        ge=64,
        le=2048,
        description="Max output tokens for sub-agent tasks.",
    )

    # ── Web search (required) ────────────────────────────────────────
    tavily_api_key: str = Field(
        ...,
        description="Tavily web search API key.",
    )

    # ── Embeddings (Google Gemini API) ──────────────────────────────
    embedding_model: str = Field(
        default="models/gemini-embedding-001",
        description="[DEPRECATED] Kept for backward compatibility. Embeddings now use Google Generative AI API (gemini-embedding-001).",
    )
    reranker_model: str = Field(
        default="rerank-english-v3.0",
        description="Cohere Rerank API model ID.",
    )
    cohere_api_key: str | None = Field(
        default=None,
        description="Cohere Rerank API key. Optional fallback to unranked if not supplied.",
    )

    # ── RAG ──────────────────────────────────────────────────────────
    rag_retrieve_k: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Candidates returned by pgvector similarity search.",
    )
    rag_rerank_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Results kept after cross-encoder reranking.",
    )

    # ── SQL ──────────────────────────────────────────────────────────
    max_sql_rows: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum rows returned by the SQL tool per query.",
    )

    # ── Ingestion / Chunking ─────────────────────────────────────────
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum characters per text chunk during ingestion.",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Character overlap between adjacent chunks.",
    )

    # ── Tavily ───────────────────────────────────────────────────────
    tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Tavily search depth: 'basic' (faster) or 'advanced' (thorough).",
    )
    tavily_max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum web search results to return per query.",
    )

    # ── Cache ────────────────────────────────────────────────────────
    cache_enabled: bool = Field(
        default=True,
        description="Enable disk-backed response caching.",
    )
    cache_dir: str = Field(
        default=".cache/responses",
        description="Directory path for diskcache storage (set to empty string to disable on ephemeral filesystems like Render).",
    )
    cache_enabled_override: bool | None = Field(
        default=None,
        description="Override cache_enabled when set (useful for production on Render where FS is ephemeral).",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        description="Default TTL for cached tool responses (seconds).",
    )
    tavily_cache_ttl_seconds: int = Field(
        default=1800,
        ge=60,
        description="TTL for cached web search responses (seconds).",
    )

    # ── Memory ───────────────────────────────────────────────────────
    memory_max_token_limit: int = Field(
        default=2000,
        ge=256,
        le=8192,
        description="Token budget for ConversationSummaryBufferMemory.",
    )

    # ── Observability ────────────────────────────────────────────────
    phoenix_enabled: bool = Field(
        default=False,
        description="Send traces to Arize Phoenix for LLM observability.",
    )

    # ── Application ──────────────────────────────────────────────────
    enable_classifier: bool = Field(
        default=True,
        description=(
            "Enable deterministic query classification before the agent loop. "
            "Set false to bypass classifier and save one sub-agent call per query."
        ),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Root logger level.",
    )
    debug: bool = Field(
        default=False,
        description="Enable verbose AgentExecutor debug output.",
    )

    # ── Validators ───────────────────────────────────────────────────

    @field_validator("supabase_url")
    @classmethod
    def _validate_supabase_url(cls, value: str) -> str:
        """Ensure the Supabase URL is a valid HTTPS endpoint.

        Args:
            value: Raw URL string from environment.

        Returns:
            Validated URL with trailing slash stripped.

        Raises:
            ValueError: If the URL does not start with ``https://``.
        """
        value = value.strip().rstrip("/")
        if not value.startswith("https://"):
            raise ValueError(
                f"SUPABASE_URL must start with 'https://'. Got: {value!r}"
            )
        return value

    @model_validator(mode="after")
    def _validate_rag_k_ordering(self) -> "Settings":
        """Ensure retrieve_k >= rerank_k (cannot rerank more than retrieved).

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If rag_rerank_k > rag_retrieve_k.
        """
        if self.rag_rerank_k > self.rag_retrieve_k:
            raise ValueError(
                f"RAG_RERANK_K ({self.rag_rerank_k}) cannot exceed "
                f"RAG_RETRIEVE_K ({self.rag_retrieve_k})."
            )
        return self


settings = Settings()  # type: ignore[call-arg]

# ── Configure root logger from settings (runs once at import time) ────
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
